#!/usr/bin/env python3
"""
M6 climb step 1: learn a light IBM-1 style phrase/unigram table from the
cached Tatoeba M6 pairs and inject high-support unigrams into densify.

Re-run m6_sentence_bleu.py after this to refresh BLEU-style bars.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
CACHE = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\m6_pairs_cache.jsonl"
)
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def main() -> None:
    if not CACHE.exists():
        raise SystemExit(f"missing {CACHE} — run m6_sentence_bleu.py first")

    co: dict[str, Counter] = defaultdict(Counter)
    src_c: Counter = Counter()
    n = 0
    with CACHE.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            st, rt = toks(r["src"]), toks(r["ref"])
            if not st or not rt:
                continue
            n += 1
            rc = Counter(rt)
            for s in st:
                src_c[s] += 1
                for t, c in rc.items():
                    co[s][t] += c

    phrase: dict[str, str] = {}
    for s, cnt in co.items():
        if src_c[s] < 4:
            continue
        t, c = cnt.most_common(1)[0]
        if c < 3 or t == s or len(t) > 40:
            continue
        # avoid mapping content words to function words too aggressively
        if t in {"the", "a", "an", "of", "to", "and"} and src_c[s] < 20:
            continue
        phrase[s] = t

    print(f"pairs={n} phrase_unigrams={len(phrase)}", flush=True)

    dens = DATA / "densify.tsv"
    # load existing to avoid huge dups (last wins in Ada score path anyway)
    existing: set[str] = set()
    if dens.exists():
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if p:
                    existing.add(p[0].lower())

    added = 0
    with dens.open("a", encoding="utf-8") as w:
        for k, v in phrase.items():
            # Only inject if not already present (keep densify product senses)
            if k in existing:
                continue
            w.write(f"{k}\t{v}\n")
            existing.add(k)
            added += 1
    print(f"densify +{added} new unigrams", flush=True)

    pt = DATA / "m6_phrase_table.tsv"
    with pt.open("w", encoding="utf-8") as w:
        for k, v in sorted(phrase.items(), key=lambda x: -src_c[x[0]])[:80_000]:
            w.write(f"{k}\t{v}\t{src_c[k]}\n")
    print(f"wrote {pt}", flush=True)


if __name__ == "__main__":
    main()
