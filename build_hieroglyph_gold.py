#!/usr/bin/env python3
"""
Build Egyptian hieroglyph Tier-A style gold from Unicode Unikemet.

Source: D:\\training data\\pflt_linguistics\\10_visual_scripts\\unicode_refs\\Unikemet.txt
Authority: Unicode Egyptian Hieroglyph Database (normative UCD contributory file).

Maps:
  Gardiner/JSesh code (A1, D21, ...)  → English function / description
  Unicode codepoint / character       → same

FSOT role: visual-script interlingua seed. Image→glyph is a later U-Net student stage;
this file is the *meaning* teacher table for attested catalog signs.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(r"D:\training data\pflt_linguistics")
UNIKEMET = ROOT / "10_visual_scripts" / "unicode_refs" / "Unikemet.txt"
OUT_DIR = ROOT / "10_visual_scripts" / "hieroglyph_egyptian"
PFLT_DATA = Path(r"C:\Users\damia\Desktop\pflt\data")


def parse_unikemet(path: Path) -> Dict[str, Dict[str, str]]:
    """codepoint -> {tag: value}"""
    by_cp: Dict[str, Dict[str, str]] = defaultdict(dict)
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        cp, tag, val = parts[0], parts[1], parts[2]
        by_cp[cp][tag] = val
    return by_cp


def cp_to_char(cp: str) -> str:
    # U+13000
    n = int(cp.replace("U+", ""), 16)
    return chr(n)


def clean_meaning(func: str, desc: str, fval: str) -> str:
    bits = []
    if func:
        f = func.strip()
        f = re.sub(r"^Classifier\s+", "classifier_", f, flags=re.I)
        f = re.sub(r"^Logogram\s*\(?", "logogram_", f, flags=re.I)
        f = re.sub(r"^Phonemogram.*", "phonemogram", f, flags=re.I)
        f = re.sub(r"[)(/,]+", "_", f)
        f = re.sub(r"\s+", "_", f)
        f = re.sub(r"_+", "_", f).strip("_").lower()
        if f:
            bits.append(f)
    if fval:
        bits.append(f"reading_{fval.strip()}")
    if desc and not bits:
        # short visual gloss
        d = desc.split(".")[0][:80]
        d = re.sub(r"[^A-Za-z0-9]+", "_", d).strip("_").lower()
        bits.append(d or "hieroglyph_sign")
    return "_".join(bits) if bits else "hieroglyph_sign"


def build_records(by_cp: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for cp, tags in sorted(by_cp.items()):
        try:
            ch = cp_to_char(cp)
        except Exception:
            continue
        jsesh = tags.get("kEH_JSesh") or tags.get("kEH_HG") or tags.get("kEH_UniK") or ""
        func = tags.get("kEH_Func") or ""
        desc = tags.get("kEH_Desc") or ""
        fval = tags.get("kEH_FVal") or ""
        core = tags.get("kEH_Core") or "N"
        meaning = clean_meaning(func, desc, fval)
        rec = {
            "source_lang": "egy",  # Egyptian (hieroglyphic stage)
            "source_script": "Egyptian_Hieroglyphs",
            "unicode": cp,
            "char": ch,
            "gardiner_jsesh": jsesh,
            "target_lang": "en",
            "target_word": meaning,
            "function": func,
            "phonetic_value": fval,
            "description": desc,
            "core": core,
            "confidence": 0.95 if core == "C" else 0.85,
            "tier": "A" if core == "C" and (func or fval) else "B",
            "source_title": "Unicode Unikemet (Egyptian Hieroglyph Database)",
            "epoch": 1,  # after Sumerian/Akkadian writing; Egyptian writing ~3200 BCE band
        }
        rows.append(rec)
    return rows


def build_lexicon(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Keys usable by PFLT pul_terms: gardiner codes + unicode char."""
    lex: Dict[str, str] = {}
    for r in rows:
        m = r["target_word"]
        if r.get("gardiner_jsesh"):
            g = r["gardiner_jsesh"].strip()
            lex[g.lower()] = m
            lex[g.upper()] = m
            # A1 style without leading zeros variants
            g2 = re.sub(r"^([A-Za-z]+)0+(\d)", r"\1\2", g)
            if g2 != g:
                lex[g2.lower()] = m
        if r.get("char"):
            lex[r["char"]] = m
        if r.get("unicode"):
            lex[r["unicode"].lower()] = m
            lex[r["unicode"].replace("U+", "u").lower()] = m
    return lex


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PFLT_DATA.mkdir(parents=True, exist_ok=True)

    by_cp = parse_unikemet(UNIKEMET)
    rows = build_records(by_cp)
    lex = build_lexicon(rows)

    gold_path = OUT_DIR / "hieroglyph_unikemet_gold.jsonl"
    with gold_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lex_path = OUT_DIR / "hieroglyph_pflt_lexicon.json"
    lex_path.write_text(json.dumps(lex, indent=2, ensure_ascii=False), encoding="utf-8")

    # copy into pflt data for easy load
    (PFLT_DATA / "hieroglyph_pflt_lexicon.json").write_text(
        json.dumps(lex, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PFLT_DATA / "hieroglyph_unikemet_gold.jsonl").write_text(
        gold_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    tier_a = sum(1 for r in rows if r["tier"] == "A")
    with_func = sum(1 for r in rows if r.get("function"))
    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(UNIKEMET),
        "n_codepoints": len(rows),
        "n_lexicon_keys": len(lex),
        "tier_a": tier_a,
        "tier_b": len(rows) - tier_a,
        "with_function": with_func,
        "gold_path": str(gold_path),
        "lexicon_path": str(lex_path),
        "pipeline_note": (
            "Meaning table from Unikemet. Image/glyph recognition is a separate "
            "U-Net student stage; FSOT scalar still modulates narrative output."
        ),
    }
    (OUT_DIR / "hieroglyph_build_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))

    # Smoke: a few famous signs
    smoke = ["A1", "D21", "G17", "N5", "S34", "𓀀", "𓂋", "𓅓"]
    print("smoke_lexicon:")
    for k in smoke:
        print(f"  {k!r} -> {lex.get(k) or lex.get(k.lower()) or lex.get(k.upper())}")


if __name__ == "__main__":
    main()
