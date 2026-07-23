#!/usr/bin/env python3
"""
Large translation accuracy + fluency battery for Protofluid.

Tracks:
  A) Sense interlingua — form → SENSE → form/meaning (identity)
  B) PFLT Python map/translate — densify surface path
  C) Curated multi-token fluency (English render quality)

Does NOT use NMT. Offline, deterministic, minutes not hours.
"""
from __future__ import annotations

import json
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
ADA_DATA = ROOT / "pflt-Ada" / "data"
REP = ROOT / "pflt-Ada" / "reports"
REP.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

# ---------------------------------------------------------------------------
# Curated gold: multi-lang + classical phrases (human-audited)
# ---------------------------------------------------------------------------
CURATED_SINGLE: List[Tuple[str, str, str, str]] = [
    # (src_lang, form, gold_en, tag)
    ("la", "aqua", "water", "core"),
    ("la", "manus", "hand", "core"),
    ("la", "lingua", "language", "core"),
    ("la", "verbum", "word", "core"),
    ("la", "deus", "god", "core"),
    ("la", "dea", "goddess", "core"),
    ("la", "rex", "king", "core"),
    ("la", "urbs", "city", "core"),
    ("la", "bellum", "war", "core"),
    ("la", "pax", "peace", "core"),
    ("la", "vita", "life", "core"),
    ("la", "mors", "death", "core"),
    ("la", "terra", "earth", "core"),
    ("la", "caelum", "sky", "core"),
    ("la", "sol", "sun", "core"),
    ("la", "luna", "moon", "core"),
    ("la", "ignis", "fire", "core"),
    ("la", "mare", "sea", "core"),
    ("la", "flumen", "river", "core"),
    ("la", "homo", "man", "core"),
    ("la", "mulier", "woman", "core"),
    ("la", "pater", "father", "core"),
    ("la", "mater", "mother", "core"),
    ("la", "filius", "son", "core"),
    ("la", "filia", "daughter", "core"),
    ("la", "amor", "love", "core"),
    ("la", "lex", "law", "core"),
    ("la", "nomen", "name", "core"),
    ("la", "tempus", "time", "core"),
    ("la", "locus", "place", "core"),
    ("la", "templum", "temple", "core"),
    ("la", "domus", "house", "core"),
    ("la", "via", "road", "core"),
    ("la", "sanguis", "blood", "core"),
    ("la", "cor", "heart", "core"),
    ("la", "oculus", "eye", "core"),
    ("la", "pes", "foot", "core"),
    ("la", "caput", "head", "core"),
    ("la", "corpus", "body", "core"),
    ("la", "vox", "voice", "core"),
    ("grc", "ὕδωρ", "water", "core"),
    ("grc", "χείρ", "hand", "core"),
    ("grc", "λόγος", "word", "core"),
    ("grc", "θεός", "god", "core"),
    ("grc", "πόλις", "city", "core"),
    ("grc", "βίος", "life", "core"),
    ("grc", "θάνατος", "death", "core"),
    ("grc", "γῆ", "earth", "core"),
    ("grc", "ἥλιος", "sun", "core"),
    ("grc", "σελήνη", "moon", "core"),
    ("grc", "πῦρ", "fire", "core"),
    ("grc", "θάλασσα", "sea", "core"),
    ("grc", "ἀνήρ", "man", "core"),
    ("grc", "γυνή", "woman", "core"),
    ("grc", "πατήρ", "father", "core"),
    ("grc", "μήτηρ", "mother", "core"),
    ("grc", "νόμος", "law", "core"),
    ("grc", "ὄνομα", "name", "core"),
    ("grc", "χρόνος", "time", "core"),
    ("de", "Wasser", "water", "modern"),
    ("de", "Hand", "hand", "modern"),
    ("de", "Sonne", "sun", "modern"),
    ("de", "Feuer", "fire", "modern"),
    ("de", "Katze", "cat", "modern"),
    ("de", "Zelle", "cell", "modern"),
    ("fr", "eau", "water", "modern"),
    ("fr", "main", "hand", "modern"),
    ("fr", "soleil", "sun", "modern"),
    ("fr", "feu", "fire", "modern"),
    ("fr", "chat", "cat", "modern"),
    ("fr", "cellule", "cell", "modern"),
    ("es", "agua", "water", "modern"),
    ("es", "mano", "hand", "modern"),
    ("es", "sol", "sun", "modern"),
    ("es", "fuego", "fire", "modern"),
    ("es", "gato", "cat", "modern"),
    ("en", "water", "water", "identity"),
    ("en", "hand", "hand", "identity"),
    ("en", "cat", "cat", "identity"),
    ("en", "cell", "cell", "identity"),
    ("en", "sun", "sun", "identity"),
    ("en", "fire", "fire", "identity"),
    ("en", "life", "life", "identity"),
    ("en", "law", "law", "identity"),
]

