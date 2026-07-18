#!/usr/bin/env python3
"""
Reverse morphology for open-set: given an unknown surface form, strip
inflectional endings and probe the train lexicon for known lemmas that
share the same stem.

Complementary to paradigm_expand (which generates forms from known lemmas).
This is finite table morphology only — no free generation.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from gapfill_student import edit_sim
from meaning_clean import content_score, fold_form, is_meta_meaning

# Longer first
_LA_STRIP = (
    "ationibus", "ationem", "ationis", "ationes", "ationi", "atione",
    "tionibus", "tionem", "tionis", "tiones", "tioni", "tione",
    "ionibus", "ionem", "ionis", "iones", "ioni", "ione", "ionum",
    "tatibus", "tatem", "tatis", "tates", "tate", "tatum",
    "oribus", "orem", "oris", "ores", "ore", "orum",
    "arum", "orum", "ibus", "uum", "eus", "ius", "ium",
    "arum", "orum",
    "abant", "ebant", "iebant", "abantur", "ebantur",
    "antur", "untur", "amini", "imini",
    "amus", "atis", "imus", "itis", "iunt",
    "avi", "atum", "ivi", "itum",
    "are", "ere", "ire",
    "us", "um", "am", "ae", "as", "is", "os", "em", "es", "en",
    "or", "ur", "ux", "ix", "ax", "ex",
    "nt", "ns",
    "a", "o", "i", "e", "u",
)

_GRC_STRIP = (
    "οισιν", "αισιν", "εσσιν", "εων", "εως", "εσιν", "εσι",
    "οις", "αις", "ους", "ων", "ον", "ος", "ης", "ης", "ην", "ας", "αι",
    "ου", "ῳ", "ῃ", "εις", "ιν", "ιου", "ιον", "ιος", "ια",
    "της", "του", "τες", "των", "τα",
    "ευς", "εως", "εα", "ευ",
    "ικος", "ικη", "ικον", "ικου", "ικης",
    "ισσα", "ισσης",
    "η", "α", "ι", "ν", "ε", "ο",
)

_GRC_LAT_STRIP = (
    "eous", "ious", "icus", "ica", "icum", "esis", "osis",
    "tes", "tis", "tos", "eus", "ios", "ion", "ias",
    "os", "on", "es", "as", "is", "ou", "oi", "ai", "ae",
    "a", "e", "i", "o", "n", "s",
)

_ANG_STRIP = (
    "ienne", "enne", "ende", "odon", "odon",
    "ath", "eth", "ian", "igan", "ende",
    "um", "an", "as", "es", "e", "a", "u", "o",
)

# Common lemma endings to reattach when probing the lexicon
_LA_LEMMA_ENDS = ("us", "um", "a", "is", "es", "or", "io", "tas", "tio", "are", "ere", "ire", "o", "")
_GRC_LEMMA_ENDS = ("ος", "η", "α", "ον", "ις", "ευς", "ης", "ων", "ος", "")
_GRC_LAT_LEMMA_ENDS = ("os", "on", "e", "a", "is", "eus", "es", "")
_ANG_LEMMA_ENDS = ("an", "ian", "a", "e", "u", "")


def _strips_for(lang: str) -> Sequence[str]:
    lang = (lang or "la").lower()
    if lang in {"grc", "el"}:
        return _GRC_STRIP + _GRC_LAT_STRIP
    if lang in {"ang", "oe"}:
        return _ANG_STRIP
    return _LA_STRIP


def _lemma_ends(lang: str, greek_script: bool) -> Sequence[str]:
    lang = (lang or "la").lower()
    if lang in {"grc", "el"}:
        return _GRC_LEMMA_ENDS if greek_script else _GRC_LAT_LEMMA_ENDS
    if lang in {"ang", "oe"}:
        return _ANG_LEMMA_ENDS
    return _LA_LEMMA_ENDS


def candidate_stems(form: str, lang: str = "la") -> List[str]:
    """Return stem candidates by stripping known endings (longest first)."""
    w = fold_form(form)
    if len(w) < 3:
        return [w] if w else []
    out: List[str] = [w]
    for suf in sorted(set(_strips_for(lang)), key=len, reverse=True):
        sf = fold_form(suf)
        if not sf:
            continue
        if w.endswith(sf) and len(w) - len(sf) >= 3:
            stem = w[: -len(sf)]
            if stem not in out:
                out.append(stem)
            # also double-strip once for case+number stacks
            for suf2 in sorted(set(_strips_for(lang)), key=len, reverse=True):
                sf2 = fold_form(suf2)
                if stem.endswith(sf2) and len(stem) - len(sf2) >= 3:
                    s2 = stem[: -len(sf2)]
                    if s2 not in out:
                        out.append(s2)
                    break
    return out


def reverse_resolve(
    form: str,
    lexicon: Dict[str, str],
    lang: str = "la",
    *,
    prefix_index: Optional[Dict[str, List[str]]] = None,
    min_stem: int = 3,
    lemma_end_only: bool = False,
    min_score: float = 0.78,
    min_sim_lemma: float = 0.42,
) -> Optional[Tuple[str, str, float, str]]:
    """
    Probe lexicon for lemma sharing stem with form.
    Returns (meaning, donor_form, score, method) or None.

    Latin-safe mode: min_stem=5, lemma_end_only=True, min_score=0.85, min_sim_lemma=0.55
    """
    if not form or not lexicon:
        return None
    nf = fold_form(form)
    if nf in lexicon:
        return lexicon[nf], nf, 1.0, "rev_exact_fold"
    if form in lexicon:
        return lexicon[form], form, 1.0, "rev_exact"
    if form.lower() in lexicon:
        return lexicon[form.lower()], form.lower(), 1.0, "rev_exact_lower"

    greek_script = bool(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", form))
    stems = candidate_stems(form, lang)
    ends = _lemma_ends(lang, greek_script)

    best: Optional[Tuple[str, str, float, str]] = None

    def consider(donor: str, meaning: str, method: str, base: float) -> None:
        nonlocal best
        if not meaning:
            return
        if lemma_end_only and method not in {"rev_lemma_end", "rev_exact_fold", "rev_exact", "rev_exact_lower"}:
            return
        df = fold_form(donor)
        sim = edit_sim(nf, df)
        if sim < 0.50 and method != "rev_lemma_end":
            return
        if method == "rev_lemma_end" and sim < min_sim_lemma:
            return
        if abs(len(nf) - len(df)) > 4 and sim < 0.60:
            return
        cs = content_score(meaning)
        if is_meta_meaning(meaning):
            base *= 0.40
        score = min(0.97, base + 0.08 * cs + 0.12 * sim)
        ratio = min(len(nf), len(df)) / max(len(nf), len(df), 1)
        score *= 0.70 + 0.30 * ratio
        if best is None or score > best[2]:
            best = (meaning, donor, score, method)

    for stem in stems:
        if len(stem) < 3:
            continue
        # stem_key / loose paths need longer stems (Latin short-stem collisions)
        allow_stem_key = (not lemma_end_only) and len(stem) >= max(4, min_stem)
        if allow_stem_key and stem in lexicon:
            consider(stem, lexicon[stem], "rev_stem_key", 0.86)
        for end in ends:
            if not end:
                continue
            cand = stem + end
            if cand not in lexicon:
                continue
            # lemma reattach: allow shorter stems when whole-form similarity is strong
            # (aquarum↔aqua, manibus↔manus) — still gated by min_sim_lemma in consider()
            if len(stem) < min_stem and edit_sim(nf, fold_form(cand)) < max(0.55, min_sim_lemma):
                continue
            if len(stem) < 4 and edit_sim(nf, fold_form(cand)) < 0.55:
                continue
            consider(cand, lexicon[cand], "rev_lemma_end", 0.91)

    if not lemma_end_only and (best is None or best[2] < 0.88):
        for stem in stems[:2]:
            if len(stem) < max(5, min_stem):
                continue
            pref = stem[:4]
            keys = (prefix_index or {}).get(pref, [])[:40]
            for k in keys:
                kf = fold_form(k)
                if abs(len(kf) - len(nf)) > 4:
                    continue
                if kf.startswith(stem) or (len(kf) >= 5 and stem.startswith(kf[:5])):
                    consider(k, lexicon[k], "rev_prefix_family", 0.78)

    if best is None:
        return None
    meaning, donor, score, method = best
    if score < min_score:
        return None
    if is_meta_meaning(meaning) and score < 0.90:
        return None
    sim = edit_sim(nf, fold_form(donor))
    floor = min_sim_lemma if method == "rev_lemma_end" else 0.50
    if sim < floor:
        return None
    return meaning, donor, score, method


def build_prefix_index(lexicon: Dict[str, str]) -> Dict[str, List[str]]:
    """4-char fold prefix → keys (capped)."""
    idx: Dict[str, List[str]] = {}
    for k in lexicon:
        ff = fold_form(k)
        if len(ff) < 4:
            continue
        pref = ff[:4]
        bucket = idx.setdefault(pref, [])
        if len(bucket) < 100:
            bucket.append(k)
    return idx
