#!/usr/bin/env python3
"""
Class-based Latin / Greek inflection tables (WORDS / Collatinus style).

Goal: map open surface forms to lemmas more accurately than greedy
suffix strip (e.g. prefer 4th-decl *manu-* analysis over bare *man-*).

FSOT-safe: finite tables only; meanings only from train lexicon.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from gapfill_student import edit_sim
from meaning_clean import content_score, fold_form, is_meta_meaning

# (ending, stem_extra_chars_before_ending)
# stem_extra: characters that belong to the stem and sit before the ending
# e.g. manibus = stem "manu" + ending "ibus" with stem_extra "" and stem "manu"
# We encode as: form = stem + ending, stem = form[:-len(ending)] with optional
# preferred stem_min_len.

# Latin 4th declension (manus, fructus, …): stem ends in -u-
_LA_4TH = (
    "ibus", "uum", "ui", "um", "us", "u", "ūs", "ū",
)

# Latin 1st: -a stems
_LA_1ST = ("arum", "is", "as", "am", "ae", "a")

# Latin 2nd: -us/-um
_LA_2ND = ("orum", "ibus", "is", "os", "um", "us", "o", "i", "e")

# Latin 3rd mixed (conservative longer endings first)
_LA_3RD = (
    "ibus", "ium", "ibus", "es", "em", "is", "i", "e", "a",
)

# Latin 5th: -es
_LA_5TH = ("erum", "ebus", "ei", "em", "es", "e")


def _la_stem_candidates(form: str) -> List[str]:
    """
    Produce preferred stems ordered by declension-class heuristics.
    4th-decl: if ends with ibus/uum and char before ending region suggests -u-
    reconstruct *manu* from manibus by stem = form[:-4] + 'u' when form ends ibus
    and len>=6.
    """
    w = fold_form(form)
    if len(w) < 3:
        return [w] if w else []
    out: List[str] = []

    # --- 4th declension special ---
    # manibus ← manu + ibus  (classical analysis)
    if w.endswith("ibus") and len(w) >= 6:
        # reconstruct -u- stem: drop ibus, ensure terminal u
        base = w[: -len("ibus")]
        if base and not base.endswith("u"):
            out.append(base + "u")  # man + u = manu
        out.append(base)
    if w.endswith("uum") and len(w) >= 5:
        base = w[: -len("uum")]
        if base and not base.endswith("u"):
            out.append(base + "u")
        out.append(base)
    if w.endswith("ui") and len(w) >= 4:
        out.append(w[:-2])  # manui → manu
    if w.endswith("um") and len(w) >= 4 and not w.endswith("uum"):
        # manum → manu (4th) or manum → man (2nd) — prefer manu if *u* before m
        base = w[:-2]
        if base.endswith("u"):
            out.append(base)
        out.append(base)

    # generic ending peels (ordered)
    for ending in (
        "ationibus", "ionibus", "tionibus", "tatibus", "oribus",
        "arum", "orum", "ibus", "uum", "ium",
        "arum", "orum",
        "em", "um", "am", "as", "os", "es", "is", "us", "ae", "ui",
        "a", "o", "i", "e", "u",
    ):
        if w.endswith(ending) and len(w) - len(ending) >= 3:
            st = w[: -len(ending)]
            if st not in out:
                out.append(st)

    if w not in out:
        out.insert(0, w)
    # unique preserve
    seen = set()
    uniq = []
    for s in out:
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _grc_stem_candidates(form: str) -> List[str]:
    w = fold_form(form)
    if len(w) < 2:
        return [w] if w else []
    out = [w]
    for ending in (
        "οισιν", "αισιν", "εσσιν", "εων", "εως", "εσιν",
        "οις", "αις", "ους", "ων", "ον", "ος", "ης", "ην", "ας", "αι",
        "ου", "εις", "ιν", "ιος", "ιον", "ια",
        "ευς", "εως", "εα",
        "η", "α", "ι", "ν", "ε", "ο",
    ):
        if w.endswith(ending) and len(w) - len(ending) >= 2:
            st = w[: -len(ending)]
            if st not in out:
                out.append(st)
    return out


def class_stem_candidates(form: str, lang: str = "la") -> List[str]:
    lang = (lang or "la").lower()
    if lang in {"grc", "el"}:
        return _grc_stem_candidates(form)
    if lang in {"ang", "oe"}:
        w = fold_form(form)
        return [w]
    return _la_stem_candidates(form)


def declension_resolve(
    form: str,
    lexicon: Dict[str, str],
    lang: str = "la",
    *,
    context: str = "historical",
) -> Optional[Tuple[str, str, float, str]]:
    """
    Probe lexicon with class-aware stems + lemma reattach.
    Returns (meaning, donor, score, method).
    """
    if not form or not lexicon:
        return None
    nf = fold_form(form)
    stems = class_stem_candidates(form, lang)
    ends = (
        ("ος", "η", "α", "ον", "ις", "ευς", "ης", "ω", "")
        if lang in {"grc", "el"}
        else ("us", "um", "a", "is", "es", "or", "io", "u", "are", "ere", "ire", "o", "")
    )

    best: Optional[Tuple[str, str, float, str]] = None

    def consider(donor: str, meaning: str, method: str, base: float, stem_len: int = 3) -> None:
        nonlocal best
        if not meaning:
            return
        if is_meta_meaning(meaning):
            base *= 0.35
        df = fold_form(donor)
        sim = edit_sim(nf, df)
        # require real kinship to the surface form (blocks manibus→mane)
        if sim < 0.48:
            return
        if abs(len(nf) - len(df)) > 4 and sim < 0.62:
            return
        # domain soft boost
        ctx = (context or "").lower()
        mlow = meaning.lower()
        if ctx in {"mythological", "religious"} and any(
            x in mlow for x in ("god", "spirit", "underworld", "hades", "myth", "divine")
        ):
            base += 0.05
        if ctx in {"historical", "linguistic", "english", "administrative"} and any(
            x in mlow for x in ("hand", "water", "law", "king", "city", "war", "people")
        ):
            base += 0.05
        # longer stem analysis preferred (manu- > man-)
        base += 0.03 * min(3, max(0, stem_len - 3))
        score = min(0.96, base + 0.10 * content_score(meaning) + 0.18 * sim)
        if best is None or score > best[2]:
            best = (meaning, donor, score, method)

    for stem in stems:
        if len(stem) < 3:
            continue
        if stem in lexicon:
            consider(stem, lexicon[stem], "decl_stem", 0.84, stem_len=len(stem))
        for end in ends:
            if not end:
                continue
            cand = stem + end
            if cand in lexicon:
                consider(cand, lexicon[cand], "decl_lemma", 0.88, stem_len=len(stem))

    if best is None or best[2] < 0.82:
        return None
    return best