CURATED_PHRASES: List[Tuple[str, str, str, str]] = [
    # (src_lang, text, gold_en_space_joined, tag)
    ("la", "aqua manus", "water hand", "phrase"),
    ("la", "aqua lingua manus", "water language hand", "phrase"),
    ("la", "sol luna terra", "sun moon earth", "phrase"),
    ("la", "vita mors", "life death", "phrase"),
    ("la", "pater mater filius", "father mother son", "phrase"),
    ("la", "rex urbs bellum", "king city war", "phrase"),
    ("la", "deus dea templum", "god goddess temple", "phrase"),
    ("la", "ignis aqua terra", "fire water earth", "phrase"),
    ("la", "lex ius pax", "law law peace", "phrase"),  # ius→law
    ("la", "nomen verbum lingua", "name word language", "phrase"),
    ("la", "cor sanguis corpus", "heart blood body", "phrase"),
    ("la", "oculus manus pes", "eye hand foot", "phrase"),
    ("grc", "ὕδωρ πῦρ γῆ", "water fire earth", "phrase"),
    ("grc", "ἥλιος σελήνη", "sun moon", "phrase"),
    ("de", "Wasser Feuer Sonne", "water fire sun", "phrase"),
    ("de", "Katze Hand", "cat hand", "phrase"),
    ("fr", "eau feu soleil", "water fire sun", "phrase"),
    ("fr", "chat main", "cat hand", "phrase"),
    ("es", "agua fuego sol", "water fire sun", "phrase"),
    ("en", "water fire sun", "water fire sun", "phrase"),
    ("en", "cat cell hand", "cat cell hand", "phrase"),
    ("la", "homo mulier puer", "man woman boy", "phrase"),
    ("la", "mare flumen mons", "sea river mountain", "phrase"),
    ("la", "dies nox annus", "day night year", "phrase"),
    ("la", "amicus hostis populus", "friend enemy people", "phrase"),
]


