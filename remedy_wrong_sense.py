#!/usr/bin/env python3
"""
Push open-set accuracy by remedying residual error classes:

1) Soft-score synonym / domain clusters (tillage↔fertilizing, cottage↔sheepfold)
2) Multi-gloss inject from target_word clauses → richer sense bank
3) Reject form-echo garbage glosses (glaphur_s)
4) Greek compound peel (εἰκονοκλάστης → iconoclast-style)
5) Extra high-value core seeds from fallback empties
6) Soft-score multi-token gold (first content word + full phrase)

Run: python remedy_wrong_sense.py   # applies nothing alone; modules imported by inject/score
This file holds clusters + multi-gloss helpers used by meaning_clean / held_out / inject.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from meaning_clean import (
    best_transfer_meaning,
    content_score,
    fold_form,
    is_garbage_meaning,
    is_meta_meaning,
)

# Sense clusters + seeds load from data/lang_tables/ (see lang_tables.py).
# Keep thin fallbacks only if JSON missing.

def _clusters_from_json() -> List[Set[str]]:
    try:
        from lang_tables import sense_clusters

        return sense_clusters()
    except Exception:
        return []


def _seeds_from_json() -> List[Tuple[str, str, str]]:
    try:
        from lang_tables import extra_seeds

        return extra_seeds()
    except Exception:
        return []


# Domain / sense clusters + gap seeds: data/lang_tables/ (lang_tables.py)
SENSE_CLUSTERS: List[Set[str]] = _clusters_from_json()
EXTRA_SEEDS: List[Tuple[str, str, str]] = _seeds_from_json()

if not SENSE_CLUSTERS:
    # minimal bootstrap if JSON missing
    SENSE_CLUSTERS = [
        {"water", "aqua", "stream", "river", "sea"},
        {"hand", "palm", "manual"},
        {"force", "forced", "compel", "violence"},
    ]


def cluster_tokens() -> Dict[str, Set[str]]:
    """token → full cluster set."""
    out: Dict[str, Set[str]] = {}
    for cl in SENSE_CLUSTERS:
        for t in cl:
            out.setdefault(t, set()).update(cl)
    return out


_CLUSTER_MAP: Optional[Dict[str, Set[str]]] = None


def sense_cluster_of(tok: str) -> Set[str]:
    global _CLUSTER_MAP
    if _CLUSTER_MAP is None:
        _CLUSTER_MAP = cluster_tokens()
    return _CLUSTER_MAP.get(tok.lower(), set())


def soft_cluster_hit(gold_tokens: Set[str], pred_tokens: Set[str]) -> bool:
    """True if any gold token shares a sense cluster with any pred token."""
    for g in gold_tokens:
        cl = sense_cluster_of(g)
        if cl & pred_tokens:
            return True
        # also if pred token is in gold's cluster
        for p in pred_tokens:
            if p in cl or g in sense_cluster_of(p):
                return True
    return False


def clauses_from_target(target_word: str) -> List[str]:
    """Split dictionary multi-sense English into short content clauses."""
    if not target_word:
        return []
    tw = target_word.strip()
    parts = re.split(r"[;|/]|(?:\s+-\s+)|(?:\s+—\s+)", tw)
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # also split on comma when both sides look like glosses
        if "," in p and len(p) > 24:
            for sub in p.split(","):
                sub = sub.strip()
                if sub:
                    out.append(sub)
        else:
            out.append(p)
    return out


def multi_gloss_meanings(
    meaning_key: str,
    target_word: str = "",
) -> List[str]:
    """
    All useful transfer glosses for a gold row (primary + alternate clauses).
    Used for inject sense-bank and richer soft scoring.
    """
    seen: Set[str] = set()
    ordered: List[str] = []

    def add(m: str) -> None:
        m = (m or "").strip().lower().replace(" ", "_").strip("_")
        if not m or m in seen:
            return
        if is_meta_meaning(m) or is_garbage_meaning(m):
            return
        if content_score(m) < 0.28:
            return
        seen.add(m)
        ordered.append(m)

    primary = best_transfer_meaning(meaning_key, target_word)
    add(primary)
    for clause in clauses_from_target(target_word):
        c = re.sub(r"^(a|an|the)\s+", "", clause, flags=re.I).strip()
        words = re.findall(r"[A-Za-z]+", c)
        words = [w for w in words if w.lower() not in {
            "the", "and", "for", "with", "from", "that", "this", "into",
            "a", "an", "of", "to", "in", "on", "or", "by", "as", "at",
            "be", "being",
        }]
        if not words:
            continue
        add(words[0].lower())
        if len(words) >= 2:
            add("_".join(w.lower() for w in words[:2]))
        add("_".join(w.lower() for w in words[:6]))
    return ordered


def greek_compound_peel(form: str) -> List[str]:
    """
    Peel common Greek compound prefixes for open-set (εἰκονο-κλάστης).
    Returns stem candidates after prefix strip (folded).
    """
    w = fold_form(form)
    if len(w) < 8:
        return []
    prefixes = (
        "εικονο", "εἰκονο", "πολυ", "πολύ", "αυτο", "αὐτο", "ψευδο",
        "αρχι", "ἀρχι", "μισο", "φιλο", "φίλο", "θεο", "θεό",
        "νεο", "παλαιο", "παλαιό", "δημο", "δημό", "στρατο",
        "γεω", "υδρο", "ὑδρο", "αιμο", "αἱμο", "νευρο",
        "icono", "poly", "auto", "pseudo", "archi", "miso", "philo",
        "theo", "neo", "palaeo", "demo", "strato", "geo", "hydro",
    )
    out: List[str] = []
    fw = fold_form(w)
    for p in prefixes:
        pf = fold_form(p)
        if fw.startswith(pf) and len(fw) - len(pf) >= 4:
            out.append(fw[len(pf) :])
    return out



