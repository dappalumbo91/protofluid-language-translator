#!/usr/bin/env python3
"""
Historical-first gold corpus for PFLT (FSOT natural communicator).

Accuracy policy:
  Tier A — human-curated seed + DB historical pairs with confidence >= 0.9
  Tier B — validation candidates (dictionary-derived; not final truth until adjudicated)
  Tier C — modern language pairs (deferred until A is solid)

Chronological training order (attested written tradition):
  sum/akk → hit/san → grc → lat/la → ang → (later) romance/germanic moderns

No animal vocal data here yet — separate bioacoustic phase after human language accuracy.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DICT_ROOT = Path(r"C:\Users\damia\Desktop\Dictionary")
SEED_PATH = DICT_ROOT / "historical_linguistics_seed.json"
CAND_PATH = DICT_ROOT / "data" / "bridge_patterns" / "historical_validation_candidates_grc_la.json"
DB_PATH = DICT_ROOT / "data" / "dictionary.db"

# Epoch order for historical-first curriculum (lower = earlier)
LANG_EPOCH: Dict[str, int] = {
    "sum": 0,   # Sumerian ~3000 BCE
    "akk": 1,   # Akkadian ~2300 BCE
    "hit": 2,   # Hittite ~1600 BCE
    "san": 3,   # Sanskrit / Vedic ~1500 BCE
    "grc": 4,   # Ancient Greek classical
    "lat": 5,   # Latin
    "la": 5,    # Latin (Wiktionary code)
    "ang": 6,   # Old English
    "en": 9,    # Modern English (target, not source curriculum)
}

# Normalize language codes used across projects
LANG_ALIASES = {
    "lat": "la",
    "latin": "la",
    "greek": "grc",
    "ancient_greek": "grc",
    "sumerian": "sum",
    "akkadian": "akk",
    "old_english": "ang",
    "sanskrit": "san",
    "hittite": "hit",
}


@dataclass(frozen=True)
class GoldPair:
    source_lang: str
    source_word: str
    target_lang: str
    target_word: str
    gloss: str
    confidence: float
    source_title: str
    tier: str  # A | B
    epoch: int

    def key(self) -> str:
        return f"{self.source_lang}:{self.source_word.lower()}"


def _norm_lang(code: str) -> str:
    c = (code or "").strip().lower()
    return LANG_ALIASES.get(c, c)


def _norm_word(w: str) -> str:
    return " ".join((w or "").strip().split())


def load_seed_pairs(path: Path = SEED_PATH) -> List[GoldPair]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: List[GoldPair] = []
    for row in raw:
        sl = _norm_lang(row["source_lang"])
        conf = float(row.get("confidence", 1.0))
        out.append(
            GoldPair(
                source_lang=sl,
                source_word=_norm_word(row["source_word"]),
                target_lang=_norm_lang(row.get("target_lang", "en")),
                target_word=_norm_word(row["target_word"]),
                gloss=row.get("gloss") or "",
                confidence=conf,
                source_title=row.get("source_title") or "historical_seed",
                tier="A" if conf >= 0.9 else "B",
                epoch=LANG_EPOCH.get(sl, 50),
            )
        )
    return out


def load_db_historical_pairs(
    path: Path = DB_PATH,
    min_confidence: float = 0.9,
) -> List[GoldPair]:
    if not path.exists():
        return []
    c = sqlite3.connect(str(path))
    cur = c.cursor()
    rows = cur.execute(
        """
        SELECT source_lang_code, source_word, target_lang_code, target_word,
               gloss, confidence, page_ref
        FROM historical_translation_pairs
        WHERE confidence >= ?
        """,
        (min_confidence,),
    ).fetchall()
    c.close()
    out: List[GoldPair] = []
    for sl, sw, tl, tw, gloss, conf, page in rows:
        sln = _norm_lang(sl)
        out.append(
            GoldPair(
                source_lang=sln,
                source_word=_norm_word(sw),
                target_lang=_norm_lang(tl),
                target_word=_norm_word(tw),
                gloss=gloss or "",
                confidence=float(conf if conf is not None else 1.0),
                source_title=page or "dictionary.db:historical_translation_pairs",
                tier="A",
                epoch=LANG_EPOCH.get(sln, 50),
            )
        )
    return out


def load_validation_candidates(path: Path = CAND_PATH) -> List[GoldPair]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: List[GoldPair] = []
    for row in raw:
        sl = _norm_lang(row["source_lang"])
        conf = float(row.get("confidence", 0.75))
        out.append(
            GoldPair(
                source_lang=sl,
                source_word=_norm_word(row["source_word"]),
                target_lang=_norm_lang(row.get("target_lang", "en")),
                target_word=_norm_word(row["target_word"]),
                gloss=row.get("gloss") or "",
                confidence=conf,
                source_title=row.get("source_title") or "validation_candidate",
                tier="B",
                epoch=LANG_EPOCH.get(sl, 50),
            )
        )
    return out


def merge_gold(
    *,
    include_candidates: bool = True,
    min_tier_a_conf: float = 0.9,
) -> List[GoldPair]:
    """Deduplicate by (lang, source_word); prefer higher tier then higher confidence."""
    merged: Dict[str, GoldPair] = {}

    def consider(p: GoldPair) -> None:
        k = p.key()
        prev = merged.get(k)
        if prev is None:
            merged[k] = p
            return
        # Prefer A over B; then higher confidence
        rank = {"A": 2, "B": 1}
        if rank[p.tier] > rank[prev.tier] or (
            p.tier == prev.tier and p.confidence > prev.confidence
        ):
            merged[k] = p

    for p in load_seed_pairs():
        if p.tier == "A" or p.confidence >= min_tier_a_conf:
            consider(p)
        else:
            consider(p)
    for p in load_db_historical_pairs(min_confidence=min_tier_a_conf):
        consider(p)
    if include_candidates:
        for p in load_validation_candidates():
            consider(p)

    pairs = list(merged.values())
    pairs.sort(key=lambda p: (p.epoch, p.source_lang, p.source_word.lower()))
    return pairs


def gold_as_lexicon(pairs: Iterable[GoldPair]) -> Dict[str, str]:
    """
    Build pul_terms-style map: source surface form -> English target meaning.
    Also registers underscore/hyphen variants for multiword forms.
    """
    lex: Dict[str, str] = {}
    for p in pairs:
        if p.target_lang not in {"en", "eng"}:
            continue
        # Stable meaning key: prefer gloss short form via target_word
        meaning = p.target_word.replace(" ", "_")
        for form in {
            p.source_word.lower(),
            p.source_word,  # preserve Greek polytonic case forms as-is lower already
        }:
            key = form.lower()
            lex[key] = meaning
            if " " in key:
                lex[key.replace(" ", "-")] = meaning
                lex[key.replace(" ", "_")] = meaning
            if "-" in key:
                lex[key.replace("-", " ")] = meaning
    return lex


def curriculum_by_epoch(pairs: List[GoldPair]) -> Dict[str, List[GoldPair]]:
    buckets: Dict[str, List[GoldPair]] = {}
    for p in pairs:
        label = {
            0: "0_sumerian",
            1: "1_akkadian",
            2: "2_hittite",
            3: "3_sanskrit",
            4: "4_ancient_greek",
            5: "5_latin",
            6: "6_old_english",
        }.get(p.epoch, f"9_other_{p.source_lang}")
        buckets.setdefault(label, []).append(p)
    return dict(sorted(buckets.items()))


def summary(pairs: List[GoldPair]) -> Dict[str, Any]:
    by_lang = Counterish(pairs)
    by_tier: Dict[str, int] = {}
    for p in pairs:
        by_tier[p.tier] = by_tier.get(p.tier, 0) + 1
    return {
        "n_pairs": len(pairs),
        "by_lang": by_lang,
        "by_tier": by_tier,
        "curriculum": {k: len(v) for k, v in curriculum_by_epoch(pairs).items()},
    }


def Counterish(pairs: List[GoldPair]) -> Dict[str, int]:
    d: Dict[str, int] = {}
    for p in pairs:
        d[p.source_lang] = d.get(p.source_lang, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: LANG_EPOCH.get(kv[0], 99)))


def export_json(pairs: List[GoldPair], path: Path) -> None:
    path.write_text(
        json.dumps([asdict(p) for p in pairs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    pairs = merge_gold(include_candidates=True)
    print(json.dumps(summary(pairs), indent=2, ensure_ascii=False))
    out = Path(__file__).resolve().parent / "data" / "historical_gold_merged.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_json(pairs, out)
    print("wrote", out)
