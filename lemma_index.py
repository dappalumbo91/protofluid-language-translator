#!/usr/bin/env python3
"""
Lemma / stem sense index (Collatinus / WORDS-inspired).

After train inject, index folded stems → frequency of *content* glosses.
Open-set: peel inflection → majority content sense when support is clear.

FSOT-safe: no free generation; only reuses train-supported senses.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from meaning_clean import content_score, fold_form, is_meta_meaning
from reverse_morph import candidate_stems
from gapfill_student import edit_sim


@dataclass
class SenseHit:
    meaning: str
    score: float
    support: int
    method: str
    donor_stem: str


class LemmaSenseIndex:
    def __init__(self) -> None:
        # stem -> Counter(meaning)
        self.stem_senses: Dict[str, Counter] = defaultdict(Counter)
        # stem -> best example surface form (for debugging)
        self.stem_example: Dict[str, str] = {}
        self.n_forms = 0

    def add_form(self, form: str, meaning: str, lang: str = "la") -> None:
        if not form or not meaning:
            return
        if is_meta_meaning(meaning):
            return
        if content_score(meaning) < 0.35:
            return
        self.n_forms += 1
        # index full fold + all candidate stems
        nf = fold_form(form)
        if len(nf) >= 3:
            self.stem_senses[nf][meaning] += 1
            self.stem_example.setdefault(nf, form)
        for st in candidate_stems(form, lang):
            if len(st) < 3:
                continue
            self.stem_senses[st][meaning] += 2 if st == nf else 1
            self.stem_example.setdefault(st, form)

    def build_from_lexicon(self, lexicon: Dict[str, str], lang_hint: str = "la") -> int:
        n = 0
        for form, meaning in lexicon.items():
            # skip pure folded duplicates of long keys lightly
            if len(form) < 2:
                continue
            # language guess for stem inventory
            lang = lang_hint
            if any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in form):
                lang = "grc"
            self.add_form(form, meaning, lang=lang)
            n += 1
        return n

    def resolve(self, form: str, lang: str = "la") -> Optional[SenseHit]:
        if not form or not self.stem_senses:
            return None
        nf = fold_form(form)
        candidates: List[Tuple[str, Counter]] = []
        # exact fold
        if nf in self.stem_senses:
            candidates.append((nf, self.stem_senses[nf]))
        for st in candidate_stems(form, lang):
            if len(st) < 3:
                continue
            if st in self.stem_senses and st != nf:
                candidates.append((st, self.stem_senses[st]))

        best: Optional[SenseHit] = None
        for stem, counter in candidates:
            if not counter:
                continue
            if len(stem) < 3:
                continue
            total = sum(counter.values())
            meaning, cnt = counter.most_common(1)[0]
            share = cnt / max(1, total)
            ex = self.stem_example.get(stem, stem)
            exf = fold_form(ex)
            sim = edit_sim(nf, exf)

            # short stems (man, aqu): need strong majority + form kinship
            if len(stem) < 4:
                if cnt < 3 or share < 0.70 or sim < 0.48:
                    continue
                # both query and example should share the short stem prefix
                if not (nf.startswith(stem) and exf.startswith(stem)):
                    continue
            else:
                if cnt < 2:
                    if len(stem) < 6 or content_score(meaning) < 0.6 or share < 0.95:
                        continue
                if share < 0.50:
                    continue
                if len(stem) < 5 and sim < 0.52:
                    continue
                if len(stem) >= 5 and sim < 0.38 and not nf.startswith(stem[:4]):
                    continue

            base = 0.52 + 0.28 * share + 0.07 * min(5, cnt) + 0.1 * content_score(meaning)
            if len(stem) >= 5:
                base += 0.04
            if sim >= 0.6:
                base += 0.05
            # penalize ultra-short stems even when accepted
            if len(stem) < 4:
                base *= 0.92
            score = min(0.94, base)
            if score < 0.76:
                continue
            hit = SenseHit(meaning, score, cnt, f"lemma_sense_n{cnt}", stem)
            if best is None or hit.score > best.score:
                best = hit
        return best


def majority_meaning(
    pairs: Iterable[Tuple[str, str]],
    token: str,
) -> Optional[Tuple[str, str, float]]:
    """
    Among (form, meaning) donors, pick content-weighted majority.
    Returns (meaning, best_form, score) or None.
    """
    weights: Dict[str, float] = defaultdict(float)
    best_form: Dict[str, str] = {}
    for form, meaning in pairs:
        if is_meta_meaning(meaning):
            w = 0.15
        else:
            w = 0.5 + 0.5 * content_score(meaning)
        w *= 0.5 + 0.5 * edit_sim(token, form)
        weights[meaning] += w
        if meaning not in best_form or edit_sim(token, form) > edit_sim(
            token, best_form[meaning]
        ):
            best_form[meaning] = form
    if not weights:
        return None
    meaning, w = max(weights.items(), key=lambda kv: kv[1])
    total = sum(weights.values()) or 1.0
    share = w / total
    if share < 0.4:
        return None
    return meaning, best_form[meaning], min(0.93, 0.5 + 0.4 * share)
