#!/usr/bin/env python3
"""
Stronger student push — NOT more 600M beam tweaks.

1) Download NLLB-1.3B if missing; sequential WMT14 de-en eval (one model on GPU)
2) Offline ensemble with cached opus hyps
3) Careful longer opus FT: early-stop on TRAIN-heldout (not WMT val — that mismatched test)

Law D1D38A fixed. Lessons: load→decode→unload; hyp_cache; no dual-model VRAM thrash.
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
NLLB_600 = MODELS / "facebook__nllb-200-distilled-600M"
NLLB_13 = MODELS / "facebook__nllb-200-1.3B"
NLLB_13_DIST = MODELS / "facebook__nllb-200-distilled-1.3B"
FT_OUT = MODELS / "Helsinki-NLP__opus-mt-de-en-wmt-ft-v4"
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
        log(f"  GPU free {free // 1024 // 1024} / {total // 1024 // 1024} MB")


def load_wmt(split: str, max_n: int | None = None):
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split=split)
    srcs = [ex["translation"]["de"] for ex in ds]
    refs = [ex["translation"]["en"] for ex in ds]
    if max_n is not None:
        srcs, refs = srcs[:max_n], refs[:max_n]
    return srcs, refs


def ensure_model(repo_id: str, dest: Path) -> Path:
    """Download HF model to dest if missing (marker: config.json)."""
    if (dest / "config.json").exists():
        log(f"  present {dest.name}")
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    log(f"  downloading {repo_id} → {dest}")
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    log(f"  done {dest.name}")
    return dest


def decode_one(
    model_dir: Path,
    tag: str,
    srcs: list[str],
    *,
    nllb_src: str | None = None,
    beams: int = 5,
    length_penalty: float = 1.0,
    batch_size: int = 8,
    cache_key: str | None = None,
    use_fp16: bool = True,
) -> tuple[list[str], list[float]]:
    cache_key = cache_key or f"{tag}_b{beams}_lp{length_penalty}_{len(srcs)}"
    hyp_path = CACHE / f"{cache_key}.json"
    if hyp_path.exists():
        data = json.loads(hyp_path.read_text(encoding="utf-8"))
        if len(data.get("hyps", [])) == len(srcs):
            log(f"  cache hit {cache_key} n={len(data['hyps'])}")
            return data["hyps"], data.get("scores", [0.0] * len(data["hyps"]))
        log(f"  cache size mismatch — re-decode {cache_key}")

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    free_gpu()
    log(f"  load {model_dir.name} beams={beams} lp={length_penalty} n={len(srcs)} fp16={use_fp16}")
    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    dtype = torch.float16 if (use_fp16 and torch.cuda.is_available()) else torch.float32
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True, torch_dtype=dtype
        )
    except Exception as e:
        log(f"  fp16 load failed ({e}); fallback fp32")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True
        )
        dtype = torch.float32
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
        try:
            with torch.no_grad():
                out = model.generate(**enc, **kw)
        except torch.cuda.OutOfMemoryError:
            free_gpu()
            log(f"  OOM at batch {bi}; retry batch_size=1")
            for s in batch:
                enc1 = tok(
                    [s],
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=192,
                )
                enc1 = {k: v.to(device) for k, v in enc1.items()}
                with torch.no_grad():
                    out1 = model.generate(**enc1, **kw)
                hyps.extend(tok.batch_decode(out1.sequences, skip_special_tokens=True))
                if hasattr(out1, "sequences_scores") and out1.sequences_scores is not None:
                    scores.extend([float(x) for x in out1.sequences_scores.cpu().tolist()])
                else:
                    scores.append(0.0)
            if (bi + 1) % 10 == 0 or bi + 1 == n_batches:
                elapsed = time.perf_counter() - t0
                rate = (bi + 1) / max(1e-6, elapsed)
                eta = (n_batches - bi - 1) / max(1e-6, rate)
                log(f"    {tag} batch {bi+1}/{n_batches} ({100*(bi+1)/n_batches:.0f}%) eta~{eta:.0f}s")
            continue
        hyps.extend(tok.batch_decode(out.sequences, skip_special_tokens=True))
        if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
            scores.extend([float(x) for x in out.sequences_scores.cpu().tolist()])
        else:
            scores.extend([0.0] * len(batch))
        if (bi + 1) % 20 == 0 or bi + 1 == n_batches:
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
            lens = {nm: len(toks(systems[nm][i])) for nm in names}
            med = sorted(lens.values())[len(lens) // 2]
            best = min(names, key=lambda nm: abs(lens[nm] - med))
        else:
            best = names[0]
        out.append(systems[best][i])
    return out


def phase_stronger_student(t_src: list[str], t_ref: list[str]) -> dict:
    """Download NLLB-1.3B (and distilled if full fails), eval, ensemble with opus cache."""
    log("=== Phase 1: stronger student (NLLB-1.3B) ===")
    free_gpu()

    results = {}
    systems: dict[str, list[str]] = {}
    score_map: dict[str, list[float]] = {}
    student_meta = {"tried": [], "used": None, "vram_ok": False}

    # Prefer full 1.3B; fall back to distilled-1.3B
    candidates = [
        ("facebook/nllb-200-1.3B", NLLB_13, "nllb13"),
        ("facebook/nllb-200-distilled-1.3B", NLLB_13_DIST, "nllb13d"),
    ]
    chosen_dir = None
    chosen_tag = None
    for repo, dest, tag in candidates:
        student_meta["tried"].append(repo)
        try:
            ensure_model(repo, dest)
            # smoke: can we load in fp16?
            free_gpu()
            import torch
            from transformers import AutoModelForSeq2SeqLM

            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            m = AutoModelForSeq2SeqLM.from_pretrained(
                str(dest), local_files_only=True, torch_dtype=dtype
            )
            m.to("cuda" if torch.cuda.is_available() else "cpu")
            free, total = torch.cuda.mem_get_info() if torch.cuda.is_available() else (0, 0)
            log(f"  smoke load {dest.name} ok free={free//1024//1024}MB")
            del m
            free_gpu()
            chosen_dir, chosen_tag = dest, tag
            student_meta["used"] = repo
            student_meta["vram_ok"] = True
            break
        except Exception as e:
            log(f"  skip {repo}: {e}")
            free_gpu()
            continue

    if chosen_dir is None:
        log("  NLLB-1.3B unavailable — will use 600M only for ensemble baseline")
        student_meta["used"] = "facebook__nllb-200-distilled-600M (fallback)"
        chosen_dir, chosen_tag = NLLB_600, "nllb600"
        student_meta["vram_ok"] = True

    # Decode new student on TEST
    bs = 4 if "1.3" in chosen_dir.name else 8
    nh, ns = decode_one(
        chosen_dir,
        chosen_tag,
        t_src,
        nllb_src="deu_Latn",
        beams=5,
        length_penalty=1.0,
        batch_size=bs,
        cache_key=f"test_{chosen_tag}_b5_lp1.0",
        use_fp16=True,
    )
    systems[chosen_tag] = nh
    score_map[chosen_tag] = ns
    results[chosen_tag] = {"sacrebleu": sacre(nh, t_ref), "chrf": chrf(nh, t_ref)}
    log(f"  {chosen_tag} TEST sacre={results[chosen_tag]['sacrebleu']}")

    # Load cached opus (no re-decode if present)
    oh, oscores = decode_one(
        OPUS,
        "opus",
        t_src,
        beams=5,
        length_penalty=1.0,
        batch_size=16,
        cache_key="test_opus_b5_lp1.0",
    )
    systems["opus_b5"] = oh
    score_map["opus_b5"] = oscores
    results["opus_b5"] = {"sacrebleu": sacre(oh, t_ref), "chrf": chrf(oh, t_ref)}

    # Also bestcfg if cache exists
    oh9, os9 = decode_one(
        OPUS,
        "opus",
        t_src,
        beams=5,
        length_penalty=0.9,
        batch_size=16,
        cache_key="test_opus_b5_lp0.9",
    )
    systems["opus_bestcfg"] = oh9
    score_map["opus_bestcfg"] = os9
    results["opus_bestcfg"] = {"sacrebleu": sacre(oh9, t_ref), "chrf": chrf(oh9, t_ref)}

    # 600M for comparison if different
    if chosen_tag != "nllb600" and NLLB_600.exists():
        n6h, n6s = decode_one(
            NLLB_600,
            "nllb600",
            t_src,
            nllb_src="deu_Latn",
            beams=5,
            length_penalty=1.0,
            batch_size=8,
            cache_key="test_nllb_b5_lp1.0",
        )
        systems["nllb600"] = n6h
        score_map["nllb600"] = n6s
        results["nllb600"] = {"sacrebleu": sacre(n6h, t_ref), "chrf": chrf(n6h, t_ref)}

    # Offline ensembles
    for mode in ("gen_score", "length_mid", "oracle"):
        hyps = offline_pick(
            systems, score_map, mode, t_ref if mode == "oracle" else None
        )
        key = f"ens_{mode}"
        results[key] = {"sacrebleu": sacre(hyps, t_ref), "chrf": chrf(hyps, t_ref)}
        log(f"  {key} sacre={results[key]['sacrebleu']}")

    # 2-system ens: opus + strong student only
    two = {k: systems[k] for k in systems if k in (chosen_tag, "opus_b5", "opus_bestcfg")}
    two_sc = {k: score_map[k] for k in two}
    for mode in ("gen_score", "oracle"):
        hyps = offline_pick(two, two_sc, mode, t_ref if mode == "oracle" else None)
        key = f"ens2_{mode}"
        results[key] = {"sacrebleu": sacre(hyps, t_ref), "chrf": chrf(hyps, t_ref)}
        log(f"  {key} sacre={results[key]['sacrebleu']}")

    product_keys = [k for k in results if "oracle" not in k]
    best_name = max(product_keys, key=lambda k: results[k]["sacrebleu"])
    return {
        "student": student_meta,
        "results": results,
        "systems_keys": list(systems.keys()),
        "best_product": {
            "name": best_name,
            "sacrebleu": results[best_name]["sacrebleu"],
        },
        "oracle": results.get("ens_oracle", {}).get("sacrebleu"),
        "chosen_tag": chosen_tag,
        "chosen_dir": str(chosen_dir),
    }


def careful_ft_v4(
    max_train: int = 200_000,
    max_steps: int = 12_000,
    batch_size: int = 8,
    lr: float = 1e-5,
    val_every: int = 400,
    patience: int = 5,
    holdout: int = 2000,
) -> dict:
    """
    Longer careful FT with early-stop that tracks real news better:
    - Hold out 2k from train for early-stop (WMT 'validation' mismatched test in v3)
    - Lower LR, longer patience, freeze bottom encoder
    - Only ship if holdout improves over base on same holdout
    """
    import torch
    from datasets import load_dataset
    from torch.utils.data import DataLoader
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    log("=== Phase 2: careful FT v4 (train-holdout early-stop) ===")
    log(
        f"  max_steps={max_steps} lr={lr} val_every={val_every} "
        f"patience={patience} holdout={holdout}"
    )
    free_gpu()
    tok = AutoTokenizer.from_pretrained(str(OPUS), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(OPUS), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    enc_layers = list(model.model.encoder.layers)
    freeze_n = max(1, (2 * len(enc_layers)) // 3)  # freeze more than v3
    for layer in enc_layers[:freeze_n]:
        for p in layer.parameters():
            p.requires_grad = False
    log(f"  froze first {freeze_n}/{len(enc_layers)} encoder layers")

    train = load_dataset("wmt/wmt14", "de-en", split="train")
    n = min(max_train + holdout, len(train))
    # stride sample for diversity
    stride = max(1, len(train) // n)
    idxs = list(range(0, len(train), stride))[:n]
    all_pairs = [
        (train[int(i)]["translation"]["de"], train[int(i)]["translation"]["en"])
        for i in idxs
    ]
    # last holdout reserved for early-stop (not used in training)
    hold_pairs = all_pairs[-holdout:]
    train_pairs = all_pairs[:-holdout]
    log(f"  train={len(train_pairs)} holdout={len(hold_pairs)}")

    # baseline holdout score (base opus) — must beat this to ship
    model.eval()
    base_hyps = []
    hs = [p[0] for p in hold_pairs]
    hr = [p[1] for p in hold_pairs]
    for i in range(0, len(hs), 12):
        batch = hs[i : i + 12]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            gen = model.generate(
                **enc, max_new_tokens=160, num_beams=4, early_stopping=True
            )
        base_hyps.extend(tok.batch_decode(gen, skip_special_tokens=True))
    base_hold = sacre(base_hyps, hr)
    log(f"  BASE holdout sacre={base_hold}")

    def collate(batch):
        srcs = [b[0] for b in batch]
        tgts = [b[1] for b in batch]
        return tok(
            srcs,
            text_target=tgts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        )

    loader = DataLoader(
        train_pairs, batch_size=batch_size, shuffle=True, collate_fn=collate
    )
    opt = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=0.01,
    )
    sched = get_linear_schedule_with_warmup(opt, 300, max_steps)

    def eval_hold() -> float:
        model.eval()
        hyps = []
        for i in range(0, len(hs), 12):
            batch = hs[i : i + 12]
            enc = tok(
                batch, return_tensors="pt", padding=True, truncation=True, max_length=192
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.no_grad():
                gen = model.generate(
                    **enc, max_new_tokens=160, num_beams=4, early_stopping=True
                )
            hyps.extend(tok.batch_decode(gen, skip_special_tokens=True))
        model.train()
        return sacre(hyps, hr)

    best_val = base_hold  # must beat base
    best_state = None
    bad = 0
    step = 0
    losses: list[float] = []
    history: list[dict] = []
    model.train()
    t0 = time.perf_counter()
    while step < max_steps:
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            if "labels" in batch:
                batch["labels"][batch["labels"] == tok.pad_token_id] = -100
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                filter(lambda p: p.requires_grad, model.parameters()), 1.0
            )
            opt.step()
            sched.step()
            opt.zero_grad()
            losses.append(float(loss.item()))
            step += 1
            if step % 200 == 0:
                log(f"  step {step}/{max_steps} loss={sum(losses[-200:])/200:.4f}")
            if step % val_every == 0 or step == max_steps:
                vs = eval_hold()
                history.append({"step": step, "holdout_sacre": vs, "base": base_hold})
                delta = round(vs - base_hold, 2)
                log(f"  HOLD step {step} sacre={vs} (base={base_hold} Δ={delta})")
                if vs > best_val + 0.05:
                    best_val = vs
                    bad = 0
                    best_state = {
                        k: v.detach().cpu().clone() for k, v in model.state_dict().items()
                    }
                    log(f"  ** new best holdout {best_val}")
                else:
                    bad += 1
                    log(f"  no improve ({bad}/{patience})")
                    if bad >= patience:
                        log("  early stop")
                        step = max_steps
                        break
            if step >= max_steps:
                break

    improved = best_state is not None and best_val > base_hold + 0.05
    if improved and best_state is not None:
        model.load_state_dict(best_state)
        log(f"  restored best holdout={best_val}")
        FT_OUT.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(FT_OUT))
        tok.save_pretrained(str(FT_OUT))
        log(f"  saved {FT_OUT}")
    else:
        log(
            f"  NO SHIP: holdout never beat base+0.05 "
            f"(best={best_val} base={base_hold}) — keep base opus"
        )

    # Full TEST only if improved (or always measure best if we have state)
    test_score = None
    if improved and best_state is not None:
        model.eval()
        t_src, t_ref = load_wmt("test")
        hyps = []
        for i in range(0, len(t_src), 12):
            batch = t_src[i : i + 12]
            enc = tok(
                batch, return_tensors="pt", padding=True, truncation=True, max_length=192
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.no_grad():
                gen = model.generate(
                    **enc, max_new_tokens=160, num_beams=5, early_stopping=True
                )
            hyps.extend(tok.batch_decode(gen, skip_special_tokens=True))
        test_score = {
            "sacrebleu": sacre(hyps, t_ref),
            "chrf": chrf(hyps, t_ref),
        }
        # cache FT hyps
        (CACHE / "test_ft_v4_b5_lp1.0.json").write_text(
            json.dumps({"hyps": hyps, "scores": [0.0] * len(hyps), "tag": "ft_v4"}),
            encoding="utf-8",
        )
        log(f"  FT v4 TEST sacre={test_score['sacrebleu']}")
    del model
    free_gpu()
    return {
        "steps_ran": step if step < max_steps else max_steps,
        "base_holdout": base_hold,
        "best_holdout": best_val,
        "improved": improved,
        "shipped": improved,
        "history": history,
        "path": str(FT_OUT) if improved else None,
        "test": test_score,
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "lr": lr,
        "train_pairs": len(train_pairs),
        "protocol": "train-holdout early-stop; only ship if beat base holdout",
        "prior_v3_lesson": "WMT val 35.76 but test 33.41 — do not early-stop on WMT val alone",
    }


def write_report(phase1: dict, phase2: dict, elapsed: float) -> None:
    results = dict(phase1.get("results") or {})
    if phase2.get("test"):
        results["ft_v4"] = phase2["test"]
        # re-ensemble if FT shipped and we have caches
        if phase2.get("shipped"):
            try:
                t_src, t_ref = load_wmt("test")
                systems = {}
                scores = {}
                for key, cache_name in [
                    ("opus_b5", "test_opus_b5_lp1.0"),
                    (phase1.get("chosen_tag") or "nllb13", f"test_{phase1.get('chosen_tag')}_b5_lp1.0"),
                    ("ft_v4", "test_ft_v4_b5_lp1.0"),
                ]:
                    p = CACHE / f"{cache_name}.json"
                    if p.exists():
                        d = json.loads(p.read_text(encoding="utf-8"))
                        systems[key] = d["hyps"]
                        scores[key] = d.get("scores", [0.0] * len(d["hyps"]))
                if len(systems) >= 2:
                    for mode in ("gen_score", "oracle"):
                        hyps = offline_pick(
                            systems, scores, mode, t_ref if mode == "oracle" else None
                        )
                        results[f"ens_ft_{mode}"] = {
                            "sacrebleu": sacre(hyps, t_ref),
                            "chrf": chrf(hyps, t_ref),
                        }
            except Exception as e:
                log(f"  re-ensemble skip: {e}")

    product_keys = [k for k in results if "oracle" not in k]
    best_name = max(product_keys, key=lambda k: results[k]["sacrebleu"]) if product_keys else "?"
    best_s = results[best_name]["sacrebleu"] if product_keys else 0.0
    oracle_keys = [k for k in results if "oracle" in k]
    oracle_s = max((results[k]["sacrebleu"] for k in oracle_keys), default=None)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "D1D38A fixed",
        "path": "stronger student + careful FT (NOT 600M beam tweaks)",
        "phase1_student": phase1,
        "phase2_ft": {
            k: v
            for k, v in phase2.items()
            if k != "history" or True
        },
        "results": results,
        "best_product": {"name": best_name, "sacrebleu": best_s},
        "oracle_sacrebleu": oracle_s,
        "gaps": {
            "best_to_40": round(MID - best_s, 2),
            "best_to_48": round(STRETCH - best_s, 2),
            "oracle_to_40": round(MID - oracle_s, 2) if oracle_s else None,
        },
        "mid40_cleared": best_s >= MID,
        "pct_of_mid40": round(100 * best_s / MID, 1),
        "chat_hybrid_prior": 48.74,
        "elapsed_s": round(elapsed, 1),
        "priors": {
            "best_product_was": 34.34,
            "opus_base": 33.88,
            "nllb600": 33.37,
            "ft_v3_test": 33.41,
            "oracle_was": 37.95,
        },
    }
    (REP / "m6_stronger_student_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = f"""# Stronger student + careful FT

