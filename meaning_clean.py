#!/usr/bin/env python3
"""
Clean dictionary-style meaning keys for open-set transfer.

~30% of classical gold is grammatical meta ("dative_singular_of_X") or
alt-form pointers. Transferring those as donor meanings poisons gap-fill.
This module peels meta wrappers and prefers content glosses.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Set

# Meta / inflectional wrapper prefixes (underscored meaning_keys)
_META_HEAD = re.compile(
    r"^(?:"
    r"nominative|genitive|dative|accusative|ablative|vocative|locative|"
    r"singular|plural|dual|"
    r"masculine|feminine|neuter|"
    r"present|perfect|imperfect|future|pluperfect|aorist|"
    r"active|passive|middle|deponent|"
    r"indicative|subjunctive|optative|imperative|infinitive|participle|"
    r"first|second|third|person|"
    r"comparative|superlative|"
    r"alternative_form|misspelling|archaic_form|obsolete_form|"
    r"initialism|abbreviation|acronym|synonym|"
    r"diminutive|augmentative|"
    r"present_active|perfect_passive|future_active|future_passive|"
    r"supine|gerund|gerundive"
    r")(?:_|$)",
    re.I,
)

_OF_TAIL = re.compile(
    r"(?:^|_)(?:(?:nominative|genitive|dative|accusative|ablative|vocative|"
    r"singular|plural|masculine|feminine|neuter|active|passive|middle|"
    r"present|perfect|future|aorist|infinitive|participle|form|alternative|"
    r"misspelling|archaic|obsolete|initialism|abbreviation|synonym|"
    r"comparative|superlative|first|second|third|person|indicative|"
    r"subjunctive|imperative|optative|deponent)_){0,12}"
    r"(?:form_of|of)_(.+)$",
    re.I,
)

_CONTENT_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "onto",
    "upon", "a", "an", "of", "to", "in", "on", "or", "by", "as", "at",
}


def fold_form(s: str) -> str:
    """Lowercase + strip combining diacritics (Latin macrons, Greek accents)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.strip().lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Greek tonos / dialytika leftovers as spacing marks already stripped
    s = re.sub(r"\s+", "", s)
    return s


def is_meta_meaning(mk: str) -> bool:
    if not mk:
        return True
    m = mk.lower().strip("_")
    if _META_HEAD.match(m):
        return True
    if "form_of_" in m or m.startswith("initialism_of"):
        return True
    if m.startswith("inflection_of_") or m.startswith("name_of_"):
        return True
    # long chain of case/number words
    bits = m.split("_")
    meta_bits = {
        "nominative", "genitive", "dative", "accusative", "ablative", "vocative",
        "singular", "plural", "masculine", "feminine", "neuter", "of", "form",
        "active", "passive", "present", "perfect", "infinitive", "participle",
        "first", "second", "third", "person", "indicative", "subjunctive",
        "optative", "imperative", "middle", "deponent", "inflection",
        "spelling", "obsolete", "clipping", "alternative",
    }
    if len(bits) >= 3 and sum(1 for b in bits if b in meta_bits) >= 2:
        return True
    # mangled case shells: go_te_genitive, x_r_s_dative (not ordinary "X_of_Y")
    caseish = {
        "nominative", "genitive", "dative", "accusative", "ablative", "vocative",
        "singular", "plural", "masculine", "feminine", "neuter",
        "participle", "infinitive", "indicative", "subjunctive", "optative",
        "spelling", "obsolete", "clipping",
    }
    if any(b in caseish or b.endswith("genitive") or b.endswith("dative") for b in bits):
        # only treat as meta when there is little real content left
        content_bits = [b for b in bits if b not in caseish and len(b) >= 3]
        if len(content_bits) <= 1:
            return True
    return False


