#!/usr/bin/env python3
"""
Breadth batch 2 — more Kaikki languages onto the game drive (not GitHub).

Goal: expand catalog toward any-language translator (beat Google/NLLB breadth).
Downloads only to:
  D:\\training data\\pflt_linguistics\\12_kaikki_downloads\\

Optional --ingest merges into pflt-Ada local packs (gold_core / train / eval / densify).
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
sys.path.insert(0, str(ADA))

# Reuse download helpers from next20
spec = importlib.util.spec_from_file_location("d20", ADA / "download_next20_languages.py")
d20 = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(d20)

DRIVE = d20.DRIVE
INGEST = d20.INGEST
MANIFEST = DRIVE / "download_manifest_batch2.json"

# Batch 2: high-coverage modern + classical not yet in batch1 Kaikki list
# (batch1 already has es/it/de/fr/pt/ru/nl/pl/sv/tr/ja/ko/hi/vi/id/ca/pi/uga/akk/egy)
KAIKKI_BATCH2: list[tuple[str, str, str]] = [
    ("Chinese", "zh", "modern"),
    ("Arabic", "ar", "modern"),
    ("Greek", "el", "modern"),
    ("Hebrew", "he", "modern"),
    ("Persian", "fa", "modern"),
    ("Ukrainian", "uk", "modern"),
    ("Czech", "cs", "modern"),
    ("Romanian", "ro", "modern"),
    ("Hungarian", "hu", "modern"),
    ("Finnish", "fi", "modern"),
    ("Thai", "th", "modern"),
    ("Swahili", "sw", "modern"),
    ("Bengali", "bn", "modern"),
    ("Tamil", "ta", "modern"),
    ("Malay", "ms", "modern"),
    ("Latin", "la", "classical"),  # full Kaikki Latin boost
    ("Ancient Greek", "grc", "ancient"),
    ("Old English", "ang", "ancient"),
    ("Sanskrit", "san", "ancient"),
    ("Gothic", "got", "ancient"),
]


def main() -> None:
    ingest = "--ingest" in sys.argv
    DRIVE.mkdir(parents=True, exist_ok=True)
    INGEST.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "drive_root": str(DRIVE),
        "batch": 2,
        "downloads": [],
        "ingest": ingest,
    }
    all_rows: list[tuple[str, str, str]] = []
    by_lang: Counter = Counter()

    for name, code, kind in KAIKKI_BATCH2:
        url = d20.kaikki_url(name)
        dest = DRIVE / f"kaikki.org-dictionary-{name.replace(' ', '_')}.jsonl"
        # Kaikki uses spaces in filenames for multi-word names
        dest_space = DRIVE / f"kaikki.org-dictionary-{name}.jsonl"
        ok = d20.download_file(url, dest_space)
        path = dest_space if dest_space.exists() else dest
        entry = {
            "name": name,
            "code": code,
            "kind": kind,
            "url": url,
            "ok": ok,
            "path": str(path) if path.exists() else None,
            "rows": 0,
        }
        if ok and path.exists():
            rows = d20.convert_kaikki_jsonl(path, code, max_rows=180_000)
            entry["rows"] = len(rows)
            out_j = INGEST / f"{code}_batch2_gold.jsonl"
            with out_j.open("w", encoding="utf-8") as w:
                for lang, form, gloss in rows:
                    w.write(
                        json.dumps(
                            {
                                "source_lang": lang,
                                "source_word": form,
                                "target_word": gloss,
                                "source": "kaikki_batch2",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            all_rows.extend(rows)
            by_lang[code] += len(rows)
            d20.log(f"{code}: +{len(rows)} rows from {name}")
        manifest["downloads"].append(entry)
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    manifest["by_lang"] = dict(by_lang)
    manifest["total_rows"] = len(all_rows)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    d20.log(f"batch2 download done: langs={len(by_lang)} rows={len(all_rows)}")
    d20.log(f"manifest={MANIFEST}")

    if not ingest or not all_rows:
        d20.log("skip merge (pass --ingest to merge into Ada packs)")
        return

    # Merge into Ada packs via expand_next20 style append
    d20.log("merging into Ada gold/train/eval/densify ...")
    gold = ADA / "data" / "gold_core.tsv"
    dens = ADA / "data" / "densify.tsv"
    train = ADA / "data" / "train_mass.tsv"
    evalp = ADA / "data" / "eval_sample.tsv"

    # densify + train append preferred senses
    dens_map: dict[str, str] = {}
    if dens.exists():
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1]:
                    dens_map[p[0].lower()] = p[1][:48]
    for lang, form, gloss in all_rows:
        fl = form.lower().strip()
        g = gloss.strip()[:48]
        if fl and g:
            dens_map[fl] = g

    with dens.open("w", encoding="utf-8") as w:
        for k, v in dens_map.items():
            w.write(f"{k}\t{v}\n")

    # gold_core append
    with gold.open("a", encoding="utf-8") as w:
        for lang, form, gloss in all_rows:
            w.write(f"{lang}\t{form}\t{gloss[:48]}\n")

    # train_mass append
    with train.open("a", encoding="utf-8") as w:
        for lang, form, gloss in all_rows:
            w.write(f"{form.lower()}\t{gloss[:48]}\n")

    # stratified eval: up to 400 new forms per lang not already in eval
    existing: set[str] = set()
    if evalp.exists():
        with evalp.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    existing.add(p[1].lower() if p[0] in by_lang else p[0].lower())

    per: Counter = Counter()
    with evalp.open("a", encoding="utf-8") as w:
        for lang, form, gloss in all_rows:
            fl = form.lower().strip()
            if fl in existing or per[lang] >= 400:
                continue
            if len(fl) < 2:
                continue
            w.write(f"{lang}\t{form}\t{gloss[:48]}\n")
            existing.add(fl)
            per[lang] += 1

    # drop train cache so next climb reloads
    cache = ADA / "data" / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    d20.log(f"ingest complete densify={len(dens_map)} eval_added={dict(per)}")
    d20.log("next: python push_universal.py && alr build")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    print(f"elapsed {time.perf_counter()-t0:.1f}s", flush=True)
