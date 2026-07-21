#!/usr/bin/env python3
"""
Fill gaps toward ~100 language codes under FSOT.

Downloads missing Kaikki postprocessed JSONL dumps to the game drive only:
  D:\\training data\\pflt_linguistics\\12_kaikki_downloads\\

Then ingests into local Ada packs (gold/train/eval/densify) and can solidify
via push_universal.

Kaikki URL rule: page path keeps spaces; JSONL stem drops spaces.
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
MANIFEST = DRIVE / "download_manifest_to100.json"

# Already in catalog (from competitor_push) — skip re-download when file exists.
# Target: bring total productive codes toward 100.
# (name_on_kaikki, iso_code, kind)
# Multi-word names OK — kaikki_url handles stems.
BATCH_TO_100: list[tuple[str, str, str]] = [
    # Modern high-utility gaps
    ("Norwegian Bokmål", "nb", "modern"),
    ("Danish", "da", "modern"),
    ("Galician", "gl", "modern"),
    ("Esperanto", "eo", "modern"),
    ("Serbo-Croatian", "sh", "modern"),
    ("Macedonian", "mk", "modern"),
    ("Bulgarian", "bg", "modern"),
    ("Norwegian Nynorsk", "nn", "modern"),
    ("Tagalog", "tl", "modern"),
    ("Irish", "ga", "modern"),
    ("Welsh", "cy", "modern"),
    ("Lithuanian", "lt", "modern"),
    ("Icelandic", "is", "modern"),
    ("Albanian", "sq", "modern"),
    ("Georgian", "ka", "modern"),
    ("Armenian", "hy", "modern"),
    ("Telugu", "te", "modern"),
    ("Cebuano", "ceb", "modern"),
    ("Scottish Gaelic", "gd", "modern"),
    ("Azerbaijani", "az", "modern"),
    ("Slovak", "sk", "modern"),
    ("Basque", "eu", "modern"),
    ("Urdu", "ur", "modern"),
    ("Malayalam", "ml", "modern"),
    ("Punjabi", "pa", "modern"),
    ("Estonian", "et", "modern"),
    ("Yiddish", "yi", "modern"),
    ("Kazakh", "kk", "modern"),
    ("Khmer", "km", "modern"),
    ("Burmese", "my", "modern"),
    ("Afrikaans", "af", "modern"),
    ("Belarusian", "be", "modern"),
    ("Gujarati", "gu", "modern"),
    ("Slovene", "sl", "modern"),
    ("Mongolian", "mn", "modern"),
    ("Occitan", "oc", "modern"),
    ("Yoruba", "yo", "modern"),
    ("Marathi", "mr", "modern"),
    ("Javanese", "jv", "modern"),
    ("Hawaiian", "haw", "modern"),
    ("Amharic", "am", "modern"),
    ("Nepali", "ne", "modern"),
    ("Quechua", "qu", "modern"),
    ("Zulu", "zu", "modern"),
    ("Xhosa", "xh", "modern"),
    ("Hausa", "ha", "modern"),
    ("Somali", "so", "modern"),
    ("Pashto", "ps", "modern"),
    ("Sinhalese", "si", "modern"),
    ("Latvian", "lv", "modern"),
    # Historical / classical gap fills (thin or missing)
    ("Middle English", "enm", "historical"),
    ("Old French", "fro", "historical"),
    ("Old Irish", "sga", "historical"),  # boost thin sga
    ("Old Norse", "non", "historical"),  # boost thin non
    ("Sumerian", "sum", "ancient"),
    ("Classical Syriac", "syc", "ancient"),
    ("Old Persian", "peo", "ancient"),
    ("Old Church Slavonic", "cu", "historical"),
    ("Middle French", "frm", "historical"),
    ("Old High German", "goh", "historical"),
    ("Middle High German", "gmh", "historical"),
    ("Old Saxon", "osx", "historical"),
    ("Coptic", "cop", "ancient"),
    ("Aramaic", "arc", "ancient"),
]


def full_url(name: str) -> str:
    page = quote(name)
    stem = name.replace(" ", "")
    return f"https://kaikki.org/dictionary/{page}/kaikki.org-dictionary-{stem}.jsonl"


def dest_path(name: str) -> Path:
    stem = name.replace(" ", "")
    return DRIVE / f"kaikki.org-dictionary-{stem}.jsonl"


def main() -> None:
    ingest = "--ingest" in sys.argv
    max_rows = 100_000  # per lang form→gloss rows (forms expand)
    DRIVE.mkdir(parents=True, exist_ok=True)
    INGEST.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "Fill gaps toward ~100 languages under FSOT",
        "drive_root": str(DRIVE),
        "downloads": [],
        "ingest": ingest,
    }
    all_rows: list[tuple[str, str, str]] = []
    by_lang: Counter = Counter()
    ok_n = fail_n = 0

    for name, code, kind in BATCH_TO_100:
        url = full_url(name)
        dest = dest_path(name)
        d20.log(f"=== {code} ({name}) [{kind}] ===")
        ok = d20.download_file(url, dest)
        entry = {
            "name": name,
            "code": code,
            "kind": kind,
            "url": url,
            "ok": ok,
            "path": str(dest) if dest.exists() else None,
            "rows": 0,
            "bytes": dest.stat().st_size if dest.exists() else 0,
        }
        if ok and dest.exists():
            ok_n += 1
            rows = d20.convert_kaikki_jsonl(dest, code, max_rows=max_rows)
            entry["rows"] = len(rows)
            out_j = INGEST / f"{code}_to100_gold.jsonl"
            with out_j.open("w", encoding="utf-8") as w:
                for lang, form, gloss in rows:
                    w.write(
                        json.dumps(
                            {
                                "source_lang": lang,
                                "source_word": form,
                                "target_word": gloss,
                                "source": "kaikki_to100",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            all_rows.extend(rows)
            by_lang[code] += len(rows)
            d20.log(f"  {code}: +{len(rows)}")
        else:
            fail_n += 1
            d20.log(f"  FAIL {code}")
        manifest["downloads"].append(entry)
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    manifest["by_lang"] = dict(by_lang)
    manifest["total_rows"] = len(all_rows)
    manifest["ok"] = ok_n
    manifest["fail"] = fail_n
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    d20.log(f"to100 download done ok={ok_n} fail={fail_n} rows={len(all_rows)} langs={len(by_lang)}")

    if not ingest:
        d20.log("skip merge (pass --ingest)")
        return
    if not all_rows:
        d20.log("no rows to ingest")
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
            if fl not in existing and per[lang] < 400 and len(fl) >= 2:
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
    d20.log("next: python push_universal.py && python cross_lingual_fsot.py")


if __name__ == "__main__":
    t0 = time.perf_counter()
    main()
    print(f"elapsed {time.perf_counter()-t0:.1f}s", flush=True)
