#!/usr/bin/env python3
"""Score densify path on public WMT14 de-en test (industry-style bar)."""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from datasets import load_dataset

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
DATA = Path(__file__).resolve().parent / "data"


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def load_maps():
    uni, bi, dens = {}, {}, {}
    for path, d in (
        (DATA / "m6_phrase_table.tsv", uni),
        (DATA / "m6_bigram_table.tsv", bi),
    ):
        if path.exists():
            for line in path.open(encoding="utf-8", errors="replace"):
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    d[p[0]] = p[1]
    dens_path = DATA / "densify.tsv"
    if dens_path.exists():
        for line in dens_path.open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                dens[p[0].lower()] = p[1][:48]
    return uni, bi, dens


def decode(src, uni, bi, dens):
    tokens = toks(src)
    out = []
    mapped = 0
    i = 0
    while i < len(tokens):
        hit = False
        for L in range(min(5, len(tokens) - i), 1, -1):
            ph = " ".join(tokens[i : i + L])
            if ph in bi:
                out.extend(bi[ph].split())
                mapped += L
                i += L
                hit = True
                break
        if hit:
            continue
        if i + 1 < len(tokens):
            bg = tokens[i] + " " + tokens[i + 1]
            if bg in bi:
                out.extend(bi[bg].split())
                mapped += 2
                i += 2
                continue
        tok = tokens[i]
        g = uni.get(tok) or dens.get(tok)
        if g:
            out.append(g.split()[0].lower())
            mapped += 1
        else:
            out.append(tok)
        i += 1
    return " ".join(out), mapped / max(1, len(tokens))


def ngrams(t, n):
    return Counter(tuple(t[i : i + n]) for i in range(len(t) - n + 1))


def bleu(hyps, refs):
    precs = []
    hl = rl = 0
    for n in range(1, 5):
        m = tot = 0
        for h, r in zip(hyps, refs):
            if len(h) < n:
                continue
            hc, rc = ngrams(h, n), ngrams(r, n)
            for ng, c in hc.items():
                m += min(c, rc.get(ng, 0))
                tot += c
        precs.append((m + 1) / (tot + 1))
    for h, r in zip(hyps, refs):
        hl += len(h)
        rl += len(r)
    bp = 1.0 if hl > rl else math.exp(1 - rl / max(1, hl))
    return 100 * bp * math.exp(sum(math.log(p) for p in precs) / 4), 100 * precs[0], bp


def main():
    uni, bi, dens = load_maps()
    print("maps", len(uni), len(bi), len(dens), flush=True)
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    hyps, refs, covs = [], [], []
    for ex in ds:
        de = ex["translation"]["de"]
        en = ex["translation"]["en"]
        hyp, cov = decode(de, uni, bi, dens)
        hyps.append(toks(hyp))
        refs.append(toks(en))
        covs.append(cov)
    b4, b1, bp = bleu(hyps, refs)
    cov = 100 * sum(covs) / len(covs)
    print(
        f"WMT14 de-en test n={len(hyps)} BLEU4={b4:.2f} BLEU1={b1:.2f} "
        f"bp={bp:.3f} cov={cov:.1f}%",
        flush=True,
    )
    try:
        import sacrebleu

        hyp_s = [" ".join(h) for h in hyps]
        ref_s = [" ".join(r) for r in refs]
        print("sacreBLEU", round(sacrebleu.corpus_bleu(hyp_s, [ref_s]).score, 2), flush=True)
    except Exception as e:
        print("sacre", e, flush=True)


if __name__ == "__main__":
    main()
