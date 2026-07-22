#!/usr/bin/env python3
"""
English-meta teaching panel for the Protofluid Language Translator.

When the user asks *in English* about Latin/Greek (e.g. "water and hands in Latin"),
prefer a classical form↔gloss teaching panel over unrelated KB formulas (pH_water).

Finite reverse tables + optional PFLT lexicon reverse probe. No LLM.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# English gloss → classical surface forms (teaching direction)
# Keep small, high-precision; product quality > coverage vanity.
_LA_TEACH: Dict[str, List[str]] = {
    "water": ["aqua"],
    "hand": ["manus"],
    "hands": ["manus", "manibus"],
    "language": ["lingua"],
    "tongue": ["lingua"],
    "word": ["verbum", "vox"],
    "words": ["verba"],
    "law": ["lex", "ius"],
    "king": ["rex"],
    "city": ["urbs", "civitas"],
    "war": ["bellum"],
    "god": ["deus"],
    "goddess": ["dea"],
    "soul": ["anima", "animus"],
    "life": ["vita"],
    "earth": ["terra"],
    "sea": ["mare"],
    "fire": ["ignis"],
    "light": ["lux", "lumen"],
    "man": ["homo", "vir"],
    "woman": ["femina", "mulier"],
    "love": ["amor"],
    "peace": ["pax"],
    "power": ["potestas", "imperium"],
    "name": ["nomen"],
    "time": ["tempus"],
    "temple": ["templum", "aedes"],
    "house": ["domus"],
    "road": ["via"],
    "day": ["dies"],
    "night": ["nox"],
    "year": ["annus"],
    "people": ["populus", "gens"],
    "blood": ["sanguis"],
    "mind": ["mens", "animus"],
    "voice": ["vox"],
    "book": ["liber"],
    "letter": ["littera"],
    "force": ["vis"],
    "master": ["dominus", "magister"],
}

_GRC_TEACH: Dict[str, List[str]] = {
    "word": ["logos", "λόγος"],
    "god": ["theos", "θεός"],
    "man": ["anthropos", "ἄνθρωπος"],
    "human": ["anthropos", "ἄνθρωπος"],
    "humanity": ["anthropos"],
    "soul": ["psyche", "ψυχή"],
    "city": ["polis", "πόλις"],
    "law": ["nomos", "νόμος"],
    "myth": ["mythos", "μῦθος"],
    "time": ["chronos", "χρόνος"],
    "cosmos": ["kosmos", "κόσμος"],
    "universe": ["kosmos"],
    "love": ["eros", "agape", "ἔρως"],
    "wisdom": ["sophia", "σοφία"],
    "truth": ["aletheia", "ἀλήθεια"],
    "temple": ["naos", "ναός"],
    "water": ["hydor", "ὕδωρ"],
    "sea": ["thalassa", "θάλασσα"],
    "earth": ["ge", "γῆ"],
    "fire": ["pyr", "πῦρ"],
    "light": ["phos", "φῶς"],
    "life": ["zoe", "bios", "ζωή"],
    "death": ["thanatos", "θάνατος"],
    "king": ["basileus", "βασιλεύς"],
    "war": ["polemos", "πόλεμος"],
    "peace": ["eirene", "εἰρήνη"],
    "mind": ["nous", "νοῦς"],
    "voice": ["phone", "φωνή"],
    "name": ["onoma", "ὄνομα"],
    "hand": ["cheir", "χείρ"],
    "language": ["glossa", "γλῶσσα"],
}

_ANG_TEACH: Dict[str, List[str]] = {
    "water": ["wæter"],
    "hand": ["hand"],
    "king": ["cyning"],
    "god": ["god"],
    "man": ["mann"],
    "earth": ["eorþe"],
    "day": ["dæg"],
    "night": ["niht"],
    "love": ["lufu"],
    "word": ["word"],
    "life": ["lif"],
    "war": ["wig", "guþ"],
    "peace": ["friþ"],
    "temple": ["ealh", "tempel"],
}

_LANG_ALIAS = {
    "latin": "la",
    "la": "la",
    "lat": "la",
    "roman": "la",
    "rome": "la",
    "greek": "grc",
    "grc": "grc",
    "el": "grc",
    "hellenic": "grc",
    "old english": "ang",
    "old_english": "ang",
    "anglo-saxon": "ang",
    "anglo": "ang",
    "ang": "ang",
    "oe": "ang",
}


def detect_teach_lang(text: str) -> Optional[str]:
    blob = (text or "").lower()
    for cue, code in _LANG_ALIAS.items():
        if re.search(rf"\b{re.escape(cue)}\b", blob):
            return code
    return None


def _table_for(lang: str) -> Dict[str, List[str]]:
    if lang == "la":
        return _LA_TEACH
    if lang == "grc":
        return _GRC_TEACH
    if lang == "ang":
        return _ANG_TEACH
    return {}


def _content_glosses(tokens: Sequence[str], meanings: Sequence[str]) -> List[str]:
    """Collect English content words that might reverse-map to classical forms."""
    stop = {
        "a", "an", "the", "is", "are", "was", "were", "be", "of", "in", "on", "at",
        "to", "for", "from", "by", "with", "and", "or", "but", "not", "about",
        "tell", "me", "what", "which", "who", "how", "why", "when", "where",
        "latin", "greek", "english", "roman", "language", "languages", "word",
        "please", "again", "remember", "earlier", "before",
    }
    # "word" kept out of stop when it's content — actually in teach table; allow
    stop.discard("word")
    stop.discard("language")
    out: List[str] = []
    for t in tokens:
        tl = (t or "").lower()
        if tl and tl not in stop and tl.isascii():
            out.append(tl)
    for m in meanings:
        ml = re.sub(r"[^a-z_]", "", (m or "").lower().replace(" ", "_"))
        base = ml.split("_")[0] if ml else ""
        if base and base not in stop:
            out.append(base)
        if ml and ml not in stop:
            out.append(ml.replace("_", " ").split()[0])
    # unique preserve order
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def teach_pairs(
    text: str,
    *,
    meanings: Optional[Sequence[str]] = None,
    tokens: Optional[Sequence[str]] = None,
    lang: Optional[str] = None,
    pul_terms: Optional[Dict[str, str]] = None,
    limit: int = 8,
) -> Dict[str, Any]:
    """
    Build form↔gloss teaching pairs for english_meta questions.
    """
    lang = lang or detect_teach_lang(text) or "la"
    table = _table_for(lang)
    glosses = _content_glosses(tokens or [], meanings or [])
    # also scan raw text words
    for w in re.findall(r"[a-zA-Z]+", text or ""):
        wl = w.lower()
        if wl not in glosses:
            glosses.append(wl)

    pairs: List[Dict[str, str]] = []
    seen_forms: set = set()
    for g in glosses:
        forms = table.get(g) or table.get(g.rstrip("s"))  # hands→hand soft
        if not forms and g.endswith("s") and g[:-1] in table:
            forms = table[g[:-1]]
        if not forms:
            continue
        for form in forms:
            key = f"{form}|{g}"
            if key in seen_forms:
                continue
            seen_forms.add(key)
            pairs.append({"lang": lang, "form": form, "gloss": g, "source": "teach_table"})
            if len(pairs) >= limit:
                break
        if len(pairs) >= limit:
            break

    # Optional targeted reverse only when table empty (avoid 100k+ scan latency)
    if pul_terms and len(pairs) == 0:
        want = {g.replace(" ", "_") for g in glosses} | set(glosses)
        found = 0
        for form, meaning in pul_terms.items():
            if found >= min(4, limit):
                break
            if not form or len(form) > 18:
                continue
            if lang == "la" and not form.isascii():
                continue
            m = (meaning or "").lower().strip().replace(" ", "_")
            base = m.split("_")[0] if m else ""
            hit_g = m if m in want else (base if base in want else None)
            if not hit_g:
                continue
            key = f"{form}|{hit_g}"
            if key in seen_forms:
                continue
            seen_forms.add(key)
            pairs.append(
                {
                    "lang": lang,
                    "form": form,
                    "gloss": hit_g.replace("_", " "),
                    "source": "lexicon_reverse",
                }
            )
            found += 1

    label = {"la": "Latin", "grc": "Greek", "ang": "Old English"}.get(lang, lang)
    lines = []
    for p in pairs:
        lines.append(f"  · {p['gloss']} ↔ {p['form']}  ({label})")
    return {
        "lang": lang,
        "label": label,
        "pairs": pairs,
        "lines": lines,
        "n": len(pairs),
        "ok": len(pairs) > 0,
    }


def format_teach_block(panel: Dict[str, Any]) -> List[str]:
    if not panel.get("ok"):
        return [
            f"Teaching ({panel.get('label', 'classical')}): "
            "(no table hit — densify classical pairs for this gloss set)"
        ]
    lines = [f"Teaching ({panel.get('label')} form ↔ English gloss):"]
    lines.extend(panel.get("lines") or [])
    return lines