def is_garbage_meaning(mk: str) -> bool:
    """
    Detect non-transferable glosses that poison open-set:
    mangled transliterations (dek_mbrios), ultra-long wiki dumps, empty shells.
    """
    if not mk:
        return True
    m = mk.lower().strip("_")
    if is_meta_meaning(m):
        return True
    if len(m) > 90 or m.count("_") > 14:
        return True
    # pure form-echo: mostly consonants (a_t_os) — not English thirst/stench/crypt
    letters = re.findall(r"[a-z]", m)
    if len(letters) >= 8:
        vowels = sum(1 for c in letters if c in "aeiouy")
        if vowels / len(letters) < 0.15:
            return True
    # single-letter underscore soup: a_t_os, x_r_s, pol_t_k_s
    bits = [b for b in m.split("_") if b]
    if len(bits) >= 2 and sum(1 for b in bits if len(b) <= 1) >= max(2, len(bits) // 2):
        return True
    # underscore shells with no long content chunk (a_t_os style)
    if "_" in m:
        long_bits = [b for b in bits if len(b) >= 4]
        if not long_bits:
            return True
        # single-letter-heavy soup: a_t_os, pol_t_k_s
        if sum(1 for b in bits if len(b) <= 1) >= 2:
            return True
    # form-echo lemma shells: glaphur_s (letter tail after _)
    if re.search(r"_[a-z]$", m) and len(m) <= 16:
        return True
    if re.fullmatch(r"[a-z]{3,12}_[a-z]{1,2}", m):
        return True
    if m in {
        "narrative_flow",
        "heritage_flow",
        "generic_dynamics",
        "fluid_resonance",
        "primordial_signal",
        "unknown",
        "inflection",
        "inflections",
        "grammar",
        "grammatical",
    }:
        return True
    # bare grammatical residue
    if m in {"form", "word", "lemma", "stem", "root", "ending", "suffix", "prefix"}:
        return True
    # Dictionary meta Ada product path rejects (parity with pflt_gloss_quality)
    if re.search(
        r"(dative|genitive|accusative|nominative|vocative|ablative|"
        r"singular of|plural of|participle of|imperative of|"
        r"the compound|compound of|with genitive|with dative)",
        m,
    ):
        return True
    return False


def peel_of_referent(mk: str) -> Optional[str]:
    """Extract lemma/referent after ..._of_X."""
    if not mk:
        return None
    m = mk.lower().strip()
    # Prefer last of_ chunk
    if "_of_" in m:
        tail = m.rsplit("_of_", 1)[-1].strip("_")
        # strip residual grammatical junk tokens from tail
        parts = [p for p in tail.split("_") if p and p not in {
            "the", "a", "an", "masculine", "feminine", "neuter",
            "singular", "plural", "active", "passive",
        }]
        if parts:
            return "_".join(parts)
    hit = _OF_TAIL.search(m)
    if hit:
        return hit.group(1).strip("_")
    return None


def content_score(mk: str) -> float:
    """Higher = better donor meaning for open-set transfer."""
    if not mk:
        return 0.0
    if is_garbage_meaning(mk):
        return 0.05
    if is_meta_meaning(mk):
        return 0.12
    tokens = [t for t in re.findall(r"[a-z]{3,}", mk.lower()) if t not in _CONTENT_STOP]
    if not tokens:
        return 0.2
    # short concrete glosses win
    length_pen = min(1.0, 12.0 / max(4, len(mk)))
    score = min(1.0, 0.4 + 0.1 * len(tokens) + 0.3 * length_pen)
    # penalize long multi-clause wiki dumps even if not hard-garbage
    if len(mk) > 50:
        score *= 0.7
    return score


def best_transfer_meaning(
    meaning_key: str,
    target_word: str = "",
    form_to_meaning: Optional[Dict[str, str]] = None,
) -> str:
    """
    Choose the best open-set transfer gloss for a gold row.
    Prefer content meaning_key; peel meta; fall back to English target_word clause.
    """
    mk = (meaning_key or "").strip()
    tw = (target_word or "").strip()

    def _ok(s: str) -> bool:
        return bool(s) and not is_garbage_meaning(s) and content_score(s) >= 0.30

    if _ok(mk) and not is_meta_meaning(mk):
        return mk

    if mk and form_to_meaning is not None:
        cleaned = resolve_meaning(mk, form_to_meaning)
        if _ok(cleaned) and not is_meta_meaning(cleaned):
            return cleaned

    ref = peel_of_referent(mk) if mk else None
    if ref and _ok(ref) and not is_meta_meaning(ref):
        return ref

    if tw:
        # first clause before ; , ( — classic dict multi-sense
        clause = re.split(r"[;,(/]| - ", tw)[0].strip()
        clause = re.sub(r"^(a|an|the)\s+", "", clause, flags=re.I).strip()
        # keep short content phrase
        words = re.findall(r"[A-Za-z]+", clause)
        words = [w for w in words if w.lower() not in _CONTENT_STOP]
        if words:
            alt = "_".join(w.lower() for w in words[:6])
            if _ok(alt):
                return alt

    # last resort: original if not garbage, else empty marker
    if mk and not is_garbage_meaning(mk) and not is_meta_meaning(mk):
        return mk
    return ""


def resolve_meaning(
    mk: str,
    form_to_meaning: Dict[str, str],
    *,
    depth: int = 0,
    seen: Optional[Set[str]] = None,
) -> str:
    """
    Peel grammatical wrappers; if referent is a known form, use its gloss.
    Falls back to original mk.
    """
    if not mk:
        return mk
    if seen is None:
        seen = set()
    if mk in seen or depth > 4:
        return mk
    seen.add(mk)

    if not is_meta_meaning(mk):
        return mk

    ref = peel_of_referent(mk)
    if not ref:
        return mk

    # try form lookup variants
    candidates = [
        ref,
        ref.replace("_", " "),
        ref.replace("_", ""),
        fold_form(ref),
    ]
    for c in candidates:
        if c in form_to_meaning:
            inner = form_to_meaning[c]
            if inner and inner != mk:
                return resolve_meaning(inner, form_to_meaning, depth=depth + 1, seen=seen)
    # no form hit — if peel produced a short english-ish gloss, use it
    if ref and len(ref) <= 40 and not is_meta_meaning(ref):
        return ref
    return mk


def build_cleaned_lexicon(raw: Dict[str, str]) -> Dict[str, str]:
    """Return form→cleaned meaning; prefer higher content_score on collision."""
    out: Dict[str, str] = {}
    # Fast path for huge lexica: only peel obvious meta, skip deep resolve
    huge = len(raw) > 40000
    for form, mk in raw.items():
        if huge:
            if is_meta_meaning(mk):
                ref = peel_of_referent(mk)
                cleaned = ref if ref and not is_meta_meaning(ref) else mk
            else:
                cleaned = mk
        else:
            cleaned = resolve_meaning(mk, raw)
        prev = out.get(form)
        if prev is None or content_score(cleaned) > content_score(prev):
            out[form] = cleaned
        ff = fold_form(form)
        if ff and ff != form:
            prev2 = out.get(ff)
            if prev2 is None or content_score(cleaned) > content_score(prev2):
                out[ff] = cleaned
    return out
