#!/usr/bin/env python3
"""
Ingest ALL local language / hieroglyph / lexicon sources into expanded gold.

Sources (offline, no paid APIs):
  - data/dictionary_extra_gold.jsonl
  - data/classical_grc_la_promoted_tierA.jsonl
  - data/historical_gold_merged.json
  - data/hieroglyph_unikemet_gold.jsonl (+ Gardiner + Unicode forms)
  - data/hieroglyph_pflt_lexicon.json
  - data/classical_full_trained_lexicon.json
  - data/dictionary_classical_lexicon.json
  - data/domain_lexica.json (per-domain term maps)
  - D:/.../classical_grc_la_pool.jsonl  (~164k la/grc — major unlock)
  - D:/.../asjp/forms.csv (concept glosses, optional)
  - core_lemma_seeds

Writes:
  data/expanded_gold.jsonl
  data/expanded_gold_report.json
  D:/training data/pflt_linguistics/01_historical_gold/expanded_gold.jsonl (if drive present)

Usage:
  python ingest_all_language_data.py
  python ingest_all_language_data.py --with-asjp
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold")
ASJP = Path(r"D:\training data\pflt_linguistics\02_cognate_lineage\asjp\forms.csv")
POOL = DRIVE / "classical_grc_la_pool.jsonl"
OUT = DATA / "expanded_gold.jsonl"
REPORT = DATA / "expanded_gold_report.json"

FOCUS = {
    "grc", "la", "lat", "ang", "akk", "sum", "san", "hit", "en",
    "egy", "egx", "cop", "heb", "he", "arc", "peo", "non", "got", "sga",
    "fro", "frm", "gml", "gmh", "goh", "osx", "mga", "cu", "orv", "sa",
    "pi", "pli", "ar", "fa", "pal", "uga", "phn", "xcl", "hy", "syc",
    "pro", "osp", "roa-opt",
}


def meaning_key(g: str) -> str:
    g = (g or "").strip().lower()
    g = re.sub(r"^(a|an|the)\s+", "", g)
    g = re.sub(r"[^a-z0-9]+", "_", g)
    return g.strip("_")[:80] or "unknown"


def _norm_lang(lang: str) -> str:
    lang = (lang or "").lower().strip()
    return {"lat": "la", "el": "grc", "eng": "en", "egx": "egy", "egy": "egy"}.get(lang, lang)


def _mk_rec(
    lang: str,
    word: str,
    tgt: str,
    *,
    conf: float = 0.85,
    title: str = "",
    pos: str = "",
    tier: str = "A",
    is_name: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    lang = _norm_lang(lang)
    word = (word or "").strip()
    tgt = (tgt or "").strip()
    if not word or not tgt or len(word) > 80:
        return None
    if lang and lang not in FOCUS and lang not in {"egy", "grc", "la", "ang"}:
        # keep extra historical if short code
        if len(lang) > 4:
            return None
    mk = meaning_key(tgt)
    if mk in {"unknown", "?", "null", "none"}:
        return None
    rec = {
        "source_lang": lang or "unk",
        "source_word": word,
        "target_lang": "en",
        "target_word": tgt,
        "meaning_key": mk,
        "confidence": float(conf),
        "tier": tier,
        "source_title": title or "ingest_all",
        "pos": pos or "",
        "is_name": bool(is_name) if is_name is not None else False,
    }
    if is_name is None:
        # light name heuristic
        tw = tgt
        if pos.lower() == "name" or (tw[:1].isupper() and " " not in word and len(word) > 2):
            if re.match(r"^[A-ZÁÉÍÓÚÄÖÜ]", tgt) and not re.search(
                r"\b(water|hand|god|king|law|city|war|love|life|death|man|woman)\b",
                tgt.lower(),
            ):
                rec["is_name"] = True
    return rec


def load_jsonl(path: Path, limit: int = 0) -> List[Dict[str, Any]]:
    rows = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def from_standard_gold(o: Dict[str, Any], title: str = "") -> Optional[Dict[str, Any]]:
    return _mk_rec(
        o.get("source_lang") or o.get("lang") or "",
        o.get("source_word") or o.get("form") or o.get("word") or "",
        o.get("target_word") or o.get("gloss") or o.get("meaning") or "",
        conf=float(o.get("confidence") or o.get("score") or 0.85),
        title=title or o.get("source_title") or o.get("source") or "",
        pos=str(o.get("pos") or ""),
        tier=str(o.get("tier") or "A"),
        is_name=o.get("is_name"),
    )


def from_hieroglyph(o: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Emit multiple forms: char, gardiner, unicode id."""
    out = []
    tgt = o.get("target_word") or o.get("function") or o.get("description") or ""
    conf = float(o.get("confidence") or 0.9)
    title = "hieroglyph_unikemet"
    for word in (
        o.get("char"),
        o.get("gardiner_jsesh"),
        o.get("unicode"),
        (o.get("gardiner_jsesh") or "").lower(),
    ):
        if not word:
            continue
        r = _mk_rec("egy", str(word), str(tgt), conf=conf, title=title, pos="glyph")
        if r:
            out.append(r)
    return out


