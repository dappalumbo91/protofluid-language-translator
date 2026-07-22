#!/usr/bin/env python3
"""
Multi-sense vote for open-set gap-fill.

Wrong-sense residual class (CORE diagnosis ~half of misses) comes from
polysemy + short-stem neighbor collisions (ψυχή→cold via ψυχ-; βραχίων→shallows).

Policy (FSOT-safe, no free NMT):
  1) Collect candidates from morph / lemma / booster methods
  2) Drop garbage/meta and weak form-similarity
  3) Vote by meaning with form_sim × method_prior × content_score
  4) Prefer multi-method agreement; domain-rank only on remaining ties
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from gapfill_student import edit_sim
from meaning_clean import content_score, fold_form, is_garbage_meaning, is_meta_meaning

# Method reliability priors (higher = trust more when form_sim ties)
_METHOD_PRIOR: Dict[str, float] = {
    "demonym_seed": 1.15,
    "demonym_stem_seed": 1.10,
    "demonym_seed_trim": 1.08,
    "decl_4th_us": 1.12,
    "decl_lemma": 1.10,
    "decl_stem": 0.95,
    "rev_lemma_end": 1.08,
    "rev_exact": 1.20,
    "rev_exact_fold": 1.18,
    "rev_stem_key": 0.90,
    "rev_prefix_family": 0.82,
    "lemma_sense": 1.00,
    "stem_match": 0.92,
    "ethnonym_peel": 0.95,
    "ethnonym_place": 0.90,
    "folded_exact": 1.15,
    "rosetta": 0.88,
    "prefix_neighbor": 0.78,
    "ngram_knn": 0.72,
    "substring": 0.80,
    "translit_exact": 1.05,
    "translit_stem": 0.88,
    "gapfill_edit": 0.70,
}


@dataclass(frozen=True)
class SenseCand:
    meaning: str
    donor: str
    score: float
    method: str
    form_sim: float = 0.0

    def effective_sim(self, token: str) -> float:
        if self.form_sim > 0:
            return self.form_sim
        return edit_sim(token, self.donor or "")


def _norm_meaning(m: str) -> str:
    return (m or "").strip().lower().replace(" ", "_").strip("_")


def form_sim_floor(method: str, token: str, donor: str) -> float:
    """Stricter floors for short stems / weak methods."""
    t, d = fold_form(token), fold_form(donor)
    L = min(len(t), len(d)) if t and d else 0
    # shared prefix length
    pref = 0
    for a, b in zip(t, d):
        if a != b:
            break
        pref += 1

    base = {
        "demonym_seed": 0.0,  # seed table — no donor form required
        "demonym_stem_seed": 0.0,
        "demonym_seed_trim": 0.0,
        "rev_exact": 0.95,
        "rev_exact_fold": 0.95,
        "folded_exact": 0.90,
        "decl_4th_us": 0.50,
        "decl_lemma": 0.48,
        "rev_lemma_end": 0.50,
        "decl_stem": 0.58,
        "rev_stem_key": 0.64,
        "rev_prefix_family": 0.66,
        "stem_match": 0.52,
        "prefix_neighbor": 0.68,
        "ngram_knn": 0.72,
        "lemma_sense": 0.45,
        "ethnonym_peel": 0.40,
        "ethnonym_place": 0.38,
        "translit_stem": 0.52,
        "translit_exact": 0.0,
        "rosetta": 0.0,
        "gapfill_edit": 0.68,
    }.get(method, 0.52)

    # fragment-only prefix match → stricter whole-form floor
    shorter = min(len(t), len(d)) if t and d else 0
    if (
        shorter >= 5
        and pref >= 3
        and (pref / shorter) < 0.55
        and abs(len(t) - len(d)) >= 2
    ):
        base = max(base, 0.70)
    if L <= 4 and method not in {"demonym_seed", "demonym_stem_seed", "demonym_seed_trim"}:
        base = max(base, 0.68)
    if t and d and abs(len(t) - len(d)) >= 5:
        base = max(base, 0.64)
    return base


def filter_cands(token: str, cands: Sequence[SenseCand]) -> List[SenseCand]:
    out: List[SenseCand] = []
    for c in cands:
        if not c.meaning or is_meta_meaning(c.meaning) or is_garbage_meaning(c.meaning):
            continue
        if content_score(c.meaning) < 0.28:
            continue
        sim = c.effective_sim(token)
        # seed demonyms may have empty donor
        if c.method.startswith("demonym_seed") or c.method.startswith("demonym_stem_seed"):
            out.append(
                SenseCand(c.meaning, c.donor, c.score, c.method, max(sim, 0.85))
            )
            continue
        floor = form_sim_floor(c.method, token, c.donor)
        if sim < floor:
            continue
        if c.score < 0.55 and sim < 0.75:
            continue
        out.append(SenseCand(c.meaning, c.donor, c.score, c.method, sim))
    return out


def vote_senses(
    token: str,
    cands: Sequence[SenseCand],
    *,
    context: str = "historical",
    min_score: float = 0.72,
) -> Optional[Tuple[str, float, str]]:
    """
    Returns (meaning, confidence, method_tag) or None.
    """
    kept = filter_cands(token, cands)
    if not kept:
        return None

    # weight per meaning
    weights: Dict[str, float] = defaultdict(float)
    methods: Dict[str, List[str]] = defaultdict(list)
    best_sim: Dict[str, float] = defaultdict(float)
    best_score: Dict[str, float] = defaultdict(float)

    for c in kept:
        mk = _norm_meaning(c.meaning)
        prior = _METHOD_PRIOR.get(c.method, 0.85)
        # method family key (strip _n12 suffixes)
        fam = c.method.split("_n")[0]
        prior = _METHOD_PRIOR.get(fam, prior)
        w = (
            c.score
            * (0.45 + 0.55 * c.form_sim)
            * prior
            * (0.55 + 0.45 * content_score(c.meaning))
        )
        # multi-method agreement bonus applied later
        weights[mk] += w
        methods[mk].append(c.method)
        best_sim[mk] = max(best_sim[mk], c.form_sim)
        best_score[mk] = max(best_score[mk], c.score)

    # agreement boost
    for mk, ms in methods.items():
        uniq = {m.split("_n")[0] for m in ms}
        if len(uniq) >= 2:
            weights[mk] *= 1.0 + 0.12 * min(3, len(uniq) - 1)
        if len(ms) >= 3:
            weights[mk] *= 1.08

    total = sum(weights.values()) or 1.0
    ranked = sorted(weights.items(), key=lambda kv: -kv[1])
    top_m, top_w = ranked[0]
    share = top_w / total

    # domain break ties when close runners
    if len(ranked) >= 2 and ranked[0][1] < ranked[1][1] * 1.12:
        try:
            from domain_sense import pick_sense

            senses = [m for m, _ in ranked[:5]]
            # map back to original casing from cands
            orig = {}
            for c in kept:
                orig.setdefault(_norm_meaning(c.meaning), c.meaning)
            picked = pick_sense([orig.get(s, s) for s in senses], context)
            if picked:
                top_m = _norm_meaning(picked)
                share = max(share, 0.45)
        except Exception:
            pass

    conf = min(
        0.96,
        0.35 * share
        + 0.35 * best_sim[top_m]
        + 0.20 * min(1.0, best_score[top_m])
        + 0.10 * min(1.0, content_score(top_m)),
    )

    # refuse high-entropy votes
    if share < 0.38 and best_sim[top_m] < 0.78:
        return None
    if conf < min_score:
        # allow strong single-method high form_sim
        if best_sim[top_m] >= 0.85 and best_score[top_m] >= 0.88 and share >= 0.50:
            conf = max(conf, 0.74)
        else:
            return None

    # recover original meaning string (prefer highest content)
    originals = [
        c.meaning
        for c in kept
        if _norm_meaning(c.meaning) == top_m
    ]
    if not originals:
        return None
    meaning = max(originals, key=lambda m: (content_score(m), -len(m)))
    tag = "+".join(sorted({m.split("_n")[0] for m in methods[top_m]})[:3])
    return meaning, conf, f"sense_vote:{tag}"


def cands_from_tuple(
    hit: Optional[Tuple],
    method: str,
    token: str,
) -> List[SenseCand]:
    """Normalize various (meaning, donor, score, ...) tuples into SenseCand list."""
    if hit is None:
        return []
    if isinstance(hit, SenseCand):
        return [hit]
    meaning = hit[0]
    donor = hit[1] if len(hit) > 1 else token
    score = float(hit[2]) if len(hit) > 2 else 0.8
    meth = hit[3] if len(hit) > 3 and isinstance(hit[3], str) else method
    sim = edit_sim(token, str(donor or token))
    return [SenseCand(str(meaning), str(donor or ""), score, str(meth), sim)]
