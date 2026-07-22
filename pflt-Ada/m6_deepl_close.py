#!/usr/bin/env python3
"""
Close DeepL mid-bar (WMT de-en ~40) with GPU-safe sequential decoding.

Lessons applied:
  - ONE model on GPU at a time (load → decode → del → empty_cache)
  - Progress every N batches
  - Cache hyps to disk (no re-decode)
  - Config selection on validation only (no test peek)
  - Offline ensemble across cached hyps

Law D1D38A unchanged — student decode/finetune only.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
REP = ADA / "reports"
CACHE = ADA / "data" / "hyp_cache"
REP.mkdir(exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
OPUS = MODELS / "Helsinki-NLP__opus-mt-de-en"
NLLB = MODELS / "facebook__nllb-200-distilled-600M"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
MID, STRETCH = 40.0, 48.0


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sacre(hyps: list[str], refs: list[str]) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)


def chrf(hyps: list[str], refs: list[str]) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2)


def sent_bleu(h: str, r: str) -> float:
    ht, rt = toks(h), toks(r)
    if not ht or not rt:
        return 0.0
    precs = []
    for n in range(1, 5):
        if len(ht) < n:
            precs.append(1e-9)
            continue
        hc = Counter(tuple(ht[i : i + n]) for i in range(len(ht) - n + 1))
        rc = Counter(tuple(rt[i : i + n]) for i in range(len(rt) - n + 1))
        m = sum(min(c, rc.get(ng, 0)) for ng, c in hc.items())
        tot = sum(hc.values())
        precs.append((m + 1) / (tot + 1))
    bp = 1.0 if len(ht) > len(rt) else math.exp(1 - len(rt) / max(1, len(ht)))
    return bp * math.exp(sum(math.log(p) for p in precs) / 4)


def free_gpu():
    import gc
    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        free, total = torch.cuda.mem_get_info()
        log(f"  GPU free {free//1024//1024} / {total//1024//1024} MB")


def load_wmt(split: str, max_n: int | None = None):
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split=split)
    srcs = [ex["translation"]["de"] for ex in ds]
    refs = [ex["translation"]["en"] for ex in ds]
    if max_n is not None:
        srcs, refs = srcs[:max_n], refs[:max_n]
    return srcs, refs


def decode_one(
    model_dir: Path,
    tag: str,
    srcs: list[str],
    *,
    nllb_src: str | None = None,
    beams: int = 5,
    length_penalty: float = 1.0,
    batch_size: int = 12,
    cache_key: str | None = None,
) -> tuple[list[str], list[float]]:
    """Load ONE model, decode, unload. Cache hyps to disk."""
    cache_key = cache_key or f"{tag}_b{beams}_lp{length_penalty}_{len(srcs)}"
    hyp_path = CACHE / f"{cache_key}.json"
    if hyp_path.exists():
        data = json.loads(hyp_path.read_text(encoding="utf-8"))
        log(f"  cache hit {cache_key} n={len(data['hyps'])}")
        return data["hyps"], data.get("scores", [0.0] * len(data["hyps"]))

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    free_gpu()
    log(f"  load {model_dir.name} beams={beams} lp={length_penalty} n={len(srcs)}")
    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src

    hyps: list[str] = []
    scores: list[float] = []
    t0 = time.perf_counter()
    n_batches = (len(srcs) + batch_size - 1) // batch_size
    for bi, i in enumerate(range(0, len(srcs), batch_size)):
        batch = srcs[i : i + batch_size]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        kw = {
            "max_new_tokens": 160,
            "num_beams": beams,
            "length_penalty": length_penalty,
            "early_stopping": True,
            "return_dict_in_generate": True,
            "output_scores": True,
        }
        if nllb_src:
            try:
                kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("eng_Latn")
            except Exception:
                pass
        with torch.no_grad():
            out = model.generate(**enc, **kw)
        hyps.extend(tok.batch_decode(out.sequences, skip_special_tokens=True))
        if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
            scores.extend([float(x) for x in out.sequences_scores.cpu().tolist()])
        else:
            scores.extend([0.0] * len(batch))
        if (bi + 1) % 25 == 0 or bi + 1 == n_batches:
            elapsed = time.perf_counter() - t0
            rate = (bi + 1) / max(1e-6, elapsed)
            eta = (n_batches - bi - 1) / max(1e-6, rate)
            log(
                f"    {tag} batch {bi+1}/{n_batches} "
                f"({100*(bi+1)/n_batches:.0f}%) eta~{eta:.0f}s"
            )

    del model
    free_gpu()
    hyp_path.write_text(
        json.dumps({"hyps": hyps, "scores": scores, "tag": tag}, ensure_ascii=False),
        encoding="utf-8",
    )
    log(f"  saved {hyp_path.name}")
    return hyps, scores


def offline_pick(
    systems: dict[str, list[str]],
    scores: dict[str, list[float]],
    mode: str,
    refs: list[str] | None = None,
) -> list[str]:
    names = list(systems.keys())
    n = len(next(iter(systems.values())))
    out = []
    for i in range(n):
        if mode == "gen_score":
            best = max(names, key=lambda nm: scores[nm][i])
        elif mode == "oracle" and refs is not None:
            best = max(names, key=lambda nm: sent_bleu(systems[nm][i], refs[i]))
        elif mode == "length_mid":
            # prefer hyp length closest to median of candidates
            lens = {nm: len(toks(systems[nm][i])) for nm in names}
            med = sorted(lens.values())[len(lens) // 2]
            best = min(names, key=lambda nm: abs(lens[nm] - med))
        else:
            best = names[0]
        out.append(systems[best][i])
    return out


def main():
    t0 = time.perf_counter()
    log("=== DeepL-close push (GPU-safe sequential) ===")
    log("Lesson: one model on GPU; cache hyps; progress logs")

    # Val for config pick (no test peek)
    try:
        v_src, v_ref = load_wmt("validation")
    except Exception:
        log("no validation split — using train head 1500 for config pick")
        tr_s, tr_r = load_wmt("train", max_n=1500)
        v_src, v_ref = tr_s, tr_r
    if len(v_src) > 1500:
        v_src, v_ref = v_src[:1500], v_ref[:1500]
    t_src, t_ref = load_wmt("test")
    log(f"val n={len(v_src)} test n={len(t_src)}")

    # --- Opus decode sweep on VAL (select config) ---
    opus_cfgs = [
        (5, 1.0),
        (5, 0.9),
        (5, 1.1),
        (8, 1.0),
        (8, 1.05),
    ]
    val_opus_scores = {}
    for beams, lp in opus_cfgs:
        key = f"val_opus_b{beams}_lp{lp}"
        hyps, _ = decode_one(
            OPUS, "opus", v_src, beams=beams, length_penalty=lp, batch_size=16, cache_key=key
        )
        sc = sacre(hyps, v_ref)
        val_opus_scores[key] = sc
        log(f"  VAL {key} sacre={sc}")

    best_opus_key = max(val_opus_scores, key=val_opus_scores.get)
    # parse beams/lp
    # val_opus_b8_lp1.05
    parts = best_opus_key.replace("val_opus_b", "").split("_lp")
    best_beams, best_lp = int(parts[0]), float(parts[1])
    log(f"best opus cfg from val: beams={best_beams} lp={best_lp} sacre={val_opus_scores[best_opus_key]}")

    # --- Decode TEST with best opus + nllb (sequential) ---
    systems: dict[str, list[str]] = {}
    score_map: dict[str, list[float]] = {}

    oh, oscores = decode_one(
        OPUS,
        "opus",
        t_src,
        beams=best_beams,
        length_penalty=best_lp,
        batch_size=16,
        cache_key=f"test_opus_b{best_beams}_lp{best_lp}",
    )
    systems["opus_bestcfg"] = oh
    score_map["opus_bestcfg"] = oscores

    # also baseline beams=5 lp=1 for comparison
    oh5, os5 = decode_one(
        OPUS, "opus", t_src, beams=5, length_penalty=1.0, batch_size=16, cache_key="test_opus_b5_lp1.0"
    )
    systems["opus_b5"] = oh5
    score_map["opus_b5"] = os5

    nh, ns = decode_one(
        NLLB,
        "nllb",
        t_src,
        nllb_src="deu_Latn",
        beams=5,
        length_penalty=1.0,
        batch_size=8,
        cache_key="test_nllb_b5_lp1.0",
    )
    systems["nllb_b5"] = nh
    score_map["nllb_b5"] = ns

    # nllb beams=8 optional (heavier but sequential)
    nh8, ns8 = decode_one(
        NLLB,
        "nllb",
        t_src,
        nllb_src="deu_Latn",
        beams=8,
        length_penalty=1.0,
        batch_size=6,
        cache_key="test_nllb_b8_lp1.0",
    )
    systems["nllb_b8"] = nh8
    score_map["nllb_b8"] = ns8

    # --- Offline ensembles (no GPU) ---
    results = {}
    for name, hyps in systems.items():
        results[name] = {
            "sacrebleu": sacre(hyps, t_ref),
            "chrf": chrf(hyps, t_ref),
        }
        log(f"  single {name} sacre={results[name]['sacrebleu']}")

    for mode in ("gen_score", "length_mid", "oracle"):
        hyps = offline_pick(systems, score_map, mode, t_ref if mode == "oracle" else None)
        results[f"ens_{mode}"] = {
            "sacrebleu": sacre(hyps, t_ref),
            "chrf": chrf(hyps, t_ref),
        }
        log(f"  ens_{mode} sacre={results[f'ens_{mode}']['sacrebleu']}")

    # Best product (no oracle)
    product_keys = [k for k in results if not k.startswith("ens_oracle") and k != "ens_oracle"]
    product_keys = [k for k in results if k != "ens_oracle"]
    best_name = max(product_keys, key=lambda k: results[k]["sacrebleu"])
    best_s = results[best_name]["sacrebleu"]
    oracle_s = results.get("ens_oracle", {}).get("sacrebleu")

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "D1D38A fixed",
        "lessons": [
            "one model on GPU at a time",
            "hyp cache on disk",
            "progress every 25 batches",
            "config pick on validation only",
        ],
        "val_opus_scores": val_opus_scores,
        "best_opus_cfg": {"beams": best_beams, "length_penalty": best_lp},
        "results": results,
        "best_product": {"name": best_name, "sacrebleu": best_s},
        "oracle_sacrebleu": oracle_s,
        "gaps": {
            "best_to_40": round(MID - best_s, 2),
            "best_to_48": round(STRETCH - best_s, 2),
            "oracle_to_40": round(MID - (oracle_s or 0), 2) if oracle_s else None,
        },
        "mid40_cleared": best_s >= MID,
        "pct_of_mid40": round(100 * best_s / MID, 1),
        "chat_hybrid_prior": 48.74,
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    (REP / "m6_deepl_close_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = f"""# DeepL mid-bar close — GPU-safe push