**Built:** {report['built_utc']}  
**Law:** D1D38A  
**Elapsed:** {report['elapsed_s']}s  
**Policy:** No more beam tweaks on 600M-only pair.

## Phase 1 — NLLB-1.3B (or fallback)

| Field | Value |
|-------|-------|
| Tried | {phase1.get('student', {}).get('tried')} |
| Used | **{phase1.get('student', {}).get('used')}** |
| VRAM OK | {phase1.get('student', {}).get('vram_ok')} |

## Phase 2 — careful FT v4

| Field | Value |
|-------|------:|
| Base holdout | {phase2.get('base_holdout')} |
| Best holdout | {phase2.get('best_holdout')} |
| Shipped | **{phase2.get('shipped')}** |
| TEST sacre | {phase2.get('test', {}).get('sacrebleu') if phase2.get('test') else 'n/a (not shipped)'} |
| Protocol | train-holdout early-stop (not WMT val) |

v3 lesson: WMT val looked strong (35.76) but test regressed (33.41).

## Distance to DeepL mid-bar (~40)

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid | 40 | **{best_s}** (`{best_name}`) | **{report['gaps']['best_to_40']}** |
| Stretch | 48 | {best_s} | {report['gaps']['best_to_48']} |
| Oracle | — | {oracle_s} | to 40: {report['gaps']['oracle_to_40']} |
| % of mid-40 | | **{report['pct_of_mid40']}%** | |