def toks(t: str) -> List[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def norm_gloss(g: str) -> str:
    g = (g or "").strip().lower().replace("_", " ")
    g = re.sub(r"\s+", " ", g)
    # strip FSOT modulation tails
    g = g.split(" [s=")[0].split(" [fsot")[0].strip()
    return g


def exact_match(pred: str, gold: str) -> bool:
    p, g = norm_gloss(pred), norm_gloss(gold)
    if not p or not g:
        return False
    return p == g or p.replace(" ", "_") == g.replace(" ", "_")


def soft_match(pred: str, gold: str) -> bool:
    if exact_match(pred, gold):
        return True
    p, g = norm_gloss(pred), norm_gloss(gold)
    if not p or not g or p in {"unresolved", "generic_dynamics", "narrative_flow"}:
        return False
    if g in p or p in g:
        return True
    pt, gt = set(toks(p)), set(toks(g))
    if not gt:
        return False
    # token recall ≥ 0.5 and at least one content token
    inter = pt & gt
    if not inter:
        # stem prefix ≥4
        for a in pt:
            for b in gt:
                if len(a) >= 4 and len(b) >= 4 and (a[:4] == b[:4]):
                    return True
        return False
    return len(inter) / max(1, len(gt)) >= 0.5


def phrase_score(pred: str, gold: str) -> Dict[str, Any]:
    """Per-token alignment for multi-word gold."""
    gp = toks(gold)
    pp = toks(pred)
    if not gp:
        return {"exact": False, "soft": False, "token_recall": 0.0, "token_precision": 0.0}
    # greedy: each gold token matched if appears in pred tokens or soft
    hit = 0
    for g in gp:
        if g in pp:
            hit += 1
            continue
        if any(soft_match(p, g) for p in pp):
            hit += 1
    recall = hit / len(gp)
    prec = hit / max(1, len(pp)) if pp else 0.0
    return {
        "exact": exact_match(pred, gold),
        "soft": recall >= 0.67 or soft_match(pred, gold),
        "token_recall": round(recall, 4),
        "token_precision": round(prec, 4),
        "token_f1": round(
            (2 * prec * recall / (prec + recall)) if (prec + recall) > 0 else 0.0, 4
        ),
    }


# Fluency heuristics for English surface renders (not BLEU)
GARBAGE = re.compile(
    r"unresolved|generic_dynamics|narrative_flow|flowing_|unknown_|name_of_",
    re.I,
)
STOP = {
    "the",
    "a",
    "an",
    "of",
    "to",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "is",
    "are",
    "be",
}


def fluency_score(text: str) -> Dict[str, Any]:
    """
    Higher is better (0–1). Penalize unresolved shells, empty, junk, excess symbols.
    Reward readable alphanumeric words, reasonable length.
    """
    t = (text or "").strip()
    if not t:
        return {"score": 0.0, "issues": ["empty"]}
    issues: List[str] = []
    score = 1.0
    if GARBAGE.search(t):
        score -= 0.55
        issues.append("garbage_shell")
    words = toks(t)
    if not words:
        score -= 0.7
        issues.append("no_words")
        return {"score": max(0.0, score), "issues": issues, "n_words": 0}
    # non-alpha ratio in raw
    alpha = sum(c.isalpha() or c.isspace() for c in t)
    if len(t) > 0 and alpha / len(t) < 0.55:
        score -= 0.25
        issues.append("low_alpha")
    # very long single tokens (encyclopedia dump)
    if any(len(w) > 40 for w in words):
        score -= 0.2
        issues.append("overlong_token")
    # all stopwords
    content = [w for w in words if w not in STOP]
    if words and not content:
        score -= 0.15
        issues.append("stopwords_only")
    # repeated identical tokens dominate
    if len(words) >= 3:
        top = Counter(words).most_common(1)[0][1]
        if top / len(words) > 0.7:
            score -= 0.15
            issues.append("repetition")
    # FSOT tail is fine but strip for display length
    if len(words) > 40:
        score -= 0.1
        issues.append("verbose")
    return {
        "score": round(max(0.0, min(1.0, score)), 4),
        "issues": issues,
        "n_words": len(words),
        "content_words": len(content),
    }


def load_eval_sample(max_n: int = 3000, seed: int = 42) -> List[Dict[str, str]]:
    path = ADA_DATA / "eval_sample.tsv"
    rows: List[Dict[str, str]] = []
    if not path.exists():
        return rows
    rng = random.Random(seed)
    all_rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            lang, form, gold = parts[0], parts[1], parts[2]
            if not form or not gold or len(form) > 48:
                continue
            # skip pure noise
            if gold.lower() in {"", "?", "xxx"}:
                continue
            all_rows.append({"lang": lang, "form": form, "gold": gold, "tag": "heldout"})
    if len(all_rows) <= max_n:
        return all_rows
    return rng.sample(all_rows, max_n)


def load_form_sense(max_n: int = 1500) -> List[Dict[str, str]]:
    path = ADA_DATA / "form_sense.tsv"
    rows: List[Dict[str, str]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= max_n:
                break
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            form, gold = parts[0], parts[1]
            rows.append(
                {
                    "lang": "?",
                    "form": form,
                    "gold": gold,
                    "tag": "form_sense",
                }
            )
    return rows


@dataclass
class TrackStats:
    n: int = 0
    exact: int = 0
    soft: int = 0
    miss: int = 0
    fluency_sum: float = 0.0
    fluency_n: int = 0
    by_tag: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: Counter()))
    examples_miss: List[Dict[str, Any]] = field(default_factory=list)
    examples_ok: List[Dict[str, Any]] = field(default_factory=list)

    def add(
        self,
        *,
        exact: bool,
        soft: bool,
        fluency: float,
        tag: str,
        record: Dict[str, Any],
    ) -> None:
        self.n += 1
        if exact:
            self.exact += 1
            self.by_tag[tag]["exact"] += 1
        if soft:
            self.soft += 1
            self.by_tag[tag]["soft"] += 1
        if not soft:
            self.miss += 1
            self.by_tag[tag]["miss"] += 1
            if len(self.examples_miss) < 40:
                self.examples_miss.append(record)
        else:
            if exact and len(self.examples_ok) < 15:
                self.examples_ok.append(record)
        self.fluency_sum += fluency
        self.fluency_n += 1
        self.by_tag[tag]["n"] += 1

    def summary(self) -> Dict[str, Any]:
        n = max(1, self.n)
        return {
            "n": self.n,
            "exact": self.exact,
            "soft": self.soft,
            "miss": self.miss,
            "exact_rate": round(self.exact / n, 4),
            "soft_rate": round(self.soft / n, 4),
            "miss_rate": round(self.miss / n, 4),
            "mean_fluency": round(self.fluency_sum / max(1, self.fluency_n), 4),
            "by_tag": {k: dict(v) for k, v in self.by_tag.items()},
            "examples_miss": self.examples_miss[:25],
            "examples_ok": self.examples_ok[:10],
        }


