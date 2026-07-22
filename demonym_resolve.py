#!/usr/bin/env python3
"""
Ethnonym / demonym peel for classical open-set.

Microscope diagnosis: many CORE misses are gentilics (Κρής→Cretan) that
fall through to narrative_flow or wrong neighbor. Finite peel + stem match
against train lexicon (and a small seed table) recovers them without NMT.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from meaning_clean import content_score, fold_form, is_garbage_meaning, is_meta_meaning

try:
    from lang_tables import demonym_seeds as _load_demonyms, ethnonym_suffixes as _load_suffixes
except Exception:  # pragma: no cover
    def _load_demonyms() -> Dict[str, str]:
        return {}

    def _load_suffixes(lang: str = "grc") -> List[str]:
        return []


def _ETHN_SUFFIX_FOR(lang: str = "grc") -> Sequence[str]:
    suf = _load_suffixes(lang)
    if suf:
        return tuple(suf)
    # bootstrap defaults
    return (
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
    )


def _SEED_DEMONYMS() -> Dict[str, str]:
    """Folded form → english gloss (from data/lang_tables/*.json)."""
    return _load_demonyms()


def demonym_resolve(
    form: str,
    lexicon: Dict[str, str],
    *,
    lang: str = "grc",
    min_score: float = 0.70,
) -> Optional[Tuple[str, str, float]]:
    """
    Return (meaning, donor_or_method, score) or None.
    """
    w = fold_form(form)
    if len(w) < 3:
        return None

    seeds = _SEED_DEMONYMS()
    # 1) Seed table exact
    if w in seeds:
        return seeds[w], "demonym_seed", 0.92

    # 2) Peel suffix → stem match in lexicon
    best: Optional[Tuple[str, str, float]] = None
    for suf in sorted(set(_ETHN_SUFFIX_FOR(lang)), key=len, reverse=True):
        sf = fold_form(suf)
        if not sf or not w.endswith(sf):
            continue
        if len(w) - len(sf) < 2:
            continue
        stem = w[: -len(sf)]
        if len(stem) < 2:
            continue
        # seed stem
        for cand in (stem, stem + "η", stem + "α", stem + "ος", stem + "ια", stem + "ηνη"):
            cf = fold_form(cand)
            if cf in seeds:
                m = seeds[cf]
                sc = 0.88
                if best is None or sc > best[2]:
                    best = (m, f"demonym_stem_seed:{cf}", sc)
        # lexicon donors sharing stem prefix
        donors: List[Tuple[str, str]] = []
        for form_k, meaning in lexicon.items():
            fk = fold_form(form_k)
            if not fk or len(fk) < 3:
                continue
            if fk == w:
                continue
            if fk.startswith(stem) or stem.startswith(fk[: max(3, len(stem) - 1)]):
                if is_meta_meaning(meaning) or is_garbage_meaning(meaning):
                    continue
                if content_score(meaning) < 0.35:
                    continue
                donors.append((form_k, meaning))
            if len(donors) > 40:
                break
        if not donors:
            continue
        # vote by content score
        weights: Dict[str, float] = {}
        donor_of: Dict[str, str] = {}
        for f, m in donors:
            weights[m] = weights.get(m, 0.0) + content_score(m)
            donor_of[m] = f
        meaning = max(weights, key=weights.get)
        sc = min(0.90, 0.55 + 0.25 * content_score(meaning) + 0.1 * min(3, len(donors)) / 3)
        if sc >= min_score and (best is None or sc > best[2]):
            best = (meaning, donor_of[meaning], sc)

    # 3) Full-form seed after peel failures
    if best is None:
        # try stripping only final ς/s
        for ch in ("ς", "s", "ν", "n"):
            if w.endswith(ch) and w[:-1] in seeds:
                return seeds[w[:-1]], "demonym_seed_trim", 0.90
    return best
