#!/usr/bin/env python3
"""
Whitaker / Morpheus-style prefix peeling for classical forms.

OSS inspiration: Whitaker's WORDS analyzes Latin as
  (prefix*) + stem + (inflection)
then maps the stem/lemma to a dictionary gloss — not free generation.

FSOT-safe: finite prefix tables only; meanings come from existing lexicon donors.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from meaning_clean import content_score, fold_form, is_meta_meaning

# Longer first. Latin productive verbal/nominal prefixes.
_LA_PREFIXES: Sequence[str] = (
    "praeter", "trans", "super", "supra", "inter", "intro", "infra", "ultra",
    "circum", "contra", "retro", "quasi",
    "prae", "post", "ante", "semi", "bene", "male",
    "con", "com", "col", "cor", "co",
    "in", "im", "il", "ir",  # in- / im- before labials
    "ad", "ac", "af", "ag", "al", "an", "ap", "ar", "as", "at",
    "ob", "oc", "of", "op",
    "sub", "suc", "suf", "sug", "sup", "sur", "sus",
    "ex", "ef", "e",
    "dis", "dif", "di",
    "re", "red",
    "se", "sed",
    "ab", "abs", "a",
    "de", "per", "pro", "pre",
)

# Greek (folded) productive prefixes — monotonic-ish after fold
_GRC_PREFIXES: Sequence[str] = (
    "κατα", "κατα", "παρα", "περι", "μετα", "προσ", "αντι", "υπερ", "υπο",
    "εκ", "εξ", "εν", "εμ", "συν", "συμ", "συγ", "συλ",
    "απο", "επι", "δια", "ανα", "αμφι", "προ", "παρα",
    "α", "αν",  # alpha privative (careful — short)
)

_ANG_PREFIXES: Sequence[str] = (
    "ofer", "under", "fore", "after", "mis", "un", "ge", "be", "a", "to", "for",
)


def _prefixes(lang: str) -> Sequence[str]:
    lang = (lang or "la").lower()
    if lang in {"grc", "el"}:
        return _GRC_PREFIXES
    if lang in {"ang", "oe"}:
        return _ANG_PREFIXES
    return _LA_PREFIXES


def peel_prefixes(form: str, lang: str = "la", max_peels: int = 2) -> List[str]:
    """
    Return residual stems after peeling 0..max_peels known prefixes.
    Always includes the original folded form first.
    """
    w = fold_form(form)
    if not w:
        return []
    out = [w]
    cur = w
    prefs = sorted(set(_prefixes(lang)), key=len, reverse=True)
    for _ in range(max_peels):
        peeled = False
        for p in prefs:
            pf = fold_form(p)
            if not pf or len(pf) < 1:
                continue
            # avoid stripping too much (leave ≥3 chars stem)
            if cur.startswith(pf) and len(cur) - len(pf) >= 3:
                # block ultra-short Greek alpha unless remainder long
                if pf in {"a", "e", "an"} and len(cur) - len(pf) < 4:
                    continue
                cur = cur[len(pf) :]
                if cur not in out:
                    out.append(cur)
                peeled = True
                break
        if not peeled:
            break
    return out


def prefix_resolve(
    form: str,
    lexicon: Dict[str, str],
    lang: str = "la",
    *,
    lemma_ends: Optional[Sequence[str]] = None,
) -> Optional[Tuple[str, str, float, str]]:
    """
    Peel prefixes, then probe lexicon for residual stem / stem+lemma ending.
    Returns (meaning, donor, score, method) or None.
    """
    if not form or not lexicon:
        return None
    if lemma_ends is None:
        if lang in {"grc", "el"}:
            lemma_ends = ("ος", "η", "α", "ον", "ις", "ευς", "ης", "ω", "ειν", "")
        elif lang in {"ang", "oe"}:
            lemma_ends = ("an", "ian", "a", "e", "u", "")
        else:
            lemma_ends = (
                "are", "ere", "ire", "us", "um", "a", "is", "es", "or", "io", "o", ""
            )

    best: Optional[Tuple[str, str, float, str]] = None
    residuals = peel_prefixes(form, lang)

    def consider(donor: str, meaning: str, method: str, base: float) -> None:
        nonlocal best
        if not meaning or is_meta_meaning(meaning):
            return
        cs = content_score(meaning)
        score = min(0.93, base + 0.1 * cs)
        # length ratio residual↔donor
        df = fold_form(donor)
        if not df:
            return
        # prefer concrete short glosses
        if len(meaning) > 40:
            score *= 0.85
        if best is None or score > best[2]:
            best = (meaning, donor, score, method)

    for i, res in enumerate(residuals):
        if i == 0:
            continue  # skip unpeeled — reverse_morph / exact handle that
        if res in lexicon:
            consider(res, lexicon[res], f"prefix_stem_n{i}", 0.86)
        for end in lemma_ends:
            if not end:
                if res in lexicon:
                    consider(res, lexicon[res], f"prefix_bare_n{i}", 0.84)
                continue
            cand = res + end
            if cand in lexicon:
                consider(cand, lexicon[cand], f"prefix_lemma_n{i}", 0.88)

    if best is None or best[2] < 0.82:
        return None
    return best
