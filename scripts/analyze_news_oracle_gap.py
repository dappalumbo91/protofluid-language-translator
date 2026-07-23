#!/usr/bin/env python3
"""Split WMT de-en gap into selection vs pool limits (cached hyps only)."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import sacrebleu
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
OUT = ROOT / "pflt-Ada" / "data" / "news_hard_sel_indices.json"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

KEYS = [
    "test_opus_b5_lp1.0",
    "test_opus_b8_lp1.0_exp",
    "test_opus_b8_ret3",
    "test_nllb13_b5_lp1.0",
    "test_nllb13_b8_lp1.0_exp",
    "test_nllb13_b8_ret3",
    "test_nllb13_b8_lp0.9",
    "test_nllb13_b8_lp1.1",
    "test_nllb13_b8_ret5",
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
    "test_nllb_b5_lp1.0",
    "test_nllb_b8_lp1.0",
    "test_nllb600_b8_ret3",
]


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


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


def load_rows(key: str, n: int):
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "hyps" in d and len(d["hyps"]) == n:
        return [
            {"hyps": [h], "scores": [s]}
            for h, s in zip(d["hyps"], d.get("scores", [0.0] * n))
        ]
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    return None


def main() -> None:
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    n = len(refs)
    rowsets = {k: load_rows(k, n) for k in KEYS}
    present = [k for k, v in rowsets.items() if v]
    print("systems", present)

    prod, oracle, pools = [], [], []
    hard = []
    pool_weak = 0
    for i in range(n):
        uniq = []
        seen = set()
        for k in present:
            for h, s in zip(rowsets[k][i]["hyps"], rowsets[k][i]["scores"]):
                if h not in seen:
                    seen.add(h)
                    uniq.append((float(s), h, k))
        pools.append(len(uniq))
        gen_h = max(uniq, key=lambda x: x[0])[1]
        or_h = max(uniq, key=lambda x: sent_bleu(x[1], refs[i]))[1]
        prod.append(gen_h)
        oracle.append(or_h)
        sb_g = sent_bleu(gen_h, refs[i])
        sb_o = sent_bleu(or_h, refs[i])
        if sb_o > sb_g + 0.05:
            hard.append(
                {
                    "i": i,
                    "dsb": round(sb_o - sb_g, 4),
                    "pool": len(uniq),
                    "gen": gen_h[:80],
                    "oracle": or_h[:80],
                }
            )
        if sb_o < 0.15:
            pool_weak += 1

    hard.sort(key=lambda x: -x["dsb"])
    ps = round(sacrebleu.corpus_bleu(prod, [refs]).score, 2)
    os_ = round(sacrebleu.corpus_bleu(oracle, [refs]).score, 2)
    rep = {
        "n": n,
        "systems": present,
        "product_gen_sacre": ps,
        "oracle_sacre": os_,
        "mean_pool": round(sum(pools) / n, 2),
        "selection_gap_count": len(hard),
        "selection_gap_pct": round(100 * len(hard) / n, 1),
        "pool_weak_oracle_sb_lt_0.15": pool_weak,
        "indices": [h["i"] for h in hard],
        "top50": hard[:50],
    }
    OUT.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in rep if k not in ("indices", "top50")}, indent=2))
    print("top dsb:", [h["dsb"] for h in hard[:10]])
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
