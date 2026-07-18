#!/usr/bin/env python3
"""
Grow Latin + Ancient Greek Tier-A style gold from Dictionary SQLite.

Policy (accuracy-first):
  - Prefer short, clean English gloss heads (not full essay definitions)
  - Cap per language for quality control; write full candidate pool separately
  - Promote high-confidence simple glosses into historical gold format
  - Merge into D:\\training data\\pflt_linguistics\\01_historical_gold

Does not invent meanings. Sources are Wiktionary-derived Dictionary DB entries.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DICT_DB = Path(r"C:\Users\damia\Desktop\Dictionary\data\dictionary.db")
OUT_DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold")
OUT_PFLT = Path(r"C:\Users\damia\Desktop\pflt\data")

# How many high-quality pairs to promote per language into active gold
PROMOTE_LIMIT = {
    "grc": 2000,
    "la": 2000,
}

# Soft filters for gloss quality
STOP_GLOSS_START = (
    "see ",
    "cf.",
    "compare ",
    "variant of",
    "alternative form",
    "misspelling",
    "obsolete",
    "archaic spelling",
)


def head_gloss(definition: str) -> Optional[str]:
    if not definition:
        return None
    d = definition.strip()
    # take first clause / first line
    d = re.split(r"[\n;|]", d)[0].strip()
    d = re.sub(r"\s+", " ", d)
    # strip leading numbering / sense markers
    d = re.sub(r"^[\(\[]?\d+[\)\].:]\s*", "", d)
    d = re.sub(r"^[a-z]\)\s*", "", d, flags=re.I)
    # remove wiki templates crud
    d = re.sub(r"\{\{[^}]+\}\}", "", d)
    d = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", d)
    d = d.strip(" .,;:-")
    if len(d) < 2 or len(d) > 60:
        return None
    low = d.lower()
    if any(low.startswith(s) for s in STOP_GLOSS_START):
        return None
    # Prefer simple English-looking glosses (letters/spaces/hyphens)
    if not re.search(r"[A-Za-z]", d):
        return None
    # Too many non-ascii beyond greek sources' english gloss — allow basic punct
    if len(re.findall(r"[A-Za-z]", d)) < 2:
        return None
    return d


def meaning_key(gloss: str) -> str:
    g = gloss.lower().strip()
    g = re.sub(r"[^a-z0-9\s\-']", " ", g)
    g = re.sub(r"\s+", "_", g).strip("_")
    return g[:80] or "unknown"


def fetch_pairs(conn: sqlite3.Connection, lang: str, limit_scan: int = 200000) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    # definitions table linked to words
    rows = cur.execute(
        """
        SELECT w.word, w.lang_code, w.pos, d.gloss, w.id
        FROM words w
        JOIN definitions d ON d.word_id = w.id
        WHERE w.lang_code = ?
          AND d.gloss_lang = 'en'
          AND d.gloss IS NOT NULL
          AND length(d.gloss) BETWEEN 2 AND 400
        LIMIT ?
        """,
        (lang, limit_scan),
    ).fetchall()

    best: Dict[str, Dict[str, Any]] = {}
    for word, code, pos, definition, wid in rows:
        if not word or len(word) > 40:
            continue
        # skip multiword noise for Tier A grow (keep single tokens mostly)
        if " " in word.strip() and lang == "la":
            # allow a few common multiwords later; skip heavy phrases now
            if word.count(" ") > 1:
                continue
        gloss = head_gloss(definition or "")
        if not gloss:
            continue
        # Prefer noun/verb/adj if pos present
        score = 1.0
        pos_l = (pos or "").lower()
        if any(p in pos_l for p in ("noun", "verb", "adj", "name", "num")):
            score += 0.5
        if len(gloss.split()) <= 3:
            score += 0.5
        if len(gloss) <= 24:
            score += 0.25
        key = word.strip()
        rec = {
            "source_lang": "grc" if code == "grc" else "la",
            "source_word": key,
            "target_lang": "en",
            "target_word": gloss,
            "meaning_key": meaning_key(gloss),
            "gloss": gloss,
            "pos": pos or "",
            "confidence": min(0.92, 0.8 + 0.05 * score),
            "source_title": "Dictionary.db Wiktionary-derived definition head (auto-curated)",
            "tier": "A" if score >= 1.75 else "B",
            "word_id": wid,
            "score": score,
            "epoch": 4 if code == "grc" else 5,
        }
        prev = best.get(key)
        if prev is None or rec["score"] > prev["score"]:
            best[key] = rec
    return list(best.values())


def main() -> None:
    OUT_DRIVE.mkdir(parents=True, exist_ok=True)
    OUT_PFLT.mkdir(parents=True, exist_ok=True)
    if not DICT_DB.exists():
        raise SystemExit(f"missing {DICT_DB}")

    conn = sqlite3.connect(str(DICT_DB))
    all_pool: List[Dict[str, Any]] = []
    promoted: List[Dict[str, Any]] = []

    for lang in ("grc", "la"):
        pairs = fetch_pairs(conn, lang)
        pairs.sort(key=lambda r: (-r["score"], r["source_word"]))
        all_pool.extend(pairs)
        # promote top N with tier A preference
        a_first = [p for p in pairs if p["tier"] == "A"] + [p for p in pairs if p["tier"] != "A"]
        take = a_first[: PROMOTE_LIMIT[lang]]
        for p in take:
            p["tier"] = "A"  # promoted batch is treated as active gold after auto filters
            p["confidence"] = max(float(p["confidence"]), 0.88)
        promoted.extend(take)
        print(f"{lang}: pool={len(pairs)} promoted={len(take)}")

    conn.close()

    # Write pools
    pool_path = OUT_DRIVE / "classical_grc_la_pool.jsonl"
    with pool_path.open("w", encoding="utf-8") as f:
        for r in all_pool:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    prom_path = OUT_DRIVE / "classical_grc_la_promoted_tierA.jsonl"
    with prom_path.open("w", encoding="utf-8") as f:
        for r in promoted:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Lexicon for PFLT
    lex: Dict[str, str] = {}
    for r in promoted:
        w = r["source_word"]
        m = r["meaning_key"]
        lex[w] = m
        lex[w.lower()] = m

    lex_path = OUT_DRIVE / "classical_grc_la_lexicon.json"
    lex_path.write_text(json.dumps(lex, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_PFLT / "classical_grc_la_lexicon.json").write_text(
        json.dumps(lex, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_PFLT / "classical_grc_la_promoted_tierA.jsonl").write_text(
        prom_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Merge into historical_gold_merged style list if present
    merged_path = OUT_DRIVE / "historical_gold_merged.json"
    base: List[Dict[str, Any]] = []
    if merged_path.exists():
        try:
            base = json.loads(merged_path.read_text(encoding="utf-8"))
        except Exception:
            base = []
    # index by lang:word
    idx = {(x.get("source_lang"), x.get("source_word")): i for i, x in enumerate(base)}
    added = 0
    for r in promoted:
        key = (r["source_lang"], r["source_word"])
        slim = {
            "source_lang": r["source_lang"],
            "source_word": r["source_word"],
            "target_lang": "en",
            "target_word": r["target_word"],
            "gloss": r["gloss"],
            "confidence": r["confidence"],
            "source_title": r["source_title"],
            "tier": "A",
            "epoch": r["epoch"],
        }
        if key in idx:
            base[idx[key]] = slim
        else:
            base.append(slim)
            added += 1
    merged_path.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT_PFLT / "historical_gold_merged.json").write_text(
        json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "pool_n": len(all_pool),
        "promoted_n": len(promoted),
        "promoted_grc": sum(1 for r in promoted if r["source_lang"] == "grc"),
        "promoted_la": sum(1 for r in promoted if r["source_lang"] == "la"),
        "lexicon_keys": len(lex),
        "merged_total": len(base),
        "merged_added": added,
        "paths": {
            "pool": str(pool_path),
            "promoted": str(prom_path),
            "lexicon": str(lex_path),
            "merged": str(merged_path),
        },
        "samples": promoted[:8] + promoted[-4:],
    }
    (OUT_DRIVE / "classical_grow_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in summary if k != "samples"}, indent=2))
    print("samples:")
    for s in summary["samples"][:6]:
        print(f"  [{s['source_lang']}] {s['source_word']} -> {s['target_word']}")


if __name__ == "__main__":
    main()
