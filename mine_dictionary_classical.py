#!/usr/bin/env python3
"""
Mine Dictionary.db for classical / historical / hieroglyph-adjacent language rows.

Local only (6GB SQLite on Desktop). Appends to data/dictionary_db_mined_gold.jsonl
and can be re-merged via ingest_all_language_data.py.

Focus langs: la, grc, ang, akk, sum, san, hit, cop, egy, he, arc, fro, goh, non, …
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DB = Path(r"C:\Users\damia\Desktop\Dictionary\data\dictionary.db")
OUT = DATA / "dictionary_db_mined_gold.jsonl"
REPORT = DATA / "dictionary_db_mine_report.json"

# ISO-ish codes seen in Dictionary.db lang_code
FOCUS: Set[str] = {
    "la", "lat", "grc", "el", "gr", "ang", "anglo-saxon", "oe",
    "akk", "sum", "sux", "san", "sa", "hit", "hit-x-luvi",
    "egy", "egy-x", "cop", "egx",
    "he", "heb", "hbo", "arc", "syc", "syr",
    "got", "non", "non-x", "gmh", "goh", "osx", "sga", "mga",
    "fro", "frm", "pro", "osp", "roa-opt",
    "cu", "orv", "chu",
    "pi", "pli", "sa",
    "ar", "fa", "peo", "pal",
    "uga", "phn", "xcl", "hy",
}

LANG_NORM = {
    "lat": "la", "el": "grc", "gr": "grc", "oe": "ang", "anglo-saxon": "ang",
    "sux": "sum", "sa": "san", "egx": "egy", "heb": "he", "hbo": "he",
    "pli": "pi",
}


def meaning_key(g: str) -> str:
    g = (g or "").strip().lower()
    g = re.sub(r"^(a|an|the)\s+", "", g)
    g = re.sub(r"[^a-z0-9]+", "_", g)
    return g.strip("_")[:80] or "unknown"


def main() -> int:
    if not DB.is_file():
        print("Dictionary.db missing:", DB)
        return 1

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    # Distinct lang codes in focus
    codes = [
        r[0]
        for r in cur.execute(
            "SELECT DISTINCT lang_code FROM words WHERE lang_code IS NOT NULL"
        ).fetchall()
    ]
    use = []
    for c in codes:
        cl = (c or "").lower()
        if cl in FOCUS or cl.split("-")[0] in FOCUS:
            use.append(c)
    print(f"lang codes in DB focus: {len(use)} / {len(codes)}", flush=True)

    # Pull words + first English-ish gloss
    # definitions.gloss_lang may be en / eng / ''
    q = """
    SELECT w.lang_code, w.word, w.pos, d.gloss
    FROM words w
    JOIN definitions d ON d.word_id = w.id
    WHERE w.lang_code IN ({placeholders})
      AND w.word IS NOT NULL AND LENGTH(w.word) BETWEEN 1 AND 64
      AND d.gloss IS NOT NULL AND LENGTH(d.gloss) BETWEEN 1 AND 200
      AND (d.gloss_lang IS NULL OR d.gloss_lang IN ('en','eng','') OR d.sense_index = 0)
    """.format(placeholders=",".join("?" * len(use)))

    rows_out: List[Dict[str, Any]] = []
    seen = set()
    lang_n: Counter = Counter()
    batch = cur.execute(q, use)
    n_scan = 0
    for lang_code, word, pos, gloss in batch:
        n_scan += 1
        if n_scan % 200_000 == 0:
            print(f"  scanned {n_scan} kept {len(rows_out)}", flush=True)
        lang = LANG_NORM.get((lang_code or "").lower(), (lang_code or "").lower())
        word = (word or "").strip()
        gloss = (gloss or "").strip()
        # take head of multi-sense gloss
        gloss = re.split(r"[;|]", gloss)[0].strip()
        gloss = re.sub(r"^\([^)]*\)\s*", "", gloss)
        if not word or not gloss or len(gloss) < 2:
            continue
        # drop pure meta
        gl = gloss.lower()
        if gl.startswith("see ") or gl in {"?", "—", "-"}:
            continue
        key = f"{lang}|{word.lower()}"
        if key in seen:
            continue
        seen.add(key)
        is_name = (pos or "").lower() in {"name", "proper noun", "propn"}
        rec = {
            "source_lang": lang,
            "source_word": word,
            "target_lang": "en",
            "target_word": gloss,
            "meaning_key": meaning_key(gloss),
            "confidence": 0.86,
            "tier": "B",
            "source_title": "Dictionary.db mine",
            "pos": pos or "",
            "is_name": is_name,
        }
        rows_out.append(rec)
        lang_n[lang] += 1

    con.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows_out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "db": str(DB),
        "n_scanned_joins": n_scan,
        "n_unique": len(rows_out),
        "by_lang": dict(lang_n.most_common(40)),
        "out": str(OUT),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:2000], flush=True)
    print("wrote", OUT, "n=", len(rows_out), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
