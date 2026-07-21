#!/usr/bin/env python3
"""
Full Kaikki dumps for Ancient Greek (grc) and Old English (ang).

Kaikki page paths keep spaces; JSONL filenames DROP spaces:
  /dictionary/Ancient%20Greek/kaikki.org-dictionary-AncientGreek.jsonl
  /dictionary/Old%20English/kaikki.org-dictionary-OldEnglish.jsonl

All files stay on the game drive (not GitHub):
  D:\\training data\\pflt_linguistics\\12_kaikki_downloads\\

Pass --ingest to merge into pflt-Ada local packs.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ADA = Path(__file__).resolve().parent
sys.path.insert(0, str(ADA))

spec = importlib.util.spec_from_file_location("d20", ADA / "download_next20_languages.py")
d20 = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(d20)

DRIVE = d20.DRIVE
INGEST = d20.INGEST
MANIFEST = DRIVE / "download_manifest_grc_ang.json"

# (page_name_with_spaces, file_stem_no_spaces, iso_code, kind)
TARGETS = [
    ("Ancient Greek", "AncientGreek", "grc", "ancient"),
    ("Old English", "OldEnglish", "ang", "ancient"),
]


def full_url(page_name: str, file_stem: str) -> str:
    """Correct Kaikki postprocessed JSONL URL (spaces in path, none in filename)."""
    return (
        f"https://kaikki.org/dictionary/{quote(page_name)}/"
        f"kaikki.org-dictionary-{file_stem}.jsonl"
    )


def main() -> None:
    ingest = "--ingest" in sys.argv
    # full dump: no artificial row cap (or very high)
    max_rows = 2_000_000
    DRIVE.mkdir(parents=True, exist_ok=True)
    INGEST.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "drive_root": str(DRIVE),
        "note": "Kaikki JSONL filenames drop spaces (AncientGreek not Ancient Greek)",
        "downloads": [],
        "ingest": ingest,
    }
    all_rows: list[tuple[str, str, str]] = []
    by_lang: Counter = Counter()

    for page_name, file_stem, code, kind in TARGETS:
        url = full_url(page_name, file_stem)
        dest = DRIVE / f"kaikki.org-dictionary-{file_stem}.jsonl"
        d20.log(f"=== {code} ({page_name}) ===")
        d20.log(f"  url={url}")
        ok = d20.download_file(url, dest)
        entry = {
            "name": page_name,
            "file_stem": file_stem,
            "code": code,
            "kind": kind,
            "url": url,
            "ok": ok,
            "path": str(dest) if dest.exists() else None,
            "rows": 0,
            "bytes": dest.stat().st_size if dest.exists() else 0,
        }
        if ok and dest.exists():
            rows = d20.convert_kaikki_jsonl(dest, code, max_rows=max_rows)
            entry["rows"] = len(rows)
            out_j = INGEST / f"{code}_full_gold.jsonl"
            with out_j.open("w", encoding="utf-8") as w:
                for lang, form, gloss in rows:
                    w.write(
                        json.dumps(
                            {
                                "source_lang": lang,
                                "source_word": form,
                                "target_word": gloss,
                                "source": "kaikki_full_grc_ang",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            all_rows.extend(rows)
            by_lang[code] += len(rows)
            d20.log(f"  {code}: +{len(rows)} form->gloss rows")
        manifest["downloads"].append(entry)
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    manifest["by_lang"] = dict(by_lang)
    manifest["total_rows"] = len(all_rows)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    d20.log(f"grc/ang full download done: {dict(by_lang)} total={len(all_rows)}")

    if not ingest or not all_rows:
        d20.log("skip merge (pass --ingest to merge into Ada packs)")
        return

    d20.log("merging into Ada packs...")
    gold = ADA / "data" / "gold_core.tsv"
    dens = ADA / "data" / "densify.tsv"
    train = ADA / "data" / "train_mass.tsv"
    evalp = ADA / "data" / "eval_sample.tsv"

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

    per: Counter = Counter()
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
            if fl not in existing and per[lang] < 800 and len(fl) >= 2:
                we.write(f"{lang}\t{form}\t{g}\n")
                existing.add(fl)
                per[lang] += 1

    with dens.open("w", encoding="utf-8") as w:
        for k, v in dens_map.items():
            w.write(f"{k}\t{v}\n")

    cache = ADA / "data" / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    d20.log(f"ingest densify={len(dens_map)} eval_added={dict(per)}")
    d20.log("next: python push_universal.py")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    print(f"elapsed {time.perf_counter()-t0:.1f}s", flush=True)
