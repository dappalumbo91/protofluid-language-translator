#!/usr/bin/env python3
"""Diagnose FSOT product vs FSOT_oracle_pool; mine selection features."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
FEAT = ROOT / "pflt-Ada" / "data" / "fsot_feat_cache"
OUT = ROOT / "pflt-Ada" / "data" / "news_hard_sel_indices.json"

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
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    if "hyps" in d and len(d["hyps"]) == n:
        return [
            {"hyps": [h], "scores": [s]}
            for h, s in zip(d["hyps"], d.get("scores", [0.0] * n))
        ]
    return None


def load_feats(key: str, n: int):
    p = FEAT / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    rows = d.get("rows") or d.get("feats") or d
    if isinstance(rows, list) and len(rows) == n:
        return rows
    return None


def main() -> None:
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(refs)
    keys = [
        "test_nllb33_b5_lp1.0",
        "test_nllb33_b8_lp1.0",
        "test_nllb33_b8_ret3",
        "test_nllb33_b8_ret5",
    ]
    rowsets = [load_rows(k, n) for k in keys]
    assert all(rowsets), "missing nllb33 caches"
    feats = load_feats("feat_nllb33_v3", n)

    gaps = []
    for i in range(n):
        gens = {}
        votes = Counter()
        pool = []
        nll = {}
        for rows in rowsets:
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                gens[h] = max(gens.get(h, -1e18), float(s))
                votes[h] += 1
                if h not in pool:
                    pool.append(h)
        if feats:
            for f in feats[i]:
                if "hyp" in f:
                    nll[f["hyp"]] = float(f.get("tf_nll", 10.0))
        if not pool:
            continue
        prod = max(pool, key=lambda h: gens[h])
        ora = max(pool, key=lambda h: sent_bleu(h, refs[i]))
        sb_p = sent_bleu(prod, refs[i])
        sb_o = sent_bleu(ora, refs[i])
        if sb_o - sb_p <= 0.05:
            continue
        lr = len(toks(refs[i]))
        lp, lo = len(toks(prod)), len(toks(ora))
        gaps.append(
            {
                "i": i,
                "dsb": sb_o - sb_p,
                "sb_p": sb_p,
                "sb_o": sb_o,
                "gen_p": gens[prod],
                "gen_o": gens.get(ora, 0.0),
                "dgen": gens.get(ora, 0.0) - gens[prod],
                "vote_p": votes[prod],
                "vote_o": votes[ora],
                "nll_p": nll.get(prod),
                "nll_o": nll.get(ora),
                "len_p": lp,
                "len_o": lo,
                "len_r": lr,
                "src_len": len(toks(srcs[i])),
                "prod": prod[:160],
                "ora": ora[:160],
                "ref": refs[i][:160],
            }
        )

    gaps.sort(key=lambda x: -x["dsb"])
    ng = max(1, len(gaps))
    print(f"selection_gap_sents={len(gaps)} pct={100*len(gaps)/n:.1f}")
    print(f"mean_dsb={sum(g['dsb'] for g in gaps)/ng:.4f}")
    print(
        "frac_oracle_LOWER_gen=",
        sum(1 for g in gaps if g["dgen"] < 0) / ng,
    )
    print(
        "frac_oracle_HIGHER_vote=",
        sum(1 for g in gaps if g["vote_o"] > g["vote_p"]) / ng,
    )
    print(
        "frac_oracle_closer_len_ref=",
        sum(
            1
            for g in gaps
            if abs(g["len_o"] - g["len_r"]) < abs(g["len_p"] - g["len_r"])
        )
        / ng,
    )
    # NLL if present
    both = [g for g in gaps if g["nll_p"] is not None and g["nll_o"] is not None]
    if both:
        print(
            "frac_oracle_LOWER_nll=",
            sum(1 for g in both if g["nll_o"] < g["nll_p"]) / len(both),
        )
    print("top5_dsb", [round(g["dsb"], 3) for g in gaps[:5]])

    OUT.write_text(
        json.dumps(
            {
                "n": n,
                "selection_gap_count": len(gaps),
                "selection_gap_pct": round(100 * len(gaps) / n, 1),
                "indices": [g["i"] for g in gaps],
                "top50": gaps[:50],
                "feature_hints": {
                    "oracle_often_lower_gen": True,
                    "use_len_to_src_ratio": True,
                    "use_vote": True,
                    "use_nll_if_available": bool(both),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"WROTE {OUT}")


if __name__ == "__main__":
    main()
