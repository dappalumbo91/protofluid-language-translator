#!/usr/bin/env python3
"""
FSOT encoder QE: NLLB mean-pool encoder cosine(src, hyp) over multi-hyp pool.

Ref-free. Ranks candidates that max-gen systematically misses (oracle always
has lower gen on gap sents). Caches scores for eval_news_deen_cached.py.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from datasets import load_dataset
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
OUT = ROOT / "pflt-Ada" / "data" / "fsot_qe_cache" / "nllb13_enc_cos.json"
MODEL = "facebook/nllb-200-1.3B"
SRC_LANG = "deu_Latn"
TGT_LANG = "eng_Latn"
KEYS = [
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
]


def load_rows(key: str, n: int):
    p = CACHE / f"{key}.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    return None


@torch.inference_mode()
def mean_pool(model, tokenizer, texts: List[str], lang: str, device: str, bs: int = 16):
    """Mean-pool encoder last hidden state (mask-aware)."""
    # NLLB: set src_lang for encoder-side
    tokenizer.src_lang = lang
    outs = []
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        enc = tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        ).to(device)
        h = model.get_encoder()(**enc).last_hidden_state  # [B,T,H]
        mask = enc["attention_mask"].unsqueeze(-1).float()
        pooled = (h * mask).sum(1) / mask.sum(1).clamp(min=1e-6)
        # L2 normalize
        pooled = torch.nn.functional.normalize(pooled, dim=-1)
        outs.append(pooled.cpu())
    return torch.cat(outs, dim=0)


def main() -> None:
    t0 = time.perf_counter()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} model={MODEL}", flush=True)

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(srcs)
    rowsets = [load_rows(k, n) for k in KEYS]
    assert all(rowsets), "missing hyp caches"

    print("loading model…", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device)
    model.eval()

    # unique hyp universe per sentence
    pools: List[List[str]] = []
    gens: List[Dict[str, float]] = []
    all_hyps_flat: List[Tuple[int, str]] = []
    for i in range(n):
        g: Dict[str, float] = {}
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                g[h] = max(g.get(h, -1e18), float(s))
        hyps = list(g.keys())
        pools.append(hyps)
        gens.append(g)
        for h in hyps:
            all_hyps_flat.append((i, h))

    print(f"n={n} total_hyp_slots={len(all_hyps_flat)}", flush=True)
    print("encoding sources…", flush=True)
    src_emb = mean_pool(model, tok, srcs, SRC_LANG, device, bs=24)

    # encode all hyps (can be many — batch)
    print("encoding hyps…", flush=True)
    hyp_texts = [h for _, h in all_hyps_flat]
    hyp_emb = mean_pool(model, tok, hyp_texts, TGT_LANG, device, bs=24)

    # cosine per (i,h)
    rows_out = []
    cursor = 0
    for i in range(n):
        hs = pools[i]
        m = len(hs)
        se = src_emb[i : i + 1]  # [1,H]
        he = hyp_emb[cursor : cursor + m]  # [m,H]
        cursor += m
        cos = (he @ se.T).squeeze(-1).tolist()  # since both normalized
        if isinstance(cos, float):
            cos = [cos]
        scores = {
            hs[j]: {
                "cos": float(cos[j]),
                "gen": float(gens[i][hs[j]]),
            }
            for j in range(m)
        }
        # pick variants
        best_gen = max(hs, key=lambda h: gens[i][h])
        best_cos = max(hs, key=lambda h: scores[h]["cos"])
        # blend z-scores within sentence
        gens_l = [gens[i][h] for h in hs]
        cos_l = [scores[h]["cos"] for h in hs]
        gmu, cmu = sum(gens_l) / m, sum(cos_l) / m
        gsd = math.sqrt(sum((x - gmu) ** 2 for x in gens_l) / m) or 1.0
        csd = math.sqrt(sum((x - cmu) ** 2 for x in cos_l) / m) or 1.0
        blend_picks = {}
        for lam in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0):
            best_h, best_v = hs[0], -1e18
            for h in hs:
                zg = (gens[i][h] - gmu) / gsd
                zc = (scores[h]["cos"] - cmu) / csd
                v = zg + lam * zc
                if v > best_v:
                    best_v, best_h = v, h
            blend_picks[str(lam)] = best_h
        rows_out.append(
            {
                "best_gen": best_gen,
                "best_cos": best_cos,
                "blend": blend_picks,
                "scores": scores,
            }
        )
        if (i + 1) % 200 == 0:
            print(f"  scored {i+1}/{n}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": MODEL,
        "method": "nllb_encoder_meanpool_cosine",
        "n": n,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "rows": rows_out,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {OUT} elapsed={payload['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    main()
