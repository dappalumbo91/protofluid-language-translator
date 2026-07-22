#!/usr/bin/env python3
"""
Per-language translation-layer tables (keywords, seeds, form senses).

Loads JSON from data/lang_tables/ instead of growing Python monoliths.

Layout:
  data/lang_tables/
    _shared.json          # sense_clusters, domain_keywords (English gloss layer)
    grc.json              # form_sense_prefer, seeds, participles, demonyms
    la.json
    ang.json
    en.json
    ...

Each language file schema:
  {
    "lang": "grc",
    "form_sense_prefer": { "γνωμων": ["sundial", ...], ... },
    "seeds": [ {"form": "γνώμων", "gloss": "sundial"}, ... ],
    "participle_stems": [ {"stem": "βιασμεν", "gloss": "forced"}, ... ],
    "demonym_seeds": { "κρης": "cretan", ... },
    "ethnonym_suffixes": ["ίτης", ...],   # optional
    "sense_clusters": [ ["hot", "boiling"], ... ]  # optional lang-extra
  }

_shared.json:
  {
    "sense_clusters": [ ["water", "aqua", ...], ... ],
    "domain_keywords": { "mythological": ["god", ...], ... }
  }
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent
TABLE_DIR = ROOT / "data" / "lang_tables"

# langs we always try to load
DEFAULT_LANGS = ("grc", "la", "ang", "en", "lat", "el", "oe")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_shared() -> Dict[str, Any]:
    return _read_json(TABLE_DIR / "_shared.json")


@lru_cache(maxsize=32)
def load_lang(lang: str) -> Dict[str, Any]:
    """Load one language pack; aliases map to primary files."""
    lang = (lang or "").lower().strip()
    alias = {
        "el": "grc",
        "greek": "grc",
        "lat": "la",
        "latin": "la",
        "oe": "ang",
        "anglo-saxon": "ang",
        "old_english": "ang",
        "english": "en",
    }.get(lang, lang)
    data = _read_json(TABLE_DIR / f"{alias}.json")
    if data and "lang" not in data:
        data["lang"] = alias
    return data


def reload_all() -> None:
    """Clear cache after editing JSON on disk."""
    load_shared.cache_clear()
    load_lang.cache_clear()
    _merged_form_sense.cache_clear()
    _merged_demonyms.cache_clear()
    _all_seeds.cache_clear()
    _all_clusters.cache_clear()
    _domain_keys.cache_clear()
    _participle_stems.cache_clear()


@lru_cache(maxsize=1)
def _merged_form_sense() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for lang in DEFAULT_LANGS:
        pack = load_lang(lang)
        for form, senses in (pack.get("form_sense_prefer") or {}).items():
            key = str(form).lower()
            vals = [str(s) for s in senses]
            if key in out:
                # merge unique
                seen = set(out[key])
                for s in vals:
                    if s not in seen:
                        out[key].append(s)
                        seen.add(s)
            else:
                out[key] = list(vals)
    return out


@lru_cache(maxsize=1)
def _merged_demonyms() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for lang in DEFAULT_LANGS:
        pack = load_lang(lang)
        for form, gloss in (pack.get("demonym_seeds") or {}).items():
            out[str(form).lower()] = str(gloss)
    return out


@lru_cache(maxsize=1)
def _all_seeds() -> List[Tuple[str, str, str]]:
    """(lang, form, gloss) triples for train inject."""
    rows: List[Tuple[str, str, str]] = []
    seen = set()
    for lang in DEFAULT_LANGS:
        pack = load_lang(lang)
        lang_id = pack.get("lang") or lang
        for item in pack.get("seeds") or []:
            if isinstance(item, dict):
                form = item.get("form") or ""
                gloss = item.get("gloss") or ""
                lid = item.get("lang") or lang_id
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                if len(item) == 3:
                    lid, form, gloss = item[0], item[1], item[2]
                else:
                    lid, form, gloss = lang_id, item[0], item[1]
            else:
                continue
            key = f"{lid}|{form}"
            if not form or not gloss or key in seen:
                continue
            seen.add(key)
            rows.append((str(lid), str(form), str(gloss)))
    return rows


@lru_cache(maxsize=1)
def _all_clusters() -> List[Set[str]]:
    clusters: List[Set[str]] = []
    shared = load_shared()
    for cl in shared.get("sense_clusters") or []:
        clusters.append({str(x).lower() for x in cl})
    for lang in DEFAULT_LANGS:
        pack = load_lang(lang)
        for cl in pack.get("sense_clusters") or []:
            clusters.append({str(x).lower() for x in cl})
    return clusters


@lru_cache(maxsize=1)
def _domain_keys() -> Dict[str, Tuple[str, ...]]:
    shared = load_shared()
    raw = shared.get("domain_keywords") or {}
    return {str(k): tuple(str(x) for x in v) for k, v in raw.items()}


@lru_cache(maxsize=1)
def _participle_stems() -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for lang in DEFAULT_LANGS:
        pack = load_lang(lang)
        for item in pack.get("participle_stems") or []:
            if isinstance(item, dict):
                out.append((str(item.get("stem") or ""), str(item.get("gloss") or "")))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append((str(item[0]), str(item[1])))
    return [(a, b) for a, b in out if a and b]


def form_sense_prefer() -> Dict[str, List[str]]:
    return dict(_merged_form_sense())


def demonym_seeds() -> Dict[str, str]:
    return dict(_merged_demonyms())


def gap_seeds() -> List[Tuple[str, str, str]]:
    return list(_all_seeds())


def extra_seeds() -> List[Tuple[str, str, str]]:
    """Alias for core_lemma / remedy inject path."""
    return gap_seeds()


def sense_clusters() -> List[Set[str]]:
    return [set(c) for c in _all_clusters()]


def domain_keywords() -> Dict[str, Sequence[str]]:
    return dict(_domain_keys())


def participle_stems() -> List[Tuple[str, str]]:
    return list(_participle_stems())


def ethnonym_suffixes(lang: str = "grc") -> List[str]:
    pack = load_lang(lang)
    suf = pack.get("ethnonym_suffixes")
    if suf:
        return [str(s) for s in suf]
    # default classical set if file omits
    return [
        "ιώτης", "ιώτου", "ιώται",
        "ίτης", "ίτου", "ῖται", "ιτης", "ιτου",
        "αῖος", "αίου", "αιος", "αιου",
        "ικός", "ικοῦ", "ική", "ικόν", "ικος", "ικου",
        "ηνός", "ηνοῦ", "ηνος", "ηνου",
        "ώτης", "ώτου", "ωτης",
        "εύς", "έως", "ευς",
        "enses", "ensis", "anum", "anus", "ana", "ani",
        "icus", "ica", "icum",
        "ης", "ου", "ος", "ων", "ις",
    ]


def table_dir() -> Path:
    return TABLE_DIR


def ensure_dir() -> Path:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    return TABLE_DIR