def run_sense_track(items: Sequence[Dict[str, str]]) -> TrackStats:
    from sense_interlingua import SenseInterlingua

    ix = SenseInterlingua()
    st = TrackStats()
    for it in items:
        form = it["form"]
        gold = it["gold"]
        lang = it.get("lang") or None
        if lang == "?":
            lang = None
        hit = ix.resolve_form(form, lang)
        if hit is None:
            hit = ix.resolve_form(form, None)
        pred = hit.canonical_en if hit else "unresolved"
        fl = fluency_score(pred)
        ex = exact_match(pred, gold)
        sm = soft_match(pred, gold)
        st.add(
            exact=ex,
            soft=sm,
            fluency=fl["score"],
            tag=it.get("tag", "x"),
            record={
                "form": form,
                "lang": lang,
                "gold": gold,
                "pred": pred,
                "sense": hit.sense_id if hit else None,
                "fluency": fl["score"],
            },
        )
    return st


def run_sense_phrases(phrases: Sequence[Tuple[str, str, str, str]]) -> TrackStats:
    from sense_interlingua import SenseInterlingua

    ix = SenseInterlingua()
    st = TrackStats()
    for src, text, gold, tag in phrases:
        r = ix.translate(text, source_lang=src, target_lang="en")
        pred = " ".join(r.meanings_en)
        # also surface forms in en
        pred_forms = " ".join(r.target_forms)
        sc = phrase_score(pred, gold)
        # accept either meanings or target forms
        sc2 = phrase_score(pred_forms, gold)
        best_soft = sc["soft"] or sc2["soft"]
        best_exact = sc["exact"] or sc2["exact"]
        fl = fluency_score(pred if pred else pred_forms)
        st.add(
            exact=best_exact,
            soft=best_soft,
            fluency=fl["score"],
            tag=tag,
            record={
                "text": text,
                "src": src,
                "gold": gold,
                "pred_meanings": pred,
                "pred_forms": pred_forms,
                "token_f1": max(sc["token_f1"], sc2["token_f1"]),
                "exact_rate_tokens": r.exact_rate,
                "fluency": fl["score"],
                "S": r.fsot.get("S"),
            },
        )
    return st


def run_pflt_track(items: Sequence[Dict[str, str]], max_items: int = 2000) -> TrackStats:
    from PFLT_FSOT_2_1_aligned import PFLT

    eng = PFLT()
    st = TrackStats()
    for it in items[:max_items]:
        form = it["form"]
        gold = it["gold"]
        ctx = "historical" if it.get("lang") in {"la", "grc", "ang"} else "linguistic"
        try:
            meaning, exact_map = eng.map_token(form, ctx)
        except Exception as e:
            meaning, exact_map = f"error:{e}", False
        pred = meaning
        fl = fluency_score(pred)
        ex = exact_match(pred, gold)
        sm = soft_match(pred, gold) or (exact_map and soft_match(pred, gold))
        st.add(
            exact=ex,
            soft=sm,
            fluency=fl["score"],
            tag=it.get("tag", "x"),
            record={
                "form": form,
                "gold": gold,
                "pred": pred,
                "exact_map": exact_map,
                "fluency": fl["score"],
            },
        )
    return st


