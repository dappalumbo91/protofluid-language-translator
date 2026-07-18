#!/usr/bin/env python3
"""
Aggressive open-set accuracy booster for classical forms.

Stack (all gated, no free LLM):
  1) Morphology stem match against train lexicon (Latin/Greek/OE-friendly)
  2) Diacritic-folded exact / stem match
  3) Prefix/suffix neighbor match (bucketed)
  4) Char n-gram k-NN over train forms
  5) Rosetta form→concept→EN (when form exists in matrix)
  6) Greek→Latin transliteration cognate bridge
  7) Substring / ethnonym ending peel
  8) Meaning-cleaned donors (prefer content glosses over grammatical meta)

Goal: push held-out partial well above ~13%.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from gapfill_student import combined_sim, edit_sim, trigram_dice
from meaning_clean import (
    build_cleaned_lexicon,
    content_score,
    fold_form,
    is_meta_meaning,
)

DATA = Path(__file__).resolve().parent / "data"

# Common Latin inflectional endings (longer first)
LAT_SUFFIXES = (
    "ationibus", "ationem", "ationis", "ationes", "ationi",
    "tionibus", "tatem", "tatis", "tates", "tatum",
    "ionibus", "iones", "ionis", "ionem", "ioni", "ione",
    "orum", "arum", "ibus", "uum", "eus", "ius", "ium",
    "arum", "orum", "ibus",
    "ibus", "orum", "arum",
    "antur", "untur", "amini", "imini",
    "abant", "ebant", "iebant", "abantur",
    "isse", "isse", "arum",
    "ibus", "orum",
    "us", "um", "am", "ae", "as", "is", "os", "em", "es", "en",
    "ou", "on", "oi", "ai",  # hellenizing latin
    "or", "ur", "ux", "ix", "ax", "ex", "ox",
    "nt", "ns", "rs",
    "a", "o", "i", "e", "u",
)

# Greek (polytonic / monotonic) common endings — folded forms also used
GRC_SUFFIXES = (
    "οισιν", "αισιν", "εσσιν",
    "οις", "αις", "ους", "ας", "ης", "ων", "ον", "ος", "η", "α", "ι", "ν",
    "ου", "ης", "ῃ", "ῳ", "εις", "εως", "εων", "εσι", "εσιν",
    "της", "τις", "τος", "τα", "τες", "των",
    "ευς", "εως", "εα", "εις",
    "ιος", "ιου", "ιον", "ια", "ιης",
    "ικος", "ικη", "ικον",
    "ισσα", "ισσης",
)

# Latin derivational / agentive (Whitaker-style residual after inflection peel)
LAT_DERIV = (
    "tionibus", "tionem", "tionis", "tiones",
    "tor", "sor", "trix", "tura", "turae", "mentum", "men",
    "bilis", "bundus", "idus", "osus", "alis", "aris", "arius",
    "ensis", "anus", "icus", "ivus", "ulus", "ellus",
)

# Latinized Greek endings on romanized forms
GRC_LAT_SUFFIXES = (
    "eous", "ious", "icus", "ica", "icum", "esis", "osis",
    "tes", "tis", "tos", "eus", "ea", "ios", "ion", "ias", "ia",
    "os", "on", "es", "as", "is", "ou", "oi", "ai", "ae",
)

# Old English / Ang common endings
ANG_SUFFIXES = (
    "ienne", "enne", "ende", "enne",
    "ath", "eth", "ian", "igan", "igan",
    "um", "an", "as", "es", "e", "a", "u", "o",
)

# Ethnonym / demonym peels (Greek + Latin)
ETHNONYM_PEEL = (
    "ιώτης", "ιώτου", "ίτης", "ίτου", "εύς", "έως", "αίος", "αῖος",
    "ιος", "ιου", "ης", "ου", "ος", "ων",
    "ensis", "enses", "anum", "anus", "ana", "ani", "icus", "ica", "icum",
    "enses", "ensium",
)


def _norm(s: str) -> str:
    return fold_form(s)


def stem_la(word: str) -> str:
    w = _norm(word)
    for suf in sorted(set(LAT_SUFFIXES) | set(LAT_DERIV), key=len, reverse=True):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def stem_grc(word: str) -> str:
    w = _norm(word)
    for suf in sorted(set(GRC_SUFFIXES), key=len, reverse=True):
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            return w[: -len(suf)]
    for suf in sorted(set(GRC_LAT_SUFFIXES), key=len, reverse=True):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def stem_ang(word: str) -> str:
    w = _norm(word)
    for suf in sorted(set(ANG_SUFFIXES), key=len, reverse=True):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def char_ngrams(s: str, n: int = 3) -> Dict[str, int]:
    s = f"#{_norm(s)}#"
    g: Dict[str, int] = defaultdict(int)
    for i in range(max(0, len(s) - n + 1)):
        g[s[i : i + n]] += 1
    return g


def cosine_sparse(a: Dict[str, int], b: Dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    for k, v in a.items():
        if k in b:
            dot += v * b[k]
    na = sum(v * v for v in a.values()) ** 0.5
    nb = sum(v * v for v in b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def grc_to_latin(s: str) -> str:
    """Rough Greek orthography → Latin letters for cognate bridge."""
    f = fold_form(s)
    for src, dst in (
        ("θ", "th"), ("φ", "ph"), ("χ", "ch"), ("ψ", "ps"), ("ξ", "x"),
        ("η", "e"), ("ω", "o"), ("υ", "y"), ("β", "b"), ("γ", "g"),
        ("δ", "d"), ("ζ", "z"), ("κ", "k"), ("λ", "l"), ("μ", "m"),
        ("ν", "n"), ("π", "p"), ("ρ", "r"), ("σ", "s"), ("ς", "s"),
        ("τ", "t"), ("α", "a"), ("ε", "e"), ("ι", "i"), ("ο", "o"),
    ):
        f = f.replace(src, dst)
    return re.sub(r"[^a-z]", "", f)


@dataclass
class OpenHit:
    meaning: str
    score: float
    method: str
    donor: str


class OpenSetBooster:
    def __init__(self, lexicon: Dict[str, str], lang_hint: str = "la"):
        """
        lexicon: surface form -> meaning_key (train only when evaluating holdout)
        """
        raw = {k: v for k, v in lexicon.items() if len(_norm(k)) >= 2}
        self.lex = build_cleaned_lexicon(raw)
        self.lang = lang_hint
        if lang_hint in {"grc", "el"}:
            self.stem_fn = stem_grc
        elif lang_hint in {"ang", "oe", "enm"}:
            self.stem_fn = stem_ang
        else:
            self.stem_fn = stem_la

        self.by_stem: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.by_fold: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.by_prefix4: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        # Lazy n-grams — full precompute is too heavy on 100k+ paradigm-expanded lex
        self.ngrams: Dict[str, Dict[str, int]] = {}
        self.forms: List[str] = []
        # Cap index growth on huge lexica (prefer shorter content headwords first)
        items = sorted(self.lex.items(), key=lambda kv: (len(kv[0]), -content_score(kv[1])))
        if len(items) > 80000:
            items = items[:80000]

        for form, meaning in items:
            nf = _norm(form)
            if len(nf) < 2:
                continue
            self.forms.append(form)
            st = self.stem_fn(form)
            # cap stem bucket size
            if len(self.by_stem[st]) < 40:
                self.by_stem[st].append((form, meaning))
            if len(self.by_fold[nf]) < 8:
                self.by_fold[nf].append((form, meaning))
            if len(nf) >= 4 and len(self.by_prefix4[nf[:4]]) < 80:
                self.by_prefix4[nf[:4]].append((form, meaning))
            # Cross-script bridges: romanized ↔ Greek stems share one bucket
            if lang_hint in {"grc", "el"}:
                lat = grc_to_latin(form) if re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", form) else nf
                if lat and len(lat) >= 2:
                    if len(self.by_fold[lat]) < 8:
                        self.by_fold[lat].append((form, meaning))
                    if len(self.by_stem[stem_la(lat)]) < 40:
                        self.by_stem[stem_la(lat)].append((form, meaning))
                    if len(lat) >= 4 and len(self.by_prefix4[lat[:4]]) < 80:
                        self.by_prefix4[lat[:4]].append((form, meaning))
                if re.fullmatch(r"[a-z]+", nf) and len(self.by_stem[stem_la(nf)]) < 40:
                    self.by_stem[stem_la(nf)].append((form, meaning))
            elif re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", form):
                lat = grc_to_latin(form)
                if lat and len(lat) >= 2:
                    if len(self.by_stem[stem_la(lat)]) < 40:
                        self.by_stem[stem_la(lat)].append((form, meaning))
                    if len(self.by_fold[lat]) < 8:
                        self.by_fold[lat].append((form, meaning))

        # rosetta
        self.concept_en: Dict[str, str] = {}
        self.form_index: Dict[str, str] = {}
        ce = DATA / "rosetta_concept_to_en.json"
        fi = DATA / "rosetta_form_index.json"
        if ce.exists():
            self.concept_en = json.loads(ce.read_text(encoding="utf-8"))
        if fi.exists():
            # index folded keys too
            raw_fi = json.loads(fi.read_text(encoding="utf-8"))
            self.form_index = dict(raw_fi)
            for k, v in list(raw_fi.items()):
                if "|" in k:
                    lang, form = k.split("|", 1)
                    fk = f"{lang}|{_norm(form)}"
                    self.form_index.setdefault(fk, v)

    def _pick_meaning(self, donors: List[Tuple[str, str]], token: str) -> Tuple[str, str, float]:
        """Majority / content-weighted meaning among donors."""
        weights: Dict[str, float] = defaultdict(float)
        best_form = donors[0][0]
        for form, meaning in donors:
            w = content_score(meaning) * (0.6 + 0.4 * edit_sim(token, form))
            # penalize pure meta
            if is_meta_meaning(meaning):
                w *= 0.25
            weights[meaning] += w
            if w >= weights[meaning] - 1e-9:
                best_form = form
        meaning = max(weights.items(), key=lambda kv: kv[1])[0]
        return meaning, best_form, weights[meaning]

    def _rosetta(self, token: str) -> Optional[OpenHit]:
        nf = _norm(token)
        langs = (self.lang, "la", "lat", "grc", "el", "ang", "en", "akk", "sum", "san")
        for lang in langs:
            for form in (nf, token.lower(), token):
                k = f"{lang}|{form}"
                if k in self.form_index:
                    concept = self.form_index[k]
                    en = self.concept_en.get(concept)
                    if en:
                        mk = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")
                        return OpenHit(mk, 0.96, "rosetta_exact", k)
        # folded greek via latinized key under en/la
        lat = grc_to_latin(token)
        if len(lat) >= 3:
            for lang in ("en", "la", "lat", "grc"):
                k = f"{lang}|{lat}"
                if k in self.form_index:
                    concept = self.form_index[k]
                    en = self.concept_en.get(concept)
                    if en:
                        mk = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")
                        return OpenHit(mk, 0.88, "rosetta_translit", k)
        return None

    def _folded_exact(self, token: str) -> Optional[OpenHit]:
        nf = _norm(token)
        pairs = self.by_fold.get(nf) or []
        if not pairs:
            return None
        meaning, donor, w = self._pick_meaning(pairs, token)
        return OpenHit(meaning, min(0.99, 0.9 + 0.05 * content_score(meaning)), "folded_exact", donor)

    def _stem_match(self, token: str) -> Optional[OpenHit]:
        st = self.stem_fn(token)
        if len(st) < 3:
            return None
        # exact stem bucket only (fuzzy stem was too noisy → ~60% wrong)
        donors = list(self.by_stem.get(st) or [])
        if not donors:
            return None
        # drop pure-meta donors when any content donor exists
        content_donors = [(f, m) for f, m in donors if not is_meta_meaning(m)]
        if content_donors:
            donors = content_donors
        # Keep only donors that look like true inflectional variants of token
        t_norm = _norm(token)
        tight: List[Tuple[str, str]] = []
        for form, m in donors:
            f = _norm(form)
            sim = edit_sim(t_norm, f)
            len_diff = abs(len(t_norm) - len(f))
            # shared stem + small length delta OR high whole-form similarity
            if sim >= 0.62 or (len_diff <= 3 and sim >= 0.48 and len(st) >= 4):
                # both should start with stem (approx)
                if f.startswith(st[: min(4, len(st))]) or t_norm.startswith(st[: min(4, len(st))]):
                    tight.append((form, m))
        if not tight:
            return None
        donors = tight
        meaning, best_form, w = self._pick_meaning(donors, token)
        # meaning concentration: refuse high-entropy stem buckets
        weights: Dict[str, float] = defaultdict(float)
        for form, m in donors:
            weights[m] += content_score(m) * (0.5 + 0.5 * edit_sim(token, form))
        total_w = sum(weights.values()) or 1.0
        top_share = weights[meaning] / total_w
        if top_share < 0.50:
            return None
        form_sim = edit_sim(token, best_form)
        support = len(donors)
        base = 0.50 + 0.05 * min(5, support) + 0.32 * form_sim
        base += 0.10 * content_score(meaning) + 0.10 * top_share
        if len(st) >= 5:
            base += 0.04
        if is_meta_meaning(meaning):
            base *= 0.5
        score = min(0.94, base)
        # Content glosses may pass a slightly looser form gate
        min_score = 0.66 if content_score(meaning) >= 0.55 else 0.72
        min_sim = 0.44 if content_score(meaning) >= 0.55 else 0.52
        if score < min_score or form_sim < min_sim:
            return None
        if len(st) < 4 and form_sim < 0.78:
            return None
        return OpenHit(meaning, score, f"stem_match_n{support}", best_form)

    def _ethnonym_peel(self, token: str) -> Optional[OpenHit]:
        """Γαλάτης / Κρής-style: peel demonym ending, match place/people stem."""
        if self.lang not in {"grc", "el", "la", "lat"}:
            return None
        w = _norm(token)
        if len(w) < 4:
            return None
        for suf in sorted(ETHNONYM_PEEL, key=len, reverse=True):
            suf_f = _norm(suf)
            if w.endswith(suf_f) and len(w) - len(suf_f) >= 3:
                stem = w[: -len(suf_f)]
                donors = list(self.by_stem.get(stem) or [])
                # also prefix neighbors
                for form, meaning in self.by_prefix4.get(stem[:4], []):
                    if _norm(form).startswith(stem[: max(3, len(stem) - 1)]):
                        donors.append((form, meaning))
                if not donors:
                    continue
                meaning, donor, _ = self._pick_meaning(donors, token)
                if is_meta_meaning(meaning):
                    continue
                # demonym gloss: prefer place/people content + form evidence
                form_sim = edit_sim(token, donor)
                if form_sim < 0.45:
                    continue
                score = min(0.9, 0.55 + 0.2 * content_score(meaning) + 0.2 * form_sim)
                if score >= 0.70:
                    return OpenHit(meaning, score, "ethnonym_peel", donor)
                # if place/people stem meaning is short content, accept as demonym
                if content_score(meaning) >= 0.55 and form_sim >= 0.40 and len(stem) >= 4:
                    return OpenHit(meaning, 0.72, "ethnonym_place", donor)
        return None

    def _prefix_match(self, token: str) -> Optional[OpenHit]:
        t = _norm(token)
        if len(t) < 4:
            return None
        bucket = self.by_prefix4.get(t[:4], [])
        best: Optional[OpenHit] = None
        for form, meaning in bucket:
            f = _norm(form)
            if len(f) < 4:
                continue
            i = 0
            while i < min(len(t), len(f)) and t[i] == f[i]:
                i += 1
            if i >= 4:
                s = 0.45 * (i / max(len(t), len(f))) + 0.55 * edit_sim(t, f)
                s *= 0.7 + 0.3 * content_score(meaning)
                if is_meta_meaning(meaning):
                    s *= 0.5
                if s >= 0.68 and (best is None or s > best.score):
                    best = OpenHit(meaning, s, "prefix_neighbor", form)
        return best

    def _ngram_knn(self, token: str, k: int = 12) -> Optional[OpenHit]:
        t = _norm(token)
        if len(t) < 3:
            return None
        q = char_ngrams(token)
        # restrict to same prefix bucket + length band for speed
        pool: List[Tuple[str, str]] = []
        if len(t) >= 4:
            pool.extend(self.by_prefix4.get(t[:4], []))
        # also second prefix if short pool
        if len(pool) < 40 and len(t) >= 3:
            for form, meaning in self.lex.items():
                f = _norm(form)
                if abs(len(f) - len(t)) <= 3 and f[:2] == t[:2]:
                    pool.append((form, meaning))
                if len(pool) > 400:
                    break
        if not pool:
            # fallback: length-band sample
            for form, meaning in self.lex.items():
                if abs(len(_norm(form)) - len(t)) <= 2:
                    pool.append((form, meaning))
                if len(pool) > 300:
                    break

        scored: List[Tuple[float, str, str]] = []
        seen = set()
        for form, meaning in pool:
            if form in seen:
                continue
            seen.add(form)
            ng = self.ngrams.get(form)
            if ng is None:
                ng = char_ngrams(form)
                if len(self.ngrams) < 20000:
                    self.ngrams[form] = ng
            s = cosine_sparse(q, ng)
            if s >= 0.20:
                s2 = 0.45 * s + 0.55 * combined_sim(token, form)
                s2 *= 0.65 + 0.35 * content_score(meaning)
                if is_meta_meaning(meaning):
                    s2 *= 0.45
                if s2 >= 0.42:
                    scored.append((s2, form, meaning))
        if not scored:
            return None
        scored.sort(reverse=True)
        top = scored[:k]
        votes: Dict[str, float] = defaultdict(float)
        for s, form, meaning in top:
            votes[meaning] += s
        meaning, score = max(votes.items(), key=lambda kv: kv[1])
        donor = next(f for s, f, m in top if m == meaning)
        conf = min(0.91, top[0][0] * (0.65 + 0.35 * (votes[meaning] / sum(votes.values()))))
        # n-gram is weakest signal — require strong agreement
        if conf < 0.72:
            return None
        if top[0][0] < 0.62:
            return None
        if is_meta_meaning(meaning):
            return None
        return OpenHit(meaning, conf, f"ngram_knn_k{len(top)}", donor)

    def _substring_match(self, token: str) -> Optional[OpenHit]:
        t = _norm(token)
        if len(t) < 6:
            return None
        best: Optional[OpenHit] = None
        pool = list(self.by_prefix4.get(t[:4], []))
        st = self.stem_fn(token)
        pool.extend(self.by_stem.get(st, []))
        seen = set()
        for form, meaning in pool:
            if form in seen:
                continue
            seen.add(form)
            f = _norm(form)
            if len(f) < 6:
                continue
            if t in f or f in t:
                ratio = min(len(t), len(f)) / max(len(t), len(f))
                # must be near-variants, not accidental substring
                if ratio < 0.72:
                    continue
                if is_meta_meaning(meaning):
                    continue
                s = 0.60 + 0.30 * ratio + 0.08 * content_score(meaning)
                if best is None or s > best.score:
                    best = OpenHit(meaning, min(0.9, s), "substring", form)
        if best is not None and best.score < 0.78:
            return None
        return best

    def _translit_bridge(self, token: str) -> Optional[OpenHit]:
        """Map Greek orthography → latin letters; match latin/en forms."""
        if self.lang not in {"grc", "el"}:
            return None
        lat = grc_to_latin(token)
        if len(lat) < 3:
            return None
        # exact folded
        pairs = self.by_fold.get(lat) or []
        if pairs:
            meaning, donor, _ = self._pick_meaning(pairs, lat)
            return OpenHit(meaning, 0.86, "translit_exact", donor)
        # stem of latinized form
        st = stem_la(lat)
        donors = list(self.by_stem.get(st) or [])
        if not donors and len(st) >= 4:
            for form, meaning in self.by_prefix4.get(st[:4], []):
                if stem_la(form) == st or edit_sim(st, stem_la(form)) >= 0.8:
                    donors.append((form, meaning))
        if not donors:
            return None
        meaning, donor, _ = self._pick_meaning(donors, lat)
        s = min(0.88, 0.58 + 0.2 * content_score(meaning) + 0.15 * edit_sim(lat, _norm(donor)))
        if s < 0.6:
            return None
        return OpenHit(meaning, s, "translit_stem", donor)

    def resolve(self, token: str) -> Optional[OpenHit]:
        if not token:
            return None
        if token in self.lex:
            return OpenHit(self.lex[token], 1.0, "exact", token)
        nf = _norm(token)
        if nf in self.lex:
            return OpenHit(self.lex[nf], 1.0, "exact", nf)
        if token.lower() in self.lex:
            return OpenHit(self.lex[token.lower()], 1.0, "exact", token.lower())

        # Tier A: high-precision (always trust)
        tier_a = []
        for fn in (self._folded_exact, self._rosetta):
            try:
                h = fn(token)
            except Exception:
                h = None
            if h is not None:
                tier_a.append(h)
        if tier_a:
            return max(tier_a, key=lambda h: (h.score, content_score(h.meaning)))

        # Tier B: morphology / transliteration (gated)
        tier_b = []
        for fn in (
            self._stem_match,
            self._translit_bridge,
            self._ethnonym_peel,
            self._substring_match,
        ):
            try:
                h = fn(token)
            except Exception:
                h = None
            if h is not None and h.score >= 0.68:
                tier_b.append(h)
        if tier_b:
            # prefer agreement: if two methods share meaning, boost
            by_m: Dict[str, List[OpenHit]] = defaultdict(list)
            for h in tier_b:
                by_m[h.meaning].append(h)
            best_m, group = max(by_m.items(), key=lambda kv: (len(kv[1]), max(x.score for x in kv[1])))
            best = max(group, key=lambda h: h.score)
            if len(group) >= 2:
                best = OpenHit(best.meaning, min(0.95, best.score + 0.06), best.method + "+agree", best.donor)
            if best.score >= 0.66 and not is_meta_meaning(best.meaning):
                return best
            if best.score >= 0.80:  # allow meta only when very strong
                return best
            return None

        # Tier C: noisy neighbors — only very high confidence content glosses
        if len(self.lex) > 50000:
            return None
        tier_c = []
        for fn in (self._prefix_match, self._ngram_knn):
            try:
                h = fn(token)
            except Exception:
                h = None
            if h is not None and h.score >= 0.78 and not is_meta_meaning(h.meaning):
                tier_c.append(h)
        if not tier_c:
            return None
        best = max(tier_c, key=lambda h: (h.score, content_score(h.meaning)))
        if best.score >= 0.80:
            return best
        return None
