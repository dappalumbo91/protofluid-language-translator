#!/usr/bin/env python3
"""
Domain-gated sense pick when a stem has multiple train-supported meanings.

OSS parallel: Whitaker/Collatinus list multiple senses; domain/context ranks them.
FSOT: use FSOT domain *label* keywords only (not free LLM).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from meaning_clean import content_score, is_meta_meaning

# context → keywords that boost matching senses
_DOMAIN_KEYS: Dict[str, Sequence[str]] = {
    "mythological": (
        "god", "goddess", "spirit", "myth", "hero", "underworld", "hades",
        "divine", "oracle", "sacrifice", "nymph", "titan", "zeus", "temple",
    ),
    "historical": (
        "king", "war", "law", "people", "city", "army", "empire", "consul",
        "senate", "province", "hand", "water", "land", "man", "woman",
    ),
    "linguistic": (
        "word", "speech", "language", "voice", "name", "write", "read", "say",
    ),
    "english": (
        "the", "a", "of", "to", "and",
    ),
    "administrative": (
        "law", "record", "tax", "office", "order", "public", "official",
    ),
    "biological": ("life", "body", "blood", "plant", "animal", "cell"),
    "genomic": ("gene", "dna", "code", "protein", "cell"),
    "geological": ("rock", "earth", "stone", "mineral", "mountain"),
    "cosmological": ("star", "sky", "heaven", "cosmos", "sun", "moon"),
    "paranormal": ("spirit", "signal", "ghost", "soul", "occult"),
}


def rank_senses(
    meanings: Sequence[str],
    context: str = "historical",
) -> List[Tuple[str, float]]:
    """Return meanings sorted by domain affinity + content quality."""
    keys = _DOMAIN_KEYS.get(context, _DOMAIN_KEYS["historical"])
    scored: List[Tuple[str, float]] = []
    for m in meanings:
        if not m or is_meta_meaning(m):
            scored.append((m, 0.05))
            continue
        ml = m.lower().replace("_", " ")
        hit = sum(1 for k in keys if k in ml)
        s = 0.4 * content_score(m) + 0.15 * min(4, hit)
        # penalize very long encyclopedia glosses
        if len(m) > 48:
            s *= 0.7
        scored.append((m, s))
    scored.sort(key=lambda x: -x[1])
    return scored


def pick_sense(
    meanings: Sequence[str],
    context: str = "historical",
    *,
    min_margin: float = 0.04,
) -> Optional[str]:
    """
    Pick best sense if it clearly wins; else top content sense.
    """
    if not meanings:
        return None
    ranked = rank_senses(list(dict.fromkeys(meanings)), context)
    if not ranked:
        return None
    if len(ranked) == 1:
        return ranked[0][0]
    if ranked[0][1] >= ranked[1][1] + min_margin:
        return ranked[0][0]
    # tie: prefer higher content_score
    return max(ranked[:3], key=lambda x: content_score(x[0]))[0]