def load_densify_index(max_lines: int = 2_500_000) -> Dict[str, str]:
    """
    Build form→gloss index from Ada densify + gold packs (shipping inventory).
    Lowercased form keys. Stops early for memory if max_lines hit.
    """
    idx: Dict[str, str] = {}
    for name in ("densify.tsv", "gold_core.tsv"):
        path = ADA_DATA / name
        if not path.exists():
            continue
        n = 0
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if n >= max_lines:
                    break
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                # formats vary: form\\tgloss OR lang\\tform\\tgold
                if len(parts) >= 3 and len(parts[0]) <= 8:
                    form, gold = parts[1], parts[2]
                else:
                    form, gold = parts[0], parts[1]
                if not form or not gold:
                    continue
                k = form.strip().lower()
                if k not in idx:
                    idx[k] = gold.strip()
                n += 1
        print(f"  loaded {name}: +lines={n} index_size={len(idx)}", flush=True)
    return idx


def run_densify_track(
    items: Sequence[Dict[str, str]], index: Dict[str, str]
) -> TrackStats:
    st = TrackStats()
    for it in items:
        form = it["form"]
        gold = it["gold"]
        pred = index.get(form.lower()) or index.get(form) or "unresolved"
        fl = fluency_score(pred)
        st.add(
            exact=exact_match(pred, gold),
            soft=soft_match(pred, gold),
            fluency=fl["score"],
            tag=it.get("tag", "x"),
            record={
                "form": form,
                "gold": gold,
                "pred": pred[:120],
                "fluency": fl["score"],
                "hit": pred != "unresolved",
            },
        )
    return st


def run_pflt_phrases(phrases: Sequence[Tuple[str, str, str, str]]) -> TrackStats:
    from PFLT_FSOT_2_1_aligned import PFLT

    eng = PFLT()
    st = TrackStats()
    for src, text, gold, tag in phrases:
        ctx = "historical" if src in {"la", "grc", "ang"} else "linguistic"
        try:
            out = eng.translate(text, context=ctx, target_lang="english")
            meanings = out.get("meanings") or []
            pred = " ".join(m.split(" [S=")[0] for m in meanings)
            translation = out.get("translation") or pred
        except Exception as e:
            pred, translation = f"error:{e}", ""
            meanings = []
            out = {}
        sc = phrase_score(pred, gold)
        sc_t = phrase_score(translation, gold)
        best_soft = sc["soft"] or sc_t["soft"]
        best_exact = sc["exact"] or sc_t["exact"]
        fl = fluency_score(pred)
        st.add(
            exact=best_exact,
            soft=best_soft,
            fluency=fl["score"],
            tag=tag,
            record={
                "text": text,
                "gold": gold,
                "pred": pred,
                "translation": translation[:200],
                "map_rate": out.get("exact_map_rate"),
                "token_f1": max(sc["token_f1"], sc_t["token_f1"]),
                "fluency": fl["score"],
                "S": out.get("fsot_coherence_S"),
            },
        )
    return st


