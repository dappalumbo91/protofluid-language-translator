#!/usr/bin/env python3
"""How much sacre if we correctly pick oracle on X% of hard selection gaps."""
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
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def toks(t: str):
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
    d = json.loads((CACHE / f"{key}.json").read_text(encoding="utf-8"))
    return d["rows"]


def main() -> None:
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    n = len(refs)
    keys = [
        "test_nllb33_b5_lp1.0",
        "test_nllb33_b8_lp1.0",
        "test_nllb33_b8_ret3",
        "test_nllb33_b8_ret5",
    ]
    rowsets = [load_rows(k, n) for k in keys]
    prod, ora = [], []
    for i in range(n):
        gens = {}
        pool = []
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                gens[h] = max(gens.get(h, -1e9), float(s))
                if h not in pool:
                    pool.append(h)
        prod.append(max(pool, key=lambda h: gens[h]))
        ora.append(max(pool, key=lambda h: sent_bleu(h, refs[i])))
    hard = json.loads(
        (ROOT / "pflt-Ada" / "data" / "news_hard_sel_indices.json").read_text(
            encoding="utf-8"
        )
    )
    idx = hard["indices"]
    print("product", round(sacrebleu.corpus_bleu(prod, [refs]).score, 2))
    print("oracle_nllb33", round(sacrebleu.corpus_bleu(ora, [refs]).score, 2))
    for frac in (0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0):
        k = int(len(idx) * frac)
        use = set(idx[:k])
        hyps = [ora[i] if i in use else prod[i] for i in range(n)]
        sc = sacrebleu.corpus_bleu(hyps, [refs]).score
        print(f"fix_{int(frac*100):3d}pct_hard sacre={sc:.2f}")


if __name__ == "__main__":
    main()
