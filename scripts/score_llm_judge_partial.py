#!/usr/bin/env python3
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
    p = ROOT / "pflt-Ada" / "data" / "fsot_qe_cache" / "llm_judge_qwen7b.json"
    if not p.exists():
        print("no partial")
        return
    j = json.loads(p.read_text(encoding="utf-8"))
    picks = j.get("picks") or {}
    print("n_picks", len(picks), "partial", j.get("partial"))
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
    hyps = []
    for i in range(n):
        gens = {}
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                gens[h] = max(gens.get(h, -1e9), float(s))
        prod = max(gens, key=lambda h: gens[h])
        hyps.append(picks.get(str(i), prod))
    print("FSOT_pick_llm_partial sacre", round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2))
    judged = [int(k) for k in picks]
    win = lose = same = 0
    sum_p = sum_j = sum_o = 0.0
    for i in judged:
        gens = {}
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                gens[h] = max(gens.get(h, -1e9), float(s))
        prod = max(gens, key=lambda h: gens[h])
        ora = max(gens, key=lambda h: sent_bleu(h, refs[i]))
        pj = picks[str(i)]
        sp, sj, so = sent_bleu(prod, refs[i]), sent_bleu(pj, refs[i]), sent_bleu(ora, refs[i])
        sum_p += sp
        sum_j += sj
        sum_o += so
        if sj > sp + 1e-9:
            win += 1
        elif sj < sp - 1e-9:
            lose += 1
        else:
            same += 1
    m = max(1, len(judged))
    print(f"on_judged win_vs_prod={win} lose={lose} same={same} n={len(judged)}")
    print(f"mean_sb prod={sum_p/m:.4f} judge={sum_j/m:.4f} ora={sum_o/m:.4f}")


if __name__ == "__main__":
    main()
