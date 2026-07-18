#!/usr/bin/env python3
"""Inventory local FSOT linguistic data available for PFLT historical-first work."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

DICT = Path(r"C:\Users\damia\Desktop\Dictionary")
LING = Path(r"C:\Users\damia\Desktop\FSOT linguistics")


def main() -> None:
    seed = json.loads((DICT / "historical_linguistics_seed.json").read_text(encoding="utf-8"))
    print("historical_seed_pairs", len(seed), dict(Counter(x["source_lang"] for x in seed)))

    cand_path = DICT / "data" / "bridge_patterns" / "historical_validation_candidates_grc_la.json"
    if cand_path.exists():
        cand = json.loads(cand_path.read_text(encoding="utf-8"))
        print("validation_candidates", len(cand), dict(Counter(x["source_lang"] for x in cand)))

    db = DICT / "data" / "dictionary.db"
    if db.exists():
        c = sqlite3.connect(str(db))
        cur = c.cursor()
        print("hist_cols", cur.execute("pragma table_info(historical_translation_pairs)").fetchall())
        print("hist_n", cur.execute("select count(*) from historical_translation_pairs").fetchone()[0])
        rows = cur.execute("select * from historical_translation_pairs limit 3").fetchall()
        print("hist_sample", rows)
        for code in ("grc", "la", "lat", "ang", "akk", "sum", "en", "fr", "de", "es"):
            n = cur.execute(
                "select count(*) from words where lang_code = ?", (code,)
            ).fetchone()[0]
            print(f"words[{code}]={n}")
        c.close()

    ros = LING / "data" / "fsot_rosetta_canonical.csv"
    if ros.exists():
        print("rosetta_csv_bytes", ros.stat().st_size)


if __name__ == "__main__":
    main()
