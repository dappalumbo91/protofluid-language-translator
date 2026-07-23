#!/usr/bin/env python3
"""Compare FSOT LLM judge modes: full vs hard-only hybrid."""
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


def toks(t):
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sent_bleu(h, r):
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


def load_rows(key, n):
    d = json.loads((CACHE / f"{key}.json").read_text(encoding="utf-8"))
    return d["rows"]


def main():
    j = json.loads(
        (ROOT / "pflt-Ada" / "data" / "fsot_qe_cache" / "llm_judge_qwen7b.json").read_text(
            encoding="utf-8"
        )
    )
    picks = j["picks"]
    hard = set(
        json.loads(
            (ROOT / "pflt-Ada" / "data" / "news_hard_sel_indices.json").read_text(
                encoding="utf-8"
            )
        )["indices"]
    )
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

    gen, full, hard_only = [], [], []
    win_e = lose_e = 0
    for i in range(n):
        gens = {}
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                gens[h] = max(gens.get(h, -1e9), float(s))
        p = max(gens, key=lambda h: gens[h])
        jh = picks.get(str(i), p)
        gen.append(p)
        full.append(jh)
        hard_only.append(jh if i in hard else p)
        if i not in hard and jh != p:
            if sent_bleu(jh, refs[i]) > sent_bleu(p, refs[i]) + 1e-9:
                win_e += 1
            elif sent_bleu(jh, refs[i]) < sent_bleu(p, refs[i]) - 1e-9:
                lose_e += 1

    for name, hyps in (
        ("gen", gen),
        ("llm_full", full),
        ("llm_hard_only", hard_only),
    ):
        sc = sacrebleu.corpus_bleu(hyps, [refs]).score
        print(f"{name}: sacre={sc:.2f}")
    print(f"easy_override win={win_e} lose={lose_e}")


if __name__ == "__main__":
    main()
