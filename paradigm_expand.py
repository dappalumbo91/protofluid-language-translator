#!/usr/bin/env python3
"""
FSOT-friendly paradigm expander: from known lemma→meaning pairs, generate
common Latin/Greek/OE inflectional variants sharing the same meaning.

This converts many open-set inflected forms into closed-set hits without
LLM free generation — pure finite morphology tables.
"""
from __future__ import annotations

import unicodedata
from typing import Dict, Iterable, List, Set, Tuple


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# (stem_suffix_to_strip, endings_to_add)
_LA_NOUN = [
    # 4th declension (manus): stem in -u-
    ("us", ["us", "um", "ui", "u", "uum", "ibus", "us", "um"]),
    ("um", ["um", "i", "o", "a", "orum", "is", "orum", "a"]),
    ("a", ["a", "am", "ae", "arum", "is", "as", "a", "ā"]),
    ("is", ["is", "em", "i", "e", "es", "ium", "ibus", "im", "e"]),
    ("es", ["es", "em", "is", "ei", "erum", "ebus", "e"]),
    ("or", ["or", "oris", "orem", "ore", "ores", "orum", "oribus"]),
    ("io", ["io", "ionis", "ionem", "ione", "iones", "ionum", "ionibus"]),
    ("tas", ["tas", "tatis", "tatem", "tate", "tates", "tatum", "tatibus"]),
    ("tio", ["tio", "tionis", "tionem", "tione", "tiones", "tionum", "tionibus"]),
    ("tudo", ["tudo", "tudinis", "tudinem", "tudine", "tudines", "tudinum"]),
    ("men", ["men", "minis", "men", "mine", "mina", "minum", "minibus"]),
    ("x", ["x", "cis", "cem", "ce", "ces", "cum", "cibus", "gis", "gem", "ges"]),
    ("ns", ["ns", "ntis", "ntem", "nte", "ntes", "ntium", "ntibus"]),
    ("er", ["er", "ri", "ro", "rum", "ris", "rem", "re"]),
]

_LA_ADJ = [
    ("us", ["us", "a", "um", "i", "ae", "o", "am", "os", "as", "orum", "arum", "is"]),
    ("is", ["is", "e", "em", "i", "ia", "ium", "ibus", "es"]),
    ("er", ["er", "era", "erum", "eri", "erae", "ero", "eram", "eros", "eras"]),
]

_LA_VERB = [
    ("are", ["are", "o", "as", "at", "amus", "atis", "ant", "avi", "atum", "ans", "abo", "abis", "abit"]),
    ("ere", ["ere", "eo", "es", "et", "emus", "etis", "ent", "ui", "itum", "ens"]),
    ("ere", ["ere", "o", "is", "it", "imus", "itis", "unt", "i", "tum"]),  # 3rd conj rough
    ("ire", ["ire", "io", "is", "it", "imus", "itis", "iunt", "ivi", "itum", "iens"]),
    ("o", ["o", "is", "it", "imus", "itis", "unt", "ere", "i"]),  # from 1sg present
]

_GRC = [
    ("ος", ["ος", "ου", "ον", "ε", "οι", "ους", "ων", "οις", "οιο", "οισι"]),
    ("η", ["η", "ης", "ην", "ῃ", "αι", "ας", "ων", "αις", "ηι"]),
    ("α", ["α", "ας", "αν", "ᾳ", "αι", "ας", "ων", "αις", "ης"]),
    ("ον", ["ον", "ου", "ῳ", "α", "ων", "οις", "ου"]),
    ("ις", ["ις", "εως", "ιν", "ι", "εις", "εων", "εσι", "εσιν"]),
    ("ευς", ["ευς", "εως", "εα", "ευ", "εις", "εων", "ευσι", "εας"]),
    ("ης", ["ης", "ου", "ην", "η", "αι", "ας", "ων", "ου"]),
    ("ων", ["ων", "οντος", "οντα", "οντι", "οντες", "οντων", "ουσα", "ον"]),
    ("μα", ["μα", "ματος", "ματι", "ματα", "ματων", "μασι"]),
    ("σις", ["σις", "σεως", "σιν", "σεις", "σεων"]),
    ("ικος", ["ικος", "ικη", "ικον", "ικου", "ικης", "ικοι", "ικαι", "ικα"]),
    ("ιος", ["ιος", "ια", "ιον", "ιου", "ιας", "ιοι", "ιαι"]),
]

_ANG = [
    ("an", ["an", "e", "as", "um", "a", "ena", "enne", "ode", "odon"]),
    ("ian", ["ian", "ie", "iaþ", "iað", "iende"]),
    ("a", ["a", "an", "as", "um", "ena"]),
    ("e", ["e", "es", "a", "um", "ena"]),
    ("ung", ["ung", "unge", "unga", "unga"]),
]


def _apply_table(word: str, table: List[Tuple[str, List[str]]], max_out: int = 14) -> List[str]:
    w = word
    wf = _fold(word)
    out: List[str] = []
    for suf, endings in table:
        sf = _fold(suf)
        if wf.endswith(sf) and len(wf) - len(sf) >= 3:
            if w.lower().endswith(suf):
                stem = w[: len(w) - len(suf)]
            elif len(w) >= len(sf):
                stem = w[: len(w) - len(sf)]
            else:
                stem = w[: len(wf) - len(sf)]
            for end in endings:
                cand = stem + end
                if cand != w:
                    out.append(cand)
            break
    seen: Set[str] = set()
    uniq = []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
        if len(uniq) >= max_out:
            break
    return uniq


def expand_form(word: str, lang: str) -> List[str]:
    lang = (lang or "").lower()
    if lang in {"la", "lat"}:
        return (
            _apply_table(word, _LA_NOUN)
            + _apply_table(word, _LA_ADJ)
            + _apply_table(word, _LA_VERB)
        )
    if lang in {"grc", "el"}:
        return _apply_table(word, _GRC)
    if lang in {"ang", "oe"}:
        return _apply_table(word, _ANG)
    return []


def expand_lexicon(
    rows: Iterable[dict],
    *,
    max_per_form: int = 10,
    only_content: bool = True,
) -> Dict[str, str]:
    """
    rows: dicts with source_lang, source_word, meaning_key
    returns extra form→meaning (does not include originals)
    """
    from meaning_clean import is_meta_meaning

    extra: Dict[str, str] = {}
    for r in rows:
        w = (r.get("source_word") or "").strip()
        m = r.get("meaning_key") or ""
        lang = (r.get("source_lang") or "").lower()
        if not w or not m:
            continue
        if only_content and is_meta_meaning(m):
            continue
        if len(m) > 48:
            continue
        for cand in expand_form(w, lang)[:max_per_form]:
            if cand not in extra:
                extra[cand] = m
            ff = _fold(cand)
            if ff and ff not in extra:
                extra[ff] = m
    return extra
