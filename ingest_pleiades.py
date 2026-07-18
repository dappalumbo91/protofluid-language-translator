#!/usr/bin/env python3
"""
Ingest Pleiades ancient-place names into PFLT name gazetteer contacts.

Source (preferred local):
  D:\\training data\\pflt_linguistics\\08_rosetta_fsot\\pleiades\\names.csv
  D:\\training data\\pflt_linguistics\\08_rosetta_fsot\\pleiades\\places.csv

Or download GIS package CSVs from:
  https://github.com/isawnyu/pleiades.datasets (data/gis/)

Policy:
  - Entity = English place title (from places.title or romanized name)
  - Multiple attested/romanized forms → historical contacts (la/grc/en/…)
  - Does NOT invent coordinates into translation; geo is optional metadata
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA = Path(__file__).resolve().parent / "data"
PLEIADES_DIR = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\pleiades")
OUT_JSON = DATA / "pleiades_contacts.json"
OUT_DRIVE = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\pleiades_contacts.json")
GAZ_PATH = DATA / "name_gazetteer.json"

# BCP47-ish language tags seen in Pleiades → our codes
_LANG_MAP = {
    "la": "la",
    "lat": "la",
    "grc": "grc",
    "el": "grc",
    "en": "en",
    "ang": "ang",
    "egy": "egy",
    "akk": "akk",
    "arc": "arc",
    "he": "he",
    "ar": "ar",
    "fa": "fa",
    "sa": "san",
    "hit": "hit",
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def title_key(s: str) -> str:
    s = re.sub(r"\s*\(.*?\)\s*", " ", s or "")
    s = re.sub(r"[^a-zA-Z0-9\u0370-\u03ff\u1f00-\u1fff]+", "_", s.strip().lower())
    return s.strip("_")[:60] or "unknown_place"


def map_lang(tag: str) -> str:
    tag = (tag or "").lower().split("-")[0]
    return _LANG_MAP.get(tag, tag if tag in {"la", "grc", "en", "ang"} else "en")


def load_places(path: Path) -> Dict[str, str]:
    """place_id → english title key."""
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = (row.get("id") or row.get("place_id") or "").strip()
            title = (row.get("title") or "").strip()
            if not pid or not title:
                continue
            out[pid] = title_key(title)
    return out


def load_names(path: Path, place_titles: Dict[str, str], max_rows: int = 0) -> Tuple[Dict, Dict, Dict]:
    """
    Returns:
      by_lang_form: lang|fold → title_key
      by_form: fold → title_key
      by_title: title_key → [lang|form, ...]
    """
    by_lang_form: Dict[str, str] = {}
    by_form: Dict[str, str] = {}
    by_title: Dict[str, List[str]] = defaultdict(list)
    if not path.exists():
        return by_lang_form, by_form, by_title

    n = 0
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n += 1
            if max_rows and n > max_rows:
                break
            pid = (row.get("place_id") or "").strip()
            title = place_titles.get(pid) or title_key(row.get("title") or row.get("romanized_form_1") or "")
            if not title or title == "unknown_place":
                continue
            lang = map_lang(row.get("language_tag") or "en")
            forms = []
            for col in (
                "attested_form",
                "romanized_form_1",
                "romanized_form_2",
                "romanized_form_3",
                "title",
            ):
                v = (row.get(col) or "").strip()
                if v and len(v) >= 2:
                    forms.append(v)
            for form in forms:
                nf = fold(form)
                if len(nf) < 2:
                    continue
                by_form.setdefault(nf, title)
                by_lang_form.setdefault(f"{lang}|{nf}", title)
                key = f"{lang}|{nf}"
                if key not in by_title[title]:
                    by_title[title].append(key)
                # English title as contact form
                by_form.setdefault(title, title)
                by_form.setdefault(title.replace("_", ""), title)
    return by_lang_form, by_form, by_title


def merge_into_gazetteer(
    by_lang_form: Dict[str, str],
    by_form: Dict[str, str],
    by_title: Dict[str, List[str]],
) -> Dict:
    """Merge Pleiades contacts into name_gazetteer.json (production full gaz)."""
    if not GAZ_PATH.exists():
        from name_gazetteer import build_from_dictionary

        build_from_dictionary()
    gaz = json.loads(GAZ_PATH.read_text(encoding="utf-8"))
    g_form = gaz.setdefault("by_form", {})
    g_lang = gaz.setdefault("by_lang_form", {})
    g_title = gaz.setdefault("by_title", {})
    g_kind = gaz.setdefault("kind", {})
    g_tr = gaz.setdefault("translit", {})

    added = 0
    for k, title in by_lang_form.items():
        if k not in g_lang:
            g_lang[k] = title
            added += 1
        g_kind.setdefault(title, "place")
    for k, title in by_form.items():
        g_form.setdefault(k, title)
        g_kind.setdefault(title, "place")
        # latinized-looking keys double as translit hits
        if re.fullmatch(r"[a-z_]+", k) and len(k) >= 3:
            g_tr.setdefault(k, title)
    for title, forms in by_title.items():
        bucket = g_title.setdefault(title, [])
        for f in forms:
            if f not in bucket:
                bucket.append(f)

    gaz["pleiades_merge"] = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_lang_forms_added": added,
        "n_pleiades_titles": len(by_title),
        "n_pleiades_forms": len(by_form),
    }
    gaz["stats"] = gaz.get("stats") or {}
    gaz["stats"]["pleiades_forms"] = len(by_form)
    gaz["stats"]["pleiades_titles"] = len(by_title)
    gaz["stats"]["n_forms"] = len(g_form)
    gaz["stats"]["n_contacts_multi"] = sum(1 for v in g_title.values() if len(v) >= 2)

    GAZ_PATH.write_text(json.dumps(gaz, ensure_ascii=False), encoding="utf-8")
    drive_gaz = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\name_gazetteer.json")
    drive_gaz.parent.mkdir(parents=True, exist_ok=True)
    drive_gaz.write_text(json.dumps(gaz, ensure_ascii=False), encoding="utf-8")
    return gaz["pleiades_merge"]


def main() -> None:
    names_p = PLEIADES_DIR / "names.csv"
    places_p = PLEIADES_DIR / "places.csv"
    if not names_p.exists():
        # try pflt data
        names_p = DATA / "pleiades" / "names.csv"
        places_p = DATA / "pleiades" / "places.csv"
    if not names_p.exists():
        raise SystemExit(
            f"missing {PLEIADES_DIR / 'names.csv'} — download Pleiades GIS CSVs first"
        )

    print("loading places...", flush=True)
    place_titles = load_places(places_p)
    print(f"  places={len(place_titles)}", flush=True)
    print("loading names...", flush=True)
    by_lang, by_form, by_title = load_names(names_p, place_titles)
    multi = {t: fs for t, fs in by_title.items() if len(fs) >= 2}
    print(
        f"  forms={len(by_form)} titles={len(by_title)} multi_contact={len(multi)}",
        flush=True,
    )

    blob = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(names_p),
        "n_forms": len(by_form),
        "n_titles": len(by_title),
        "n_multi_contact": len(multi),
        "by_lang_form_sample": dict(list(by_lang.items())[:20]),
        "contacts_sample": dict(list(multi.items())[:25]),
        "by_lang_form": by_lang,
        "by_form": by_form,
        "by_title": {k: v[:30] for k, v in by_title.items()},
    }
    # write compact contacts for merge (full maps)
    OUT_JSON.write_text(
        json.dumps(
            {
                "built_utc": blob["built_utc"],
                "n_forms": blob["n_forms"],
                "n_titles": blob["n_titles"],
                "n_multi_contact": blob["n_multi_contact"],
                "by_lang_form": by_lang,
                "by_form": by_form,
                "by_title": dict(by_title),
                "contacts_sample": blob["contacts_sample"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    OUT_DRIVE.parent.mkdir(parents=True, exist_ok=True)
    OUT_DRIVE.write_text(OUT_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    print("wrote", OUT_JSON, flush=True)

    print("merging into name_gazetteer.json ...", flush=True)
    merge_stats = merge_into_gazetteer(by_lang, by_form, by_title)
    print("merge", merge_stats, flush=True)
    print("sample contacts", list(multi.items())[:8], flush=True)


if __name__ == "__main__":
    main()