Prior best product was **34.34**. Chat hybrid remains **48.74**.

## All systems

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
"""
    for k, v in sorted(results.items(), key=lambda x: -x[1]["sacrebleu"]):
        md += f"| {k} | **{v['sacrebleu']}** | {v.get('chrf', '—')} |\n"
    md += """
## Next if still < 40

1. Stronger teacher hyps (3.3B if VRAM/disk, or better news-domain data)
2. Quality parallel data (news-commentary + Europarl filtered), longer LoRA FT
3. Not more beam search on the same 600M pair
"""
    (REP / "STRONGER_STUDENT.md").write_text(md, encoding="utf-8")
    docs = ADA.parent / "docs"
    if docs.is_dir():
        (docs / "STRONGER_STUDENT.md").write_text(md, encoding="utf-8")
    log(f"BEST product {best_name} sacre={best_s} gap40={report['gaps']['best_to_40']}")


def main():
    t0 = time.perf_counter()
    log("=== Stronger student push (NLLB-1.3B + careful FT) ===")
    log("Policy: NOT more 600M beam tweaks")
    t_src, t_ref = load_wmt("test")
    log(f"WMT test n={len(t_src)}")

    phase1 = phase_stronger_student(t_src, t_ref)
    # Always run careful FT (quality path) — independent of 1.3B
    phase2 = careful_ft_v4(
        max_train=200_000,
        max_steps=12_000,
        batch_size=8,
        lr=1e-5,
        val_every=400,
        patience=5,
        holdout=2000,
    )
    write_report(phase1, phase2, time.perf_counter() - t0)
    log(f"elapsed {time.perf_counter()-t0:.0f}s")


if __name__ == "__main__":
    main()