def from_lexicon_dict(path: Path, lang_hint: str = "", title: str = "") -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(d, dict):
        return []
    rows = []
    for form, gloss in d.items():
        if form.startswith("_") or form in {"built_utc", "n_domains"}:
            continue
        if isinstance(gloss, dict):
            gloss = gloss.get("meaning") or gloss.get("gloss") or gloss.get("en") or ""
        if not isinstance(gloss, str):
            continue
        # lang from script
        lang = lang_hint
        if not lang:
            if any(ord(c) >= 0x13000 for c in form):
                lang = "egy"
            elif any(0x370 <= ord(c) <= 0x3FF or 0x1F00 <= ord(c) <= 0x1FFF for c in form):
                lang = "grc"
            elif re.search(r"[āēīōūăĕĭŏŭ]", form):
                lang = "la"
            elif form.isascii():
                lang = "la" if re.search(r"(us|um|ae|is|or|io)$", form.lower()) else "en"
            else:
                lang = "unk"
        r = _mk_rec(lang, form, gloss, conf=0.88, title=title or path.name, pos="lex")
        if r:
            rows.append(r)
    return rows


def from_domain_lexica(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = []
    by = d.get("by_domain") or {}
    for dom, lex in by.items():
        if not isinstance(lex, dict):
            continue
        for form, gloss in lex.items():
            if not isinstance(gloss, str):
                continue
            r = _mk_rec("en", form, gloss, conf=0.8, title=f"domain_lexica:{dom}", pos="domain")
            if r:
                rows.append(r)
    gsafe = d.get("global_safe") or {}
    if isinstance(gsafe, dict):
        for form, gloss in gsafe.items():
            if isinstance(gloss, str):
                r = _mk_rec("en", form, gloss, conf=0.82, title="domain_lexica:global", pos="domain")
                if r:
                    rows.append(r)
    return rows


def from_asjp(path: Path, limit: int = 50000) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            form = (row.get("Form") or row.get("Value") or "").strip()
            gloss = (row.get("gloss_in_source") or "").strip()
            lang = (row.get("Language_ID") or "asjp").strip()[:24]
            if not form or not gloss or gloss.isdigit():
                continue
            r = _mk_rec(f"asjp_{lang}" if len(lang) < 20 else "asjp", form, gloss, conf=0.7, title="asjp", pos="cognate")
            # normalize lang to short
            if r:
                r["source_lang"] = "asjp"
                rows.append(r)
    return rows


def merge_best(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        if not r:
            continue
        lang = r["source_lang"]
        word = r["source_word"]
        key = f"{lang}|{word}"
        prev = best.get(key)
        conf = float(r.get("confidence") or 0)
        if prev is None or conf >= float(prev.get("confidence") or 0):
            if prev is not None and prev.get("is_name"):
                r = dict(r)
                r["is_name"] = True
            best[key] = r
        elif prev is not None and r.get("is_name"):
            prev["is_name"] = True
    return list(best.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-asjp", action="store_true", help="Include ASJP cognate forms (large)")
    ap.add_argument("--asjp-limit", type=int, default=40000)
    ap.add_argument("--pool-limit", type=int, default=0, help="0 = all pool rows")
    args = ap.parse_args()

    stats: Counter = Counter()
    raw: List[Dict[str, Any]] = []

    def add(rows: List[Dict[str, Any]], tag: str) -> None:
        n = 0
        for r in rows:
            if r:
                raw.append(r)
                n += 1
        stats[tag] = n
        print(f"  +{tag}: {n}", flush=True)

    print("Ingesting local language + hieroglyph sources…", flush=True)

    # Existing gold jsonl
    for p, tag in [
        (DATA / "dictionary_extra_gold.jsonl", "dictionary_extra_gold"),
        (DATA / "dictionary_db_mined_gold.jsonl", "dictionary_db_mined"),
        (DATA / "classical_grc_la_promoted_tierA.jsonl", "promoted_tierA"),
        (DRIVE / "dictionary_extra_gold.jsonl", "drive_dictionary_extra"),
        (DRIVE / "classical_grc_la_promoted_tierA.jsonl", "drive_promoted"),
    ]:
        if p.is_file():
            add([from_standard_gold(o, tag) for o in load_jsonl(p)], tag)

    # historical merged
    for p in (DATA / "historical_gold_merged.json", DRIVE / "historical_gold_merged.json"):
        if p.is_file():
            try:
                blob = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(blob, list):
                    add([from_standard_gold(o, "historical_merged") for o in blob], "historical_merged")
            except Exception:
                pass

    # MAJOR: classical pool (~164k)
    if POOL.is_file():
        print(f"Loading pool {POOL} …", flush=True)
        pool_rows = []
        with POOL.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if args.pool_limit and i >= args.pool_limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                r = from_standard_gold(o, "classical_pool")
                if r:
                    if (o.get("pos") or "").lower() == "name":
                        r["is_name"] = True
                    pool_rows.append(r)
        add(pool_rows, "classical_pool")

    # Hieroglyphs
    for p in (
        DATA / "hieroglyph_unikemet_gold.jsonl",
        DRIVE.parent / "10_visual_scripts" / "hieroglyph_egyptian" / "hieroglyph_unikemet_gold.jsonl",
    ):
        if p.is_file():
            hiero = []
            for o in load_jsonl(p):
                hiero.extend(from_hieroglyph(o))
            add(hiero, "hieroglyph_unikemet")
            break

    # Lexicon dumps
    add(from_lexicon_dict(DATA / "classical_full_trained_lexicon.json", title="classical_full_lex"), "classical_full_lex")
    add(from_lexicon_dict(DATA / "dictionary_classical_lexicon.json", title="dictionary_classical_lex"), "dictionary_classical_lex")
    add(from_lexicon_dict(DATA / "hieroglyph_pflt_lexicon.json", lang_hint="egy", title="hieroglyph_pflt_lex"), "hieroglyph_pflt_lex")
    add(from_domain_lexica(DATA / "domain_lexica.json"), "domain_lexica")

    # Seeds
    try:
        from core_lemma_seeds import seed_records

        add(list(seed_records()), "core_lemma_seeds")
    except Exception as e:
        print("  seeds skip", e, flush=True)

    if args.with_asjp:
        print("Loading ASJP…", flush=True)
        add(from_asjp(ASJP, limit=args.asjp_limit), "asjp")

    print("Merging / deduping…", flush=True)
    merged = merge_best(raw)
    langs = Counter(r["source_lang"] for r in merged)
    names = sum(1 for r in merged if r.get("is_name"))
    core = len(merged) - names

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    drive_out = DRIVE / "expanded_gold.jsonl"
    if DRIVE.is_dir():
        try:
            with drive_out.open("w", encoding="utf-8") as f:
                for r in merged:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        except Exception as e:
            print("drive write skip", e, flush=True)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_raw": len(raw),
        "n_merged": len(merged),
        "n_core_est": core,
        "n_name_est": names,
        "by_source_in": dict(stats),
        "by_lang": dict(langs.most_common(40)),
        "out": str(OUT),
        "drive_out": str(drive_out) if drive_out.exists() else None,
        "note": "Expanded gold for chew_climb / load_all_gold — local only",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2)[:2500], flush=True)
    print(f"Wrote {OUT}  n={len(merged)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