def main() -> None:
    t0 = time.perf_counter()
    print("=== Protofluid large translation battery ===", flush=True)

    curated_items = [
        {"lang": la, "form": form, "gold": gold, "tag": tag}
        for la, form, gold, tag in CURATED_SINGLE
    ]
    heldout = load_eval_sample(3000, seed=7)
    form_sense = load_form_sense(1500)
    print(
        f"curated_single={len(curated_items)} heldout={len(heldout)} "
        f"form_sense={len(form_sense)} phrases={len(CURATED_PHRASES)}",
        flush=True,
    )

    # Sense: curated + phrases + sample of heldout/form_sense
    print("--- sense interlingua ---", flush=True)
    sense_cur = run_sense_track(curated_items)
    sense_ph = run_sense_phrases(CURATED_PHRASES)
    sense_ho = run_sense_track(heldout[:2000])
    sense_fs = run_sense_track(form_sense[:1000])

    # PFLT: curated + phrases + heldout sample (seed lexicon only — not densify)
    print("--- PFLT map/translate (seed lexicon) ---", flush=True)
    pflt_cur = run_pflt_track(curated_items)
    pflt_ph = run_pflt_phrases(CURATED_PHRASES)
    pflt_ho = run_pflt_track(heldout, max_items=2000)

    # Densify inventory = Ada shipping store (fair held-out coverage measure)
    print("--- densify/gold index (Ada packs) ---", flush=True)
    dens_idx = load_densify_index(2_000_000)
    dens_cur = run_densify_track(curated_items, dens_idx)
    dens_ho = run_densify_track(heldout[:3000], dens_idx)
    dens_fs = run_densify_track(form_sense[:1500], dens_idx)

    # Combined mega-score: soft accuracy weighted
    def pack(name: str, st: TrackStats) -> Dict[str, Any]:
        s = st.summary()
        s["track"] = name
        return s

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "Large accuracy + fluency battery (sense identity + PFLT surface)",
        "protocol": {
            "exact": "normalized string equality to gold English gloss",
            "soft": "substring / token recall≥0.5 / stem-4 / phrase token F1 proxy",
            "fluency": "0–1 heuristic: penalize unresolved shells, junk, non-alpha, dumps",
            "not_used": "NMT, QLoRA, BLEU as primary product score",
        },
        "counts": {
            "curated_single": len(curated_items),
            "curated_phrases": len(CURATED_PHRASES),
            "heldout_sample": len(heldout),
            "form_sense_sample": len(form_sense),
            "sense_heldout_eval": min(2000, len(heldout)),
            "pflt_heldout_eval": min(2000, len(heldout)),
            "densify_index_size": len(dens_idx),
            "densify_heldout_eval": min(3000, len(heldout)),
        },
        "tracks": {
            "sense_curated_single": pack("sense_curated_single", sense_cur),
            "sense_curated_phrases": pack("sense_curated_phrases", sense_ph),
            "sense_heldout_2k": pack("sense_heldout_2k", sense_ho),
            "sense_form_sense_1k": pack("sense_form_sense_1k", sense_fs),
            "pflt_curated_single": pack("pflt_curated_single", pflt_cur),
            "pflt_curated_phrases": pack("pflt_curated_phrases", pflt_ph),
            "pflt_heldout_2k_seed_only": pack("pflt_heldout_2k_seed_only", pflt_ho),
            "densify_curated": pack("densify_curated", dens_cur),
            "densify_heldout_3k": pack("densify_heldout_3k", dens_ho),
            "densify_form_sense_1.5k": pack("densify_form_sense_1.5k", dens_fs),
        },
        "headline": {},
        "prior_ada_eval": {
            "open_set_partial": 0.9771,
            "product_partial": 0.8983,
            "open_set_exact": 0.9755,
            "product_exact": 0.8951,
            "n": 8000,
            "note": "Ada binary eval 2026-07-23 (train_mass / gold+densify)",
        },
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }

    # Headlines
    report["headline"] = {
        "sense_curated_exact_pct": round(100 * sense_cur.summary()["exact_rate"], 2),
        "sense_curated_soft_pct": round(100 * sense_cur.summary()["soft_rate"], 2),
        "sense_phrase_soft_pct": round(100 * sense_ph.summary()["soft_rate"], 2),
        "sense_phrase_mean_fluency": sense_ph.summary()["mean_fluency"],
        "sense_heldout_soft_pct": round(100 * sense_ho.summary()["soft_rate"], 2),
        "pflt_curated_exact_pct": round(100 * pflt_cur.summary()["exact_rate"], 2),
        "pflt_curated_soft_pct": round(100 * pflt_cur.summary()["soft_rate"], 2),
        "pflt_phrase_soft_pct": round(100 * pflt_ph.summary()["soft_rate"], 2),
        "pflt_phrase_mean_fluency": pflt_ph.summary()["mean_fluency"],
        "pflt_heldout_seed_soft_pct": round(100 * pflt_ho.summary()["soft_rate"], 2),
        "densify_curated_soft_pct": round(100 * dens_cur.summary()["soft_rate"], 2),
        "densify_heldout_soft_pct": round(100 * dens_ho.summary()["soft_rate"], 2),
        "densify_heldout_exact_pct": round(100 * dens_ho.summary()["exact_rate"], 2),
        "densify_heldout_mean_fluency": dens_ho.summary()["mean_fluency"],
        "densify_form_sense_soft_pct": round(100 * dens_fs.summary()["soft_rate"], 2),
        "ada_open_set_partial_pct": 97.71,
        "ada_product_partial_pct": 89.83,
        "queries_total_approx": (
            sense_cur.n
            + sense_ph.n
            + sense_ho.n
            + sense_fs.n
            + pflt_cur.n
            + pflt_ph.n
            + pflt_ho.n
            + dens_cur.n
            + dens_ho.n
            + dens_fs.n
        ),
    }

    out_json = REP / "TRANSLATION_BATTERY.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    h = report["headline"]
    md = f"""# Translation accuracy & fluency battery

**Built:** {report['built_utc']}  
**Elapsed:** {report['elapsed_s']}s  
**Queries scored (all tracks):** ~{h.get('queries_total_approx')}  
**Law:** FSOT pin D1D38A · no NMT  

## Headlines

| Track | Exact % | Soft/Partial % | Mean fluency (0–1) |
|-------|--------:|---------------:|-------------------:|
| Sense curated single (n={sense_cur.n}) | **{h['sense_curated_exact_pct']}** | **{h['sense_curated_soft_pct']}** | {sense_cur.summary()['mean_fluency']} |
| Sense curated phrases (n={sense_ph.n}) | {round(100*sense_ph.summary()['exact_rate'],2)} | **{h['sense_phrase_soft_pct']}** | **{h['sense_phrase_mean_fluency']}** |
| Sense held-out 2k (thin graph) | {round(100*sense_ho.summary()['exact_rate'],2)} | {h['sense_heldout_soft_pct']} | {sense_ho.summary()['mean_fluency']} |
| Densify curated (Ada packs) | {round(100*dens_cur.summary()['exact_rate'],2)} | **{h['densify_curated_soft_pct']}** | {dens_cur.summary()['mean_fluency']} |
| **Densify held-out 3k (Ada packs)** | **{h['densify_heldout_exact_pct']}** | **{h['densify_heldout_soft_pct']}** | **{h['densify_heldout_mean_fluency']}** |
| Densify form_sense 1.5k | {round(100*dens_fs.summary()['exact_rate'],2)} | **{h['densify_form_sense_soft_pct']}** | {dens_fs.summary()['mean_fluency']} |
| PFLT curated single (seed lex) | **{h['pflt_curated_exact_pct']}** | **{h['pflt_curated_soft_pct']}** | {pflt_cur.summary()['mean_fluency']} |
| PFLT curated phrases | {round(100*pflt_ph.summary()['exact_rate'],2)} | **{h['pflt_phrase_soft_pct']}** | **{h['pflt_phrase_mean_fluency']}** |
| PFLT held-out seed-only (no densify) | {round(100*pflt_ho.summary()['exact_rate'],2)} | {h['pflt_heldout_seed_soft_pct']} | {pflt_ho.summary()['mean_fluency']} |
| **Ada OPEN-SET binary (8k)** | 97.55 | **97.71** | — |
| **Ada PRODUCT binary (8k)** | 89.51 | **89.83** | — |

## Protocol

- **Exact:** normalized gold English gloss equality  
- **Soft:** gold in pred / token recall / stem-4 / phrase coverage  
- **Fluency:** heuristic 0–1 (penalize `unresolved`, garbage shells, non-alpha dumps)  
- **Densify track:** Ada `densify.tsv` + `gold_core.tsv` form→gloss index (shipping inventory)  
- **Not primary:** sacreBLEU / NMT paraphrase  

## Interpretation

1. **Curated core + phrases** — meaning identity (*aqua*≡*water*) and multi-token fluency.  
2. **Densify held-out** — fair inventory accuracy (same packs as Ada product).  
3. **Sense held-out low** — sense graph is intentionally sparse (expand by binding, not NMT).  
4. **PFLT seed-only held-out low** — expected without loading densify packs.  
5. **Ada binary eval** remains the shipping morph/product bar.

## Sample misses

### Sense curated
```json
{json.dumps(sense_cur.summary().get('examples_miss', [])[:8], ensure_ascii=False, indent=2)}
```

### Densify held-out
```json
{json.dumps(dens_ho.summary().get('examples_miss', [])[:12], ensure_ascii=False, indent=2)}
```

## Reproduce

```powershell
cd C:\\Users\\damia\\Desktop\\pflt
python -u eval_translation_battery.py
```

JSON: `pflt-Ada/reports/TRANSLATION_BATTERY.json`
"""
    out_md = REP / "TRANSLATION_BATTERY.md"
    out_md.write_text(md, encoding="utf-8")
    # also docs
    docs = ROOT / "docs" / "TRANSLATION_BATTERY.md"
    docs.write_text(md, encoding="utf-8")

    print(json.dumps(report["headline"], indent=2), flush=True)
    print(f"elapsed {report['elapsed_s']}s", flush=True)
    print(f"WROTE {out_json}", flush=True)
    print(f"WROTE {out_md}", flush=True)


if __name__ == "__main__":
    main()
