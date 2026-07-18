#!/usr/bin/env python3
"""
Mine FSOT linguistics + Dictionary desktop assets into PFLT gap-fill data.

Sources:
  C:\\Users\\damia\\Desktop\\FSOT linguistics\\data\\fsot_rosetta_canonical.csv
  C:\\Users\\damia\\Desktop\\Dictionary\\data\\dictionary.db
  C:\\Users\\damia\\Desktop\\Dictionary\\historical_linguistics_seed.json

Outputs (Game Drive + pflt/data):
  rosetta_form_to_concept.jsonl   — form lookups
  rosetta_concept_to_en.json      — concept → English form
  dictionary_ipa_lexicon.json     — word → IPA
  dictionary_extra_gold.jsonl     — more classical/modern pairs
  mine_report.json
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

LING = Path(r"C:\Users\damia\Desktop\FSOT linguistics")
DICT = Path(r"C:\Users\damia\Desktop\Dictionary")
ROSETTA = LING / "data" / "fsot_rosetta_canonical.csv"
DB = DICT / "data" / "dictionary.db"
SEED = DICT / "historical_linguistics_seed.json"

OUT_PFLT = Path(r"C:\Users\damia\Desktop\pflt\data")
OUT_DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold")
OUT_AUDIO = Path(r"D:\training data\pflt_linguistics\05_phonology_vocal")


def mine_rosetta(max_rows: int = 0) -> Tuple[Dict[str, str], List[Dict[str, Any]], Dict[str, int]]:
    """
    Stream canonical CSV.
    Header: concept,language,form,v0..v255
    Build:
      - concept -> English form (prefer language en)
      - form index rows for grc/la/en/ang/akk/sum/san/hit
    """
    if not ROSETTA.exists():
        return {}, [], {"error": 1}

    concept_en: Dict[str, str] = {}
    form_rows: List[Dict[str, Any]] = []
    stats = Counter()
    focus_langs = {"en", "eng", "la", "lat", "grc", "el", "ang", "akk", "sum", "san", "hit", "fr", "de", "es"}

    # form_key (lang|normform) -> concept
    form_index: Dict[str, str] = {}

    with ROSETTA.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        # concept, language, form, vectors...
        for i, row in enumerate(reader):
            if max_rows and i >= max_rows:
                break
            if len(row) < 3:
                continue
            concept, lang, form = row[0].strip(), row[1].strip().lower(), row[2].strip()
            if not concept or not form:
                continue
            stats["rows"] += 1
            stats[f"lang_{lang}"] += 1
            if lang in {"en", "eng"} and concept not in concept_en:
                concept_en[concept] = form
            if lang in focus_langs:
                nf = form.lower()
                form_index[f"{lang}|{nf}"] = concept
                # also bare form for en preference
                if lang in {"en", "eng"}:
                    form_index[f"en|{nf}"] = concept
                form_rows.append({"lang": lang, "form": form, "concept": concept})

    # secondary: if concept has no en, use first form seen as english gloss label
    for fr in form_rows:
        c = fr["concept"]
        if c not in concept_en:
            concept_en[c] = fr["form"]

    stats["concepts_with_en"] = len(concept_en)
    stats["form_index"] = len(form_index)
    return concept_en, form_rows, dict(stats)


def mine_dictionary() -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, int]]:
    gold: List[Dict[str, Any]] = []
    ipa: Dict[str, str] = {}
    stats: Dict[str, int] = {}
    if not DB.exists():
        return gold, ipa, {"db_missing": 1}

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    stats["tables"] = len(tables)

    # Historical pairs
    if "historical_translation_pairs" in tables:
        rows = cur.execute(
            """
            SELECT source_lang_code, source_word, target_lang_code, target_word, gloss, confidence
            FROM historical_translation_pairs
            WHERE confidence >= 0.85
            """
        ).fetchall()
        for sl, sw, tl, tw, gloss, conf in rows:
            gold.append({
                "source_lang": sl,
                "source_word": sw,
                "target_lang": tl or "en",
                "target_word": tw,
                "gloss": gloss or tw,
                "confidence": float(conf or 0.9),
                "tier": "A",
                "source_title": "dictionary.db:historical_translation_pairs",
            })
        stats["historical_pairs"] = len(rows)

    # Extra classical gold: grc/la head glosses (high quality filter)
    if "definitions" in tables and "words" in tables:
        # Prefer short content glosses; skip pure inflectional meta definitions
        _META_GLOSS = re.compile(
            r"^(nominative|genitive|dative|accusative|ablative|vocative|singular|plural|"
            r"present|perfect|infinitive|participle|alternative form|initialism)\b",
            re.I,
        )
        for lang, limit in (("grc", 12000), ("la", 16000), ("ang", 5000), ("en", 6000)):
            rows = cur.execute(
                """
                SELECT w.word, w.pos, d.gloss
                FROM words w
                JOIN definitions d ON d.word_id = w.id
                WHERE w.lang_code = ?
                  AND d.gloss_lang = 'en'
                  AND length(d.gloss) BETWEEN 2 AND 80
                  AND length(w.word) BETWEEN 2 AND 40
                LIMIT ?
                """,
                (lang, limit * 4),
            ).fetchall()
            best: Dict[str, Tuple[float, str]] = {}
            for word, pos, gloss in rows:
                g = (gloss or "").split(";")[0].split("\n")[0].strip()
                g = re.sub(r"\{\{[^}]+\}\}", "", g)
                g = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", g).strip(" .,;")
                if len(g) < 2 or len(g) > 60:
                    continue
                if _META_GLOSS.match(g):
                    score = 0.4  # keep only if no better gloss
                else:
                    score = 1.0
                if pos and any(x in (pos or "").lower() for x in ("noun", "verb", "adj")):
                    score += 0.4
                if len(g.split()) <= 4:
                    score += 0.3
                if len(g.split()) <= 2 and not _META_GLOSS.match(g):
                    score += 0.25  # short concrete glosses are gold for open-set
                prev = best.get(word)
                if prev is None or score > prev[0]:
                    best[word] = (score, g)
            # take top by score then alpha
            items = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))[:limit]
            for word, (sc, g) in items:
                gold.append({
                    "source_lang": lang,
                    "source_word": word,
                    "target_lang": "en",
                    "target_word": g,
                    "meaning_key": re.sub(r"[^a-z0-9]+", "_", g.lower()).strip("_"),
                    "confidence": min(0.93, 0.82 + 0.05 * sc),
                    "tier": "A" if sc >= 1.4 else "B",
                    "source_title": f"dictionary.db:words+definitions:{lang}",
                })
            stats[f"extra_{lang}"] = len(items)

        # Proper names / places / peoples (high open-set miss class)
        _PLACE_GLOSS = re.compile(
            r"\b(city|town|village|river|island|region|province|country|mountain|"
            r"people|tribe|inhabitant|ancient|kingdom|sea|lake|port|colony|"
            r"capital|district|territory|nation)\b",
            re.I,
        )
        name_n = 0
        for lang, limit in (("grc", 8000), ("la", 8000), ("ang", 1500), ("en", 2000)):
            # pos=name first
            rows = cur.execute(
                """
                SELECT w.word, w.pos, d.gloss
                FROM words w
                JOIN definitions d ON d.word_id = w.id
                WHERE w.lang_code = ?
                  AND d.gloss_lang = 'en'
                  AND (w.pos = 'name' OR w.pos LIKE '%name%')
                  AND length(d.gloss) BETWEEN 2 AND 100
                  AND length(w.word) BETWEEN 2 AND 45
                LIMIT ?
                """,
                (lang, limit * 3),
            ).fetchall()
            # also place/people patterned nouns
            rows2 = cur.execute(
                """
                SELECT w.word, w.pos, d.gloss
                FROM words w
                JOIN definitions d ON d.word_id = w.id
                WHERE w.lang_code = ?
                  AND d.gloss_lang = 'en'
                  AND w.pos IN ('noun', 'name', 'adj')
                  AND length(d.gloss) BETWEEN 3 AND 90
                  AND length(w.word) BETWEEN 3 AND 40
                  AND (
                    d.gloss LIKE '%city%' OR d.gloss LIKE '%river%' OR
                    d.gloss LIKE '%island%' OR d.gloss LIKE '%people%' OR
                    d.gloss LIKE '%inhabitant%' OR d.gloss LIKE '%ancient %' OR
                    d.gloss LIKE '%town%' OR d.gloss LIKE '%region%' OR
                    d.gloss LIKE '%tribe%' OR d.gloss LIKE '%kingdom%'
                  )
                LIMIT ?
                """,
                (lang, limit * 2),
            ).fetchall()
            best: Dict[str, Tuple[float, str]] = {}
            for word, pos, gloss in list(rows) + list(rows2):
                g = (gloss or "").split(";")[0].split("\n")[0].strip()
                g = re.sub(r"\{\{[^}]+\}\}", "", g)
                g = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", g).strip(" .,;")
                if len(g) < 2 or len(g) > 70:
                    continue
                if _META_GLOSS.match(g):
                    continue
                score = 1.0
                if (pos or "").lower() in {"name", "proper"}:
                    score += 0.5
                if _PLACE_GLOSS.search(g):
                    score += 0.4
                if len(g.split()) <= 6:
                    score += 0.2
                prev = best.get(word)
                if prev is None or score > prev[0]:
                    best[word] = (score, g)
            items = sorted(best.items(), key=lambda kv: (-kv[1][0], kv[0]))[:limit]
            for word, (sc, g) in items:
                gold.append({
                    "source_lang": lang,
                    "source_word": word,
                    "target_lang": "en",
                    "target_word": g,
                    "meaning_key": re.sub(r"[^a-z0-9]+", "_", g.lower()).strip("_"),
                    "confidence": min(0.94, 0.84 + 0.04 * sc),
                    "tier": "A" if sc >= 1.5 else "B",
                    "source_title": f"dictionary.db:names_places:{lang}",
                })
                name_n += 1
            stats[f"names_{lang}"] = len(items)
        stats["names_total"] = name_n

    # Pronunciations / IPA
    if "pronunciations" in tables:
        cols = [x[1] for x in cur.execute("pragma table_info(pronunciations)").fetchall()]
        # try common schemas
        if "ipa" in cols or "pronunciation" in cols or "value" in cols:
            # discover
            sample = cur.execute("SELECT * FROM pronunciations LIMIT 1").fetchone()
            colmap = {c: i for i, c in enumerate(cols)}
            ipa_col = next((c for c in ("ipa", "pronunciation", "value", "phonetic") if c in colmap), None)
            word_id_col = "word_id" if "word_id" in colmap else None
            if ipa_col and word_id_col:
                rows = cur.execute(
                    f"""
                    SELECT w.word, w.lang_code, p.{ipa_col}
                    FROM pronunciations p
                    JOIN words w ON w.id = p.word_id
                    WHERE p.{ipa_col} IS NOT NULL AND length(p.{ipa_col}) > 0
                    LIMIT 50000
                    """
                ).fetchall()
                for word, lang, ipa_s in rows:
                    if not word or not ipa_s:
                        continue
                    # clean /slashes/
                    ipa_s = str(ipa_s).strip().strip("/").strip("[]")
                    key = f"{lang}|{word.lower()}"
                    if key not in ipa and re.search(r"[\u0250-\u02AF\u1D00-\u1DFFa-zˈˌː]", ipa_s, re.I):
                        ipa[key] = ipa_s
                        # also bare for en
                        if lang == "en":
                            ipa.setdefault(word.lower(), ipa_s)
                stats["ipa_entries"] = len(ipa)

    # translations table: source word in other langs to english head
    if "translations" in tables:
        tcols = [x[1] for x in cur.execute("pragma table_info(translations)").fetchall()]
        stats["translation_cols"] = len(tcols)

    conn.close()

    if SEED.exists():
        for row in json.loads(SEED.read_text(encoding="utf-8")):
            gold.append({
                "source_lang": row.get("source_lang"),
                "source_word": row.get("source_word"),
                "target_lang": row.get("target_lang", "en"),
                "target_word": row.get("target_word"),
                "gloss": row.get("gloss"),
                "confidence": float(row.get("confidence", 1.0)),
                "tier": "A",
                "source_title": row.get("source_title") or "historical_seed",
            })
        stats["seed_pairs"] = 23

    return gold, ipa, stats


def main() -> None:
    OUT_PFLT.mkdir(parents=True, exist_ok=True)
    OUT_DRIVE.mkdir(parents=True, exist_ok=True)
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)

    print("Mining Rosetta canonical (stream)...")
    concept_en, form_rows, rstats = mine_rosetta()
    print("  rosetta stats", {k: rstats[k] for k in list(rstats)[:12]}, "...")

    print("Mining Dictionary DB...")
    gold, ipa, dstats = mine_dictionary()
    print("  dict stats", dstats)

    # write concept_en
    (OUT_PFLT / "rosetta_concept_to_en.json").write_text(
        json.dumps(concept_en, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DRIVE / "rosetta_concept_to_en.json").write_text(
        json.dumps(concept_en, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # form index compact: only focus languages, unique
    form_index = {}
    for fr in form_rows:
        k = f"{fr['lang']}|{fr['form'].lower()}"
        form_index[k] = fr["concept"]
    (OUT_PFLT / "rosetta_form_index.json").write_text(
        json.dumps(form_index, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DRIVE / "rosetta_form_index.json").write_text(
        json.dumps(form_index, ensure_ascii=False), encoding="utf-8"
    )

    # gold jsonl
    gold_path = OUT_PFLT / "dictionary_extra_gold.jsonl"
    with gold_path.open("w", encoding="utf-8") as f:
        for g in gold:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
    (OUT_DRIVE / "dictionary_extra_gold.jsonl").write_text(
        gold_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # IPA
    ipa_path = OUT_PFLT / "dictionary_ipa_lexicon.json"
    ipa_path.write_text(json.dumps(ipa, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_AUDIO / "dictionary_ipa_lexicon.json").write_text(
        json.dumps(ipa, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Build PFLT-ready classical lexicon merge from new gold (grc/la)
    classical_lex = {}
    for g in gold:
        if g.get("source_lang") in {"grc", "la", "lat", "ang"} and g.get("target_lang") in {"en", "eng"}:
            w = str(g["source_word"])
            mk = g.get("meaning_key") or re.sub(r"[^a-z0-9]+", "_", str(g["target_word"]).lower()).strip("_")
            classical_lex[w] = mk
            classical_lex[w.lower()] = mk
    (OUT_PFLT / "dictionary_classical_lexicon.json").write_text(
        json.dumps(classical_lex, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "rosetta": rstats,
        "dictionary": dstats,
        "n_concept_en": len(concept_en),
        "n_form_index": len(form_index),
        "n_gold": len(gold),
        "n_ipa": len(ipa),
        "n_classical_lex": len(classical_lex),
        "paths": {
            "concept_en": str(OUT_PFLT / "rosetta_concept_to_en.json"),
            "form_index": str(OUT_PFLT / "rosetta_form_index.json"),
            "gold": str(gold_path),
            "ipa": str(ipa_path),
        },
    }
    (OUT_PFLT / "mine_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DRIVE / "mine_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