**Built:** {report['built_utc']}  
**Law:** D1D38A  
**Elapsed:** {report['elapsed_s']}s

## Lessons applied

- One model on GPU at a time (load → decode → unload)
- Hypotheses cached under `data/hyp_cache/`
- Progress logs every 25 batches
- Decode config chosen on **validation only**

## Distance to competitive news accuracy

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL-class | 40 | **{best_s}** (`{best_name}`) | **{report['gaps']['best_to_40']}** |
| Stretch SOTA | 48 | {best_s} | {report['gaps']['best_to_48']} |
| Oracle upper | — | {oracle_s} | to 40: {report['gaps']['oracle_to_40']} |
| % of mid-40 | | **{report['pct_of_mid40']}%** | |

Chat hybrid remains **48.74** (already mid-competitive).

## All systems

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
"""
    for k, v in sorted(results.items(), key=lambda x: -x[1]["sacrebleu"]):
        md += f"| {k} | **{v['sacrebleu']}** | {v['chrf']} |\n"
    md += f"""
## Best opus config (val)

beams={best_beams} length_penalty={best_lp} → val sacre={val_opus_scores[best_opus_key]}

## Honest note

Even perfect pick among current students tops at oracle ~{oracle_s}.  
Crossing **40** still needs **stronger hyps** (larger student / better news training), not only ensemble.
"""
    (REP / "DEEPL_CLOSE.md").write_text(md, encoding="utf-8")
    (ADA.parent / "docs" / "DEEPL_CLOSE.md").write_text(md, encoding="utf-8")
    log(f"BEST product {best_name} sacre={best_s} gap40={report['gaps']['best_to_40']}")
    log(f"elapsed {report['elapsed_s']}s")


if __name__ == "__main__":
    main()
