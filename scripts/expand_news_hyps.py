#!/usr/bin/env python3
"""
B) Expand multi-hyp diversity for WMT14 de-en (sequential GPU, cache everything).

New configs (only if not cached):
  - nllb33 beams=10 lp=1.0 ret=1
  - nllb33 beams=8 lp=0.9 ret=1
  - nllb33 beams=8 lp=1.1 ret=1
  - nllb33 beams=8 lp=1.0 ret=5
  - nllb600 beams=8 lp=1.0 ret=3  (if model present)
  - opus beams=8 lp=1.0 ret=3

One model on GPU at a time. Writes pflt-Ada/data/hyp_cache/*.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADA = ROOT / "pflt-Ada"
CACHE = ADA / "data" / "hyp_cache"
CACHE.mkdir(parents=True, exist_ok=True)

MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
NLLB33 = MODELS / "facebook__nllb-200-3.3B"
NLLB13 = MODELS / "facebook__nllb-200-1.3B"
NLLB600 = MODELS / "facebook__nllb-200-distilled-600M"
OPUS = MODELS / "Helsinki-NLP__opus-mt-de-en"

# (model_dir, tag, nllb_src, beams, lp, ret, cache_key, batch)
# Order: smaller/faster first (stable), then one high-value 3.3B multi-return.
# (b10/lp variants dropped — same model family as b8, costly 3.3B reloads.)
JOBS = [
    (OPUS, "opus_b8r3", None, 8, 1.0, 3, "test_opus_b8_ret3", 4),
    (NLLB600, "nllb600_b8r3", "deu_Latn", 8, 1.0, 3, "test_nllb600_b8_ret3", 2),
    (NLLB13, "nllb13_b8_lp09", "deu_Latn", 8, 0.9, 1, "test_nllb13_b8_lp0.9", 2),
    (NLLB13, "nllb13_b8_lp11", "deu_Latn", 8, 1.1, 1, "test_nllb13_b8_lp1.1", 2),
    (NLLB13, "nllb13_b8r5", "deu_Latn", 8, 1.0, 5, "test_nllb13_b8_ret5", 1),
    (NLLB33, "nllb33_b8r5", "deu_Latn", 8, 1.0, 5, "test_nllb33_b8_ret5", 1),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def free_gpu() -> None:
    import gc

    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        f, t = torch.cuda.mem_get_info()
        log(f"  GPU free {f // 1024 // 1024}/{t // 1024 // 1024} MB")


def load_wmt_test():
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    return [ex["translation"]["de"] for ex in ds]


def cache_ok(key: str, n: int, num_return: int) -> bool:
    p = CACHE / f"{key}.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text(encoding="utf-8"))
    # incomplete checkpoint must not count as done
    if d.get("partial"):
        return False
    if "rows" in d and d.get("n_src") == n:
        rows = d["rows"]
        if len(rows) == n and all(len(r.get("hyps", [])) >= num_return for r in rows):
            return True
    if "hyps" in d and len(d["hyps"]) == n and num_return == 1 and not d.get("partial"):
        return True
    return False


def decode_job(
    model_dir: Path,
    tag: str,
    srcs: list[str],
    *,
    nllb_src: str | None,
    beams: int,
    lp: float,
    ret: int,
    cache_key: str,
    batch_size: int,
) -> None:
    if not model_dir.is_dir():
        log(f"  SKIP missing model {model_dir}")
        return
    if cache_ok(cache_key, len(srcs), ret):
        log(f"  cache hit {cache_key}")
        return

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    free_gpu()
    log(
        f"  decode {model_dir.name} b={beams} lp={lp} ret={ret} n={len(srcs)} key={cache_key}"
    )
    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True, torch_dtype=dtype
        )
    except Exception:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True
        )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src

    path = CACHE / f"{cache_key}.json"
    rows: list = []
    start_i = 0
    # Resume partial checkpoint
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if d.get("partial") and isinstance(d.get("rows"), list):
                rows = d["rows"]
                start_i = len(rows)
                if start_i >= len(srcs):
                    log(f"  resume complete {cache_key}")
                    return
                log(f"  resume {cache_key} from {start_i}/{len(srcs)}")
        except Exception:
            rows = []
            start_i = 0

    t0 = time.perf_counter()
    n_batches = (len(srcs) + batch_size - 1) // batch_size
    for bi, i in enumerate(range(0, len(srcs), batch_size)):
        if i < start_i:
            continue
        batch = srcs[i : i + batch_size]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        kw = {
            "max_new_tokens": 160,
            "num_beams": max(beams, ret),
            "length_penalty": lp,
            "early_stopping": True,
            "return_dict_in_generate": True,
            "output_scores": True,
            "num_return_sequences": ret,
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
            log("  OOM → batch=1")
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
                hyps = tok.batch_decode(out1.sequences, skip_special_tokens=True)
                sc = (
                    [float(x) for x in out1.sequences_scores.cpu().tolist()]
                    if getattr(out1, "sequences_scores", None) is not None
                    else [0.0] * len(hyps)
                )
                rows.append({"hyps": hyps, "scores": sc})
            continue
        hyps_flat = tok.batch_decode(out.sequences, skip_special_tokens=True)
        sc_flat = (
            [float(x) for x in out.sequences_scores.cpu().tolist()]
            if getattr(out, "sequences_scores", None) is not None
            else [0.0] * len(hyps_flat)
        )
        for j in range(len(batch)):
            sl = slice(j * ret, (j + 1) * ret)
            rows.append({"hyps": hyps_flat[sl], "scores": sc_flat[sl]})
        done = len(rows)
        if done % 50 == 0 or done == len(srcs):
            elapsed = time.perf_counter() - t0
            rate = max(1, done - start_i) / max(1e-6, elapsed)
            eta = (len(srcs) - done) / max(1e-6, rate)
            log(f"    {tag} {done}/{len(srcs)} eta~{eta:.0f}s")
        # checkpoint every 200 sentences
        if done % 200 == 0:
            path.write_text(
                json.dumps(
                    {
                        "rows": rows,
                        "n_src": len(srcs),
                        "num_return": ret,
                        "tag": tag,
                        "beams": beams,
                        "lp": lp,
                        "partial": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            log(f"  checkpoint {done}/{len(srcs)} → {path.name}")

    del model
    free_gpu()
    path.write_text(
        json.dumps(
            {
                "rows": rows,
                "n_src": len(srcs),
                "num_return": ret,
                "tag": tag,
                "beams": beams,
                "lp": lp,
                "partial": False,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    log(f"  saved {path.name}")


def main() -> None:
    log("=== Expand news multi-hyp diversity ===")
    srcs = load_wmt_test()
    log(f"n={len(srcs)}")
    for model_dir, tag, nllb_src, beams, lp, ret, key, bs in JOBS:
        decode_job(
            model_dir,
            tag,
            srcs,
            nllb_src=nllb_src,
            beams=beams,
            lp=lp,
            ret=ret,
            cache_key=key,
            batch_size=bs,
        )
    log("DONE expand")


if __name__ == "__main__":
    main()
