#!/usr/bin/env python3
"""
Protofluid converse refinements — capability + error-area hardening.

Addresses live-battery weaknesses:
  1) Modern English morph decoration (flowing_*) polluting science / chat Qs
  2) Domain misfires (water → oceanography over Latin historical)
  3) Soft fallback shells (narrative_flow) on junk / unknown tokens
  4) Duplicate archive facts in relay
  5) English function words needlessly gapfilled (latency + wrong sense)

FSOT law is never rewritten here — surface / routing / display only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# --- Shells that mean "we did not resolve" ---------------------------------
FALLBACK_SHELLS: Set[str] = {
    "narrative_flow",
    "heritage_flow",
    "generic_dynamics",
    "fluid_resonance",
    "life_process",
    "ecosystem_dynamics",
    "mineral_formation",
    "fossil_dynamics",
    "energy_process",
    "chemical_structure",
    "cosmic_flow",
    "quantum_state",
    "cosmic_event",
    "material_property",
    "record_flow",
    "primordial_signal",
    "consciousness_signal",
    "unresolved",
}

# Fluid S-prefix decoration from synthesize/modulate
_FLUID_PREFIXES = ("resonant_", "flowing_", "softened_", "stabilized_")

# Modern English function / closed-class (do not morph-decorate as content)
EN_STOP: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "am", "do", "does", "did", "have", "has", "had", "will", "would",
    "can", "could", "should", "may", "might", "must", "shall",
    "of", "in", "on", "at", "to", "for", "from", "by", "with", "as",
    "and", "or", "but", "not", "no", "nor", "if", "then", "than",
    "that", "this", "these", "those", "it", "its", "i", "you", "we",
    "they", "he", "she", "them", "me", "my", "your", "our", "their",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "about", "tell", "me", "again", "please", "also", "just", "only",
    "very", "really", "more", "most", "some", "any", "all", "each",
    "there", "here", "so", "too", "up", "out", "into", "over", "under",
    "remember", "earlier", "before", "previous", "prior",
    "exactly", "says", "said", "must", "claim", "claimed", "equals",
}

# Language / classical meta cues (beat earth-science water routing)
LANG_META: Set[str] = {
    "latin", "greek", "classical", "roman", "rome", "ancient",
    "old_english", "anglo", "sanskrit", "hebrew", "egyptian",
    "language", "languages", "word", "words", "translate", "translation",
    "gloss", "lexicon", "grammar", "morphology", "etymology",
    "lingua", "verbum", "λόγος",
}

# Linguistic-science cues → archive-first answers
SCIENCE_CUES: Set[str] = {
    "zipf", "entropy", "exponent", "shannon", "heaps", "phoneme",
    "phonology", "syntax", "syllable", "orthography", "saccade",
    "fixation", "type-token", "type_token", "bits", "lexicon",
    "information", "frequency", "rank",
}

# English content words that are already glosses — pass through, no gapfill
EN_CONTENT_PASS: Dict[str, str] = {
    "temple": "temple",
    "divine": "divine",
    "soul": "soul",
    "god": "god",
    "goddess": "goddess",
    "hero": "hero",
    "zeus": "zeus",
    "water": "water",
    "hand": "hand",
    "hands": "hands",
    "language": "language",
    "word": "word",
    "words": "words",
    "energy": "energy",
    "field": "field",
    "photon": "photon",
    "quantum": "quantum",
    "myth": "myth",
    "memory": "memory",
    "king": "king",
    "war": "war",
    "city": "city",
    "empire": "empire",
    "law": "law",
    "mind": "mind",
    "brain": "brain",
    "life": "life",
    "cell": "cell",
    "earth": "earth",
    "star": "star",
    "sky": "sky",
    "time": "time",
    "space": "space",
    "light": "light",
    "sound": "sound",
    "force": "force",
    "matter": "matter",
    "formula": "formula",
    "knowledge": "knowledge",
    "observer": "observer",
    "token": "token",
    "nonsense": "nonsense",
    # language names / science labels (must not gapfill invent)
    "latin": "latin",
    "greek": "greek",
    "english": "english",
    "roman": "roman",
    "classical": "classical",
    "zipf": "zipf",
    "entropy": "entropy",
    "exponent": "exponent",
    "shannon": "shannon",
    "letter": "letter",
    "heaps": "heaps",
    "phoneme": "phoneme",
    "syntax": "syntax",
    "syllable": "syllable",
    "frequency": "frequency",
    "rank": "rank",
    "information": "information",
}

# Known classical / heritage surface forms (lowercase)
CLASSICAL_HINTS: Set[str] = {
    "aqua", "manus", "lingua", "verbum", "rex", "urbs", "bellum", "lex",
    "deus", "dea", "templum", "animus", "anima", "vita", "terra", "mare",
    "logos", "theos", "anthropos", "anthrôpos", "psyche", "psychê",
    "polis", "nomos", "mythos", "chronos", "cosmos", "kosmos",
    "ud", "bi", "an", "ki",  # sumerian crumbs
}

_WORD_RE = re.compile(r"[a-zA-Z\u0370-\u03ff\u1f00-\u1fff]+", re.UNICODE)


def tokenize_words(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def strip_fluid_prefix(meaning: str) -> str:
    m = (meaning or "").split(" [S=")[0].strip()
    for p in _FLUID_PREFIXES:
        if m.startswith(p):
            return m[len(p) :]
    return m


def is_fallback_shell(meaning: str) -> bool:
    base = strip_fluid_prefix(meaning).lower().strip()
    return base in FALLBACK_SHELLS or base.startswith("unresolved")


def looks_junk_token(token: str) -> bool:
    """Heuristic unknown / adversarial form — should not invent glosses."""
    t = (token or "").lower().strip()
    if len(t) < 3:
        return False
    if t in EN_STOP or t in EN_CONTENT_PASS or t in CLASSICAL_HINTS:
        return False
    if t in SCIENCE_CUES:
        return False
    # triple repeated letter (zzzxq)
    if re.search(r"(.)\1{2,}", t):
        return True
    # no vowel (latin/greek still have vowels including y)
    if t.isascii() and not re.search(r"[aeiouy]", t) and len(t) >= 4:
        return True
    # nonsense-y digraph soup
    if re.match(r"^(zz|xx|qq|glaphur|asdf|qwer|zxcv)", t):
        return True
    # high unique-consonant density short junk
    if t.isascii() and len(t) >= 5:
        vowels = len(re.findall(r"[aeiouy]", t))
        if vowels <= 1 and len(set(t)) >= len(t) - 1:
            # e.g. zzzxq already caught; glaphur has vowels
            pass
    return False


def detect_input_mode(text: str) -> Dict[str, Any]:
    """
    Classify utterance for Protofluid product path.

    Modes:
      classical_surface — mostly heritage forms (aqua manus …)
      science_query     — Zipf / entropy / linguistic measures
      english_meta      — English talking *about* Latin/Greek/language
      modern_english    — general English chat / question
      mixed             — English + classical tokens
    """
    tokens = tokenize_words(text)
    n = max(len(tokens), 1)
    stop_n = sum(1 for t in tokens if t in EN_STOP)
    science_n = sum(1 for t in tokens if t in SCIENCE_CUES or any(s in t for s in SCIENCE_CUES))
    meta_n = sum(1 for t in tokens if t in LANG_META)
    classical = [t for t in tokens if t in CLASSICAL_HINTS]
    content_en = [t for t in tokens if t in EN_CONTENT_PASS]
    non_ascii = any(ord(c) > 127 for c in (text or ""))
    # Greek letters
    has_greek = bool(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", text or ""))

    en_ratio = stop_n / n
    content_tokens = [t for t in tokens if t not in EN_STOP]
    classical_ratio = len(classical) / max(len(content_tokens), 1)

    if science_n >= 1 and en_ratio >= 0.25:
        mode = "science_query"
    elif meta_n >= 1 and en_ratio >= 0.35:
        mode = "english_meta"
    elif classical and en_ratio >= 0.4:
        mode = "mixed"
    elif (classical_ratio >= 0.5 and len(content_tokens) <= 8) or has_greek or (
        classical and en_ratio < 0.35
    ):
        mode = "classical_surface"
    elif en_ratio >= 0.4 or (stop_n >= 2 and len(content_tokens) >= 1):
        mode = "modern_english"
    elif classical:
        mode = "classical_surface"
    else:
        mode = "mixed"

    return {
        "mode": mode,
        "tokens": tokens,
        "classical_forms": classical,
        "content_en": content_en,
        "science_hits": science_n,
        "lang_meta_hits": meta_n,
        "en_ratio": round(en_ratio, 3),
        "has_greek": has_greek,
        "non_ascii": non_ascii,
        "translate_surface": mode
        in {"classical_surface", "mixed"}  # full morph useful
        or bool(classical),
        "archive_first": mode in {"science_query", "english_meta"},
        "skip_fluid_prefix": mode
        in {"science_query", "english_meta", "modern_english", "mixed"},
        "light_gapfill": mode
        in {"science_query", "english_meta", "modern_english"},
    }


def preferred_domain(
    text: str,
    *,
    pathway_hint: Optional[str] = None,
    keyword_domain: Optional[str] = None,
    keyword_score: int = 0,
) -> Optional[str]:
    """
    Hard domain overrides from product findings.
    Returns domain key or None to keep prior choice.
    """
    blob = (text or "").lower()
    tokens = set(tokenize_words(text))

    # Science linguistics
    if any(t in SCIENCE_CUES for t in tokens) or any(
        s in blob for s in ("zipf", "letter entropy", "heaps law", "type-token")
    ):
        return "linguistic"

    # Explicit language names beat oceanography / chemistry water routing
    if re.search(r"\b(latin|latine|roman|rome)\b", blob):
        return "historical"
    if re.search(r"\b(greek|hellenic|hellenistic|ancient greek)\b", blob):
        return "mythological" if any(
            t in tokens for t in ("god", "zeus", "myth", "temple", "soul", "divine")
        ) else "linguistic"
    if re.search(r"\b(old english|anglo[- ]?saxon|anglo)\b", blob):
        return "historical"
    if re.search(r"\b(language|languages|translate|translation|word|words|lexicon)\b", blob):
        # only force linguistic if not pure classical form line
        if len(tokens) >= 3:
            return "linguistic"

    # Classical forms alone
    classical = tokens & CLASSICAL_HINTS
    if classical and not (tokens & SCIENCE_CUES):
        if classical & {"aqua", "manus", "rex", "urbs", "bellum", "lex", "templum"}:
            return "historical"
        if classical & {"logos", "theos", "anthropos", "mythos", "psyche"}:
            return "linguistic"
        return "historical"

    # Myth proper names
    if tokens & {"zeus", "hera", "apollo", "athena", "odin", "myth", "temple", "divine"}:
        if "temple" in tokens or "divine" in tokens or "zeus" in tokens:
            return "mythological"

    # Soft: do not let pathway oceanography win when hands/water + language cues
    if pathway_hint in {
        "oceanography",
        "chemistry",
        "fluid_dynamics",
        "biological",
        "meteorology",
    }:
        if tokens & LANG_META or tokens & {"hand", "hands", "manus", "aqua", "latin"}:
            return "historical"
        if tokens & SCIENCE_CUES:
            return "linguistic"

    # Prefer keyword domain when strong
    if keyword_domain and keyword_score >= 2:
        return keyword_domain
    return None


def clean_meanings(
    meanings: Sequence[str],
    tokens: Optional[Sequence[str]] = None,
    *,
    token_exact: Optional[Sequence[bool]] = None,
) -> List[str]:
    """Strip fluid prefixes; replace shells / junk with unresolved."""
    out: List[str] = []
    toks = list(tokens or [])
    exacts = list(token_exact or [])
    for i, m in enumerate(meanings or []):
        base = strip_fluid_prefix(m)
        tok = toks[i] if i < len(toks) else ""
        exact = exacts[i] if i < len(exacts) else None
        if looks_junk_token(tok):
            out.append("unresolved")
            continue
        if is_fallback_shell(base):
            # exact lexicon hit that is literally "quantum_state" etc. still shell-like
            if exact is False or exact is None:
                out.append("unresolved")
                continue
            # even "exact" shells from _infer are false exact — treat as unresolved
            if base in FALLBACK_SHELLS:
                out.append("unresolved")
                continue
        # reject form-echo garbage if available
        try:
            from meaning_clean import is_garbage_meaning, is_meta_meaning

            if is_garbage_meaning(base) or is_meta_meaning(base):
                out.append("unresolved")
                continue
        except Exception:
            pass
        out.append(base)
    return out


def gloss_line(meanings: Sequence[str], *, hide_stop: bool = False) -> str:
    parts_in = list(meanings or [])
    if hide_stop:
        parts_in = [m for m in parts_in if m not in EN_STOP]
    good = [m for m in parts_in if m and m != "unresolved"]
    bad = sum(1 for m in parts_in if m == "unresolved")
    if not parts_in:
        return "(no tokens)"
    if not good and bad:
        return f"(unresolved surface — {bad} unknown token(s))"
    body = ", ".join(parts_in)
    if bad:
        body += f"  [{bad} unresolved]"
    return body


def plain_relay(meanings: Sequence[str], *, hide_stop: bool = False) -> str:
    """Human-readable relay without flowing_* decoration."""
    items = list(meanings or [])
    if hide_stop:
        items = [m for m in items if m not in EN_STOP]
    good = [m.replace("_", " ") for m in items if m and m != "unresolved"]
    if not good:
        return "(no confident gloss)"
    return " · ".join(good)


def dedup_knowledge(items: Sequence[Dict[str, Any]], *, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Drop duplicate archive/session rows (kb portable mirrors, identical claims).
    """
    seen_ids: Set[str] = set()
    seen_text: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for c in items:
        cid = str(c.get("id") or "")
        # normalize portable summary mirrors
        if cid.startswith("kb:portable_summary"):
            cid_key = "kb:portable_summary"
        else:
            cid_key = cid
        ct = re.sub(r"\s+", " ", (c.get("claim_text") or "")[:200]).strip().lower()
        title = (c.get("title") or "").lower()
        text_key = ct or title
        if cid_key and cid_key in seen_ids:
            continue
        if text_key and text_key in seen_text:
            continue
        if cid_key:
            seen_ids.add(cid_key)
        if text_key:
            seen_text.add(text_key)
        out.append(c)
        if len(out) >= limit:
            break
    return out


def science_answer_lines(archive_facts: Sequence[Dict[str, Any]]) -> List[str]:
    """Lead with archive linguistics facts for science_query mode."""
    lines: List[str] = []
    for c in archive_facts:
        src = c.get("source") or "archive"
        if src not in {"linguistics_derivations", "linguistic_targets", "kb_portable", "formula_corpus"}:
            continue
        ct = (c.get("claim_text") or "")[:200]
        if not ct:
            continue
        lines.append(f"  · [{src}] {ct}")
        if len(lines) >= 5:
            break
    return lines


def english_pass_meaning(token: str) -> Optional[str]:
    """If token is known English content, return identity gloss (skip gapfill)."""
    t = (token or "").lower()
    if t in EN_CONTENT_PASS:
        return EN_CONTENT_PASS[t]
    if t in EN_STOP:
        return None  # skip stopwords entirely
    if t in SCIENCE_CUES:
        return t  # keep as cue label, not morph invent
    return None
