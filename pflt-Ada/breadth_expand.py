#!/usr/bin/env python3
"""
Expand language breadth under FSOT solidify rules: add high-mass codes
from expanded_gold that are not yet in the Ada catalog.

Tier-1 add this pass: hy (Armenian), fro/frm (Old/Middle French),
goh/gmh (Old/Middle High German) — historical depth + breadth toward DeepL band.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA = Path(__file__).resolve().parent
DATA = ADA / "data"

NEW_LANGS = {"hy", "fro", "frm", "goh", "gmh", "got", "non", "sga"}
# got/non/sga may already be present; re-mine adds mass

META = re.compile(
    r"(dative|genitive|accusative|nominative|singular of|plural of|"
    r"inflection|participle|the compound|heritage_flow|panel_resonance)",
    re.I,
)


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 64 or META.search(g):
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    return head[:48] if head else ""


def clean_form(w: str) -> str:
    w = (w or "").replace("\t", " ").strip()
    if not w or len(w) > 64 or "_" in w:
        return ""
    return w


def main() -> None:
    gold_path = DATA / "gold_core.tsv"
    existing = set()
    rows = []
    if gold_path.exists():
        for line in gold_path.open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                existing.add(f"{p[0]}|{p[1].lower()}")
                rows.append(line if line.endswith("\n") else line + "\n")

    added = Counter()
    src = ROOT / "data" / "expanded_gold.jsonl"
    if not src.exists():
        print("no expanded_gold.jsonl")
        return
    with src.open(encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            lang = (o.get("source_lang") or "").lower().strip()
            if lang not in NEW_LANGS or o.get("is_name"):
                continue
            word = clean_form(o.get("source_word") or "")
            gloss = clean_gloss(o.get("target_word") or o.get("meaning_key") or "")
            if not word or not gloss:
                continue
            key = f"{lang}|{word.lower()}"
            if key in existing:
                continue
            existing.add(key)
            rows.append(f"{lang}\t{word}\t{gloss}\n")
            added[lang] += 1

    gold_path.write_text("".join(rows), encoding="utf-8")
    print("appended", dict(added), "gold_lines", len(rows))

    # append bare forms into densify + train for product/open mass
    dens = DATA / "densify.tsv"
    train = DATA / "train_mass.tsv"
    dens_seen = set()
    if dens.exists():
        for line in dens.open(encoding="utf-8", errors="replace"):
            p = line.split("\t", 1)
            if p:
                dens_seen.add(p[0].lower().strip())
    new_d = []
    for line in rows:
        p = line.rstrip("\n").split("\t")
        if len(p) < 3:
            continue
        lang, word, gloss = p[0], p[1], p[2]
        if lang not in added:
            continue
        fl = word.lower()
        if fl not in dens_seen:
            dens_seen.add(fl)
            new_d.append(f"{fl}\t{gloss}\n")
    if new_d:
        with dens.open("a", encoding="utf-8") as w:
            w.writelines(new_d)
        # also train
        if train.exists():
            with train.open("a", encoding="utf-8") as w:
                w.writelines(new_d)
        # invalidate pickle cache
        cache = DATA / "train_cache.pkl"
        if cache.exists():
            cache.unlink()
    print("densify+train appended", len(new_d))


if __name__ == "__main__":
    main()
