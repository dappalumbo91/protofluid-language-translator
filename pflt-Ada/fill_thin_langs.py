#!/usr/bin/env python3
"""
Fill thin language gaps (n<50 eval) before any Hugging Face packaging.

Targets (current thin set):
  hit, pal, pro, mga, osp, orv, roa-opt
Also thicken borderline uga if under 100.

Sources:
  - Kaikki full dumps on D: (correct multi-word URL stems)
  - Local expanded_gold.jsonl mine for codes without Kaikki

Then append gold/train/eval/densify and leave push_universal to solidify.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ADA = Path(__file__).resolve().parent
ROOT = ADA.parent
sys.path.insert(0, str(ADA))

spec = importlib.util.spec_from_file_location("d20", ADA / "download_next20_languages.py")
d20 = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(d20)

DRIVE = d20.DRIVE
INGEST = d20.INGEST
DATA = ADA / "data"
TARGET_EVAL = 200  # solid bar: n>=50; aim 200 when data allows
MAX_ROWS = 80_000

# (iso, kaikki_page_name or None, file_stem override or None)
# file_stem: if None, spaces dropped from page name; hyphens dropped for SerboCroatian-style
THIN_TARGETS: list[tuple[str, str | None, str | None]] = [
    ("osp", "Old Spanish", "OldSpanish"),
    ("orv", "Old East Slavic", "OldEastSlavic"),
    ("roa-opt", "Old Galician-Portuguese", "OldGalician-Portuguese"),
    ("mga", "Middle Irish", "MiddleIrish"),
    ("pro", "Old Occitan", "OldOccitan"),
    ("uga", "Ugaritic", "Ugaritic"),  # borderline thicken
    # Pahlavi / Middle Persian often listed as:
    ("pal", "Middle Persian", "MiddlePersian"),
    # Hittite — try Kaikki; fall back to local mine
    ("hit", "Hittite", "Hittite"),
]

META = re.compile(
    r"(dative|genitive|accusative|nominative|singular of|plural of|"
    r"inflection|participle|the compound|heritage_flow|panel_resonance|"
    r"alternative transliteration|manuel de codage|obsolete form of)",
    re.I,
)


def log(msg: str) -> None:
    print(msg, flush=True)


def kaikki_url(page: str, stem: str) -> str:
    # percent-encode page; stem may include hyphen (OldGalician-Portuguese)
    return (
        f"https://kaikki.org/dictionary/{quote(page)}/"
        f"kaikki.org-dictionary-{stem}.jsonl"
    )


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 80 or META.search(g):
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    return head[:48] if head else ""


def clean_form(w: str) -> str:
    w = (w or "").replace("\t", " ").replace("\n", " ").strip()
    if not w or len(w) > 64 or "_" in w:
        return ""
    return w


def mine_local(lang: str, max_rows: int = 20_000) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    paths = [
        ROOT / "data" / "expanded_gold.jsonl",
        ROOT / "data" / "dictionary_db_mined_gold.jsonl",
        ROOT / "data" / "expanded_gold_next20.jsonl",
    ]
    aliases = {lang}
    # common alt codes
    if lang == "roa-opt":
        aliases |= {"roa-opt", "pt-old", "opt", "osx-pt"}  # rare
    if lang == "pal":
        aliases |= {"pal", "pal-mp", "xmn"}
    if lang == "pro":
        aliases |= {"pro", "oc-old", "pro-oc"}
    for p in paths:
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if len(rows) >= max_rows:
                    break
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                L = (o.get("source_lang") or o.get("lang") or "").lower().strip()
                if L not in aliases:
                    continue
                word = clean_form(o.get("source_word") or o.get("word") or "")
                gloss = clean_gloss(
                    o.get("target_word") or o.get("meaning_key") or o.get("gloss") or ""
                )
                if not word or not gloss:
                    continue
                key = f"{word.lower()}|{gloss.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append((lang, word, gloss))
        if len(rows) >= max_rows:
            break
    return rows


def eval_counts() -> Counter:
    c: Counter = Counter()
    evalp = DATA / "eval_sample.tsv"
    if not evalp.exists():
        return c
    with evalp.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                c[p[0]] += 1
    return c


def main() -> None:
    DRIVE.mkdir(parents=True, exist_ok=True)
    INGEST.mkdir(parents=True, exist_ok=True)
    before = eval_counts()
    log(f"BEFORE thin: {sorted((L, before[L]) for L in before if before[L] < 50)}")

    all_rows: list[tuple[str, str, str]] = []
    by: Counter = Counter()

    for code, page, stem in THIN_TARGETS:
        rows: list[tuple[str, str, str]] = []
        if page and stem:
            url = kaikki_url(page, stem)
            dest = DRIVE / f"kaikki.org-dictionary-{stem.replace(' ', '')}.jsonl"
            # normalize dest name
            dest = DRIVE / f"kaikki.org-dictionary-{stem}.jsonl"
            log(f"=== {code} try Kaikki {page} ===")
            log(f"  url={url}")
            ok = d20.download_file(url, dest)
            if ok and dest.exists() and dest.stat().st_size > 500:
                rows = d20.convert_kaikki_jsonl(dest, code, max_rows=MAX_ROWS)
                log(f"  kaikki rows={len(rows)}")
            else:
                log(f"  kaikki miss for {code}")
        if len(rows) < 500:
            local = mine_local(code, max_rows=MAX_ROWS)
            log(f"  local mine +{len(local)}")
            # merge unique
            seen = {f"{a}|{b.lower()}|{c.lower()}" for a, b, c in rows}
            for a, b, c in local:
                k = f"{a}|{b.lower()}|{c.lower()}"
                if k not in seen:
                    seen.add(k)
                    rows.append((a, b, c))
        out_j = INGEST / f"{code}_thin_fill.jsonl"
        with out_j.open("w", encoding="utf-8") as w:
            for lang, form, gloss in rows:
                w.write(
                    json.dumps(
                        {
                            "source_lang": lang,
                            "source_word": form,
                            "target_word": gloss,
                            "source": "thin_fill",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        all_rows.extend(rows)
        by[code] = len(rows)
        log(f"  {code} total fill mass={len(rows)}")

    if not all_rows:
        log("nothing to ingest")
        return

    gold = DATA / "gold_core.tsv"
    dens = DATA / "densify.tsv"
    train = DATA / "train_mass.tsv"
    evalp = DATA / "eval_sample.tsv"

    dens_map: dict[str, str] = {}
    if dens.exists():
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1]:
                    dens_map[p[0].lower()] = p[1][:48]

    existing: set[str] = set()
    if evalp.exists():
        with evalp.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    existing.add(parts[1].lower().strip())

    # current per-lang eval counts
    per_eval = Counter(before)
    n_gold = 0
    with gold.open("a", encoding="utf-8") as wg, train.open(
        "a", encoding="utf-8"
    ) as wt, evalp.open("a", encoding="utf-8") as we:
        for lang, form, gloss in all_rows:
            fl = form.lower().strip()
            g = gloss.strip()[:48]
            if not fl or not g:
                continue
            wg.write(f"{lang}\t{form}\t{g}\n")
            wt.write(f"{fl}\t{g}\n")
            dens_map[fl] = g
            n_gold += 1
            if (
                fl not in existing
                and per_eval[lang] < TARGET_EVAL
                and len(fl) >= 2
            ):
                we.write(f"{lang}\t{form}\t{g}\n")
                existing.add(fl)
                per_eval[lang] += 1

    with dens.open("w", encoding="utf-8") as w:
        for k, v in dens_map.items():
            w.write(f"{k}\t{v}\n")

    cache = DATA / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    after_thin = {L: per_eval[L] for L, _, _ in THIN_TARGETS}
    log(f"appended gold/train rows~{n_gold}")
    log(f"eval after targets: {after_thin}")
    still = [L for L, n in after_thin.items() if n < 50]
    log(f"still thin n<50: {still}")
    log("next: python push_universal.py && python inject_converse_seeds.py")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    print(f"elapsed {time.perf_counter()-t0:.1f}s", flush=True)
