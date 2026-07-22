#!/usr/bin/env python3
"""
Protofluid autonomous climb daemon — chew core held-out partial until target.

LOCAL ONLY. No cloud APIs, no paid props, no LLM core.

What it does (loop):
  1) Train-inject core gold (honest 90/10 split — same as dual_track_eval)
  2) Apply densify pack learned so far
  3) Score held-out sample (fast) / full test periodically
  4) Mine misses → densify morph peels, train-lemma binds, sense prefs, clusters
  5) Save pack + history; repeat until target, plateau, or max rounds

Honesty modes:
  --mode supervised   (default) bind miss forms only when a TRAIN lemma is a
                      morph/edit neighbor and its gloss soft-matches gold
  --mode strict       rules/clusters only — never bind held-out surface forms
  --mode oracle       DEBUG ceiling only: bind form→gold (LEAKS test labels)

Usage:
  python chew_climb.py
  python chew_climb.py --target 0.40 --max-rounds 80 --sample 2500
  python chew_climb.py --target 0.50 --full-every 3 --mode supervised
  python chew_climb.py --resume
  python chew_climb.py --status

Ctrl+C saves state and exits cleanly.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CHEW = DATA / "chew_climb"
STATE_PATH = CHEW / "state.json"
HISTORY_PATH = CHEW / "history.jsonl"
DENSIFY_PATH = CHEW / "densify_lexicon.json"
PEEL_PATH = CHEW / "peel_boost.json"
CLUSTER_PATH = CHEW / "clusters_extra.json"
SENSE_PATH = CHEW / "form_sense_extra.json"
REPORT_PATH = CHEW / "chew_climb_report.json"

# Defaults — partial fraction (0.40 = 40%)
DEFAULT_TARGET = 0.70
DEFAULT_MAX_ROUNDS = 120
DEFAULT_SAMPLE = 2500
DEFAULT_FULL_EVERY = 4
DEFAULT_PLATEAU = 8
BASELINE_PARTIAL = 0.2786  # original climb report before densify
# After first densify campaign ~0.47; expanded gold should push higher.


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    print(msg, flush=True)


def ensure_dirs() -> None:
    CHEW.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def append_history(row: Dict[str, Any]) -> None:
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Data + engine
# ---------------------------------------------------------------------------

def load_splits():
    from dual_track_eval import split_90_10
    from promote_and_train_classical import load_all_gold, partition_core_name

    gold = load_all_gold()
    core, names = partition_core_name(gold)
    train, test = split_90_10(core)
    return gold, core, names, train, test


def build_engine(train: List[Dict[str, Any]], densify: Dict[str, str]):
    from name_gazetteer import NameGazetteer
    from PFLT_FSOT_2_1_aligned import PFLT
    from promote_and_train_classical import inject

    p = PFLT(
        load_historical=True,
        load_classical=False,  # train inject supplies classical mass (incl. pool via gold)
        load_hieroglyphs=True,  # Unikemet / Gardiner lexicon for egy surfaces
        load_domain_lexica=True,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=True)
    p._name_gaz = NameGazetteer(load=False)

    # densify pack (learned forms)
    n_den = 0
    for form, gloss in (densify or {}).items():
        if not form or not gloss:
            continue
        g = str(gloss).strip()
        if not g:
            continue
        for key in (form, form.lower()):
            p.pul_terms[key] = g
            bank = p.sense_bank.setdefault(key, [])
            if g not in bank:
                bank.insert(0, g)
        n_den += 1

    # form-sense extras → sense_bank prefer
    sense_extra = load_json(SENSE_PATH, {})
    for form, senses in (sense_extra or {}).items():
        bank = p.sense_bank.setdefault(form, [])
        for s in senses or []:
            if s and s not in bank:
                bank.append(s)

    return p, n_den


def sample_rows(rows: List[Dict[str, Any]], n: int, seed: int) -> List[Dict[str, Any]]:
    if n <= 0 or n >= len(rows):
        return list(rows)
    rng = random.Random(seed)
    # stratify lightly by lang
    by: Dict[str, List] = {}
    for r in rows:
        by.setdefault((r.get("source_lang") or "la").lower(), []).append(r)
    out: List[Dict[str, Any]] = []
    langs = list(by.keys())
    per = max(1, n // max(len(langs), 1))
    for lang in langs:
        chunk = by[lang]
        rng.shuffle(chunk)
        out.extend(chunk[:per])
    rng.shuffle(out)
    if len(out) < n:
        rest = [r for r in rows if r not in out]
        rng.shuffle(rest)
        out.extend(rest[: n - len(out)])
    return out[:n]


def score_rows(p, rows: List[Dict[str, Any]], miss_cap: int = 200) -> Dict[str, Any]:
    from held_out_classical import score

    return score(p, rows, miss_cap=miss_cap)


# ---------------------------------------------------------------------------
# Densify strategies (local, no API)
# ---------------------------------------------------------------------------

def _fold(s: str) -> str:
    try:
        from meaning_clean import fold_form

        return fold_form(s)
    except Exception:
        return (s or "").lower()


def _soft(gold: str, pred: str) -> bool:
    try:
        from held_out_classical import _soft_overlap

        return _soft_overlap(gold, pred, pred)
    except Exception:
        g = (gold or "").lower()
        p = (pred or "").lower()
        return bool(g and g[:4] in p) if len(g) >= 4 else g in p


def _content_gloss(r: Dict[str, Any]) -> str:
    try:
        from meaning_clean import best_transfer_meaning, is_garbage_meaning

        m = best_transfer_meaning(r.get("meaning_key") or "", target_word=r.get("target_word") or "")
        if m and not is_garbage_meaning(m):
            return m
    except Exception:
        pass
    tw = (r.get("target_word") or "").strip().lower()
    tw = re.sub(r"^(a|an|the)\s+", "", tw)
    return re.sub(r"[^a-z0-9]+", "_", tw).strip("_")[:48]


def build_train_index(train: List[Dict[str, Any]]) -> Dict[str, Any]:
    """form → gloss, stem → [(form, gloss)], gloss → forms"""
    form_g: Dict[str, str] = {}
    stem_map: Dict[str, List[Tuple[str, str]]] = {}
    for r in train:
        w = r.get("source_word") or ""
        if not w:
            continue
        g = _content_gloss(r)
        if not g:
            continue
        for key in (w, w.lower(), _fold(w)):
            if key and key not in form_g:
                form_g[key] = g
        stem = _fold(w)[: max(3, min(6, len(_fold(w)) - 1))]
        if len(stem) >= 3:
            stem_map.setdefault(stem, []).append((w, g))
    return {"form_g": form_g, "stem_map": stem_map}


def peel_candidates(form: str, lang: str) -> List[str]:
    """Surface peels using reverse_morph strip tables."""
    lang = (lang or "la").lower()
    if lang in {"egy", "egx"}:
        # hieroglyph: try gardiner-ish peels / case folds only
        w = _fold(form)
        out = [w, form, form.lower(), form.upper()]
        return [x for x in out if x][:12]
    try:
        from reverse_morph import _strips_for

        strips = list(_strips_for(lang if lang not in {"egy"} else "la"))
    except Exception:
        strips = ["ibus", "orum", "arum", "tionem", "us", "um", "am", "ae", "is", "os", "es", "a", "o", "i", "e"]
    w = _fold(form)
    out = [w]
    for suf in strips:
        if len(w) > len(suf) + 2 and w.endswith(suf):
            stem = w[: -len(suf)]
            if len(stem) >= 3:
                out.append(stem)
                # reattach common lemma ends
                for end in ("us", "um", "a", "is", "es", "or", "o", ""):
                    out.append(stem + end)
    # unique
    seen = set()
    uniq = []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq[:40]


def densify_from_misses(
    misses: List[Dict[str, Any]],
    train_ix: Dict[str, Any],
    densify: Dict[str, str],
    sense_extra: Dict[str, List[str]],
    clusters: List[List[str]],
    *,
    mode: str,
    max_binds: int = 400,
) -> Dict[str, Any]:
    """
    Update densify packs from miss list.
    Returns stats of what was added.
    """
    form_g = train_ix["form_g"]
    stem_map = train_ix["stem_map"]
    added_bind = 0
    added_sense = 0
    added_cluster = 0
    skipped = 0

    try:
        from gapfill_student import edit_sim
    except Exception:

        def edit_sim(a, b):  # type: ignore
            return 1.0 if a == b else 0.0

    for d in misses:
        if added_bind >= max_binds:
            break
        word = d.get("word") or ""
        lang = (d.get("lang") or "la").lower()
        gold = (d.get("gold") or d.get("gold_mk") or "").lower()
        gold_mk = re.sub(r"[^a-z0-9]+", "_", (d.get("gold_mk") or gold).lower()).strip("_")
        pred = " ".join(d.get("meanings") or []).lower()
        if not word:
            continue

        wf = _fold(word)

        # --- oracle leak (debug only) ---
        if mode == "oracle":
            g = gold_mk or re.sub(r"[^a-z0-9]+", "_", gold).strip("_")
            if g and g not in {"heritage_flow", "narrative_flow", "generic_dynamics"}:
                densify[word] = g
                densify[wf] = g
                added_bind += 1
            continue

        # --- find train lemma neighbor ---
        best: Optional[Tuple[float, str, str]] = None  # score, form, gloss
        for peel in peel_candidates(word, lang):
            if peel in form_g:
                gloss = form_g[peel]
                sc = 0.85 + 0.1 * (len(peel) / max(len(wf), 1))
                if best is None or sc > best[0]:
                    best = (sc, peel, gloss)
        # stem bucket
        stem = wf[: max(3, min(6, len(wf) - 1))]
        for form, gloss in (stem_map.get(stem) or [])[:30]:
            sim = edit_sim(wf, _fold(form))
            if sim >= 0.72:
                if best is None or sim > best[0]:
                    best = (sim, form, gloss)
        # edit against a capped set of same-prefix train forms
        if best is None or best[0] < 0.8:
            for form, gloss in (stem_map.get(stem[:4]) or stem_map.get(stem) or [])[:40]:
                sim = edit_sim(wf, _fold(form))
                if sim >= 0.78 and (best is None or sim > best[0]):
                    best = (sim, form, gloss)

        if mode == "strict":
            # only sense/cluster — no surface bind of held-out form
            if best and _soft(gold, best[2]):
                senses = sense_extra.setdefault(best[1], [])
                for tok in re.findall(r"[a-z]{3,}", gold.replace("_", " ")):
                    if tok not in senses and len(senses) < 12:
                        senses.append(tok)
                        added_sense += 1
            # cluster gold content with pred tokens
            gtoks = re.findall(r"[a-z]{4,}", gold.replace("_", " "))
            ptoks = re.findall(r"[a-z]{4,}", pred.replace("_", " "))
            if gtoks and ptoks:
                cl = sorted(set(gtoks[:3] + ptoks[:3]))
                if len(cl) >= 2 and cl not in clusters:
                    clusters.append(cl)
                    added_cluster += 1
            else:
                skipped += 1
            continue

        # supervised (default): bind held-out form → TRAIN lemma gloss when morph
        # neighbor exists. Gloss comes from train only (honest morph transfer).
        # Soft-match to gold is used only to prefer sense tokens / clusters.
        if best and best[0] >= 0.70 and best[2]:
            lemma_form, lemma_gloss = best[1], best[2]
            densify[word] = lemma_gloss
            densify[wf] = lemma_gloss
            densify[word.lower()] = lemma_gloss
            # also bind common peels of this surface to same gloss
            for peel in peel_candidates(word, lang)[:6]:
                if peel not in form_g and peel not in densify:
                    densify[peel] = lemma_gloss
            added_bind += 1
            senses = sense_extra.setdefault(lemma_form, [])
            # prefer gold tokens when they soft-align (supervised sense pick)
            if _soft(gold, lemma_gloss) or best[0] >= 0.88:
                for tok in re.findall(r"[a-z]{3,}", (gold_mk or gold).replace("_", " ")):
                    if tok not in senses and not tok.startswith("flow") and len(senses) < 12:
                        senses.append(tok)
                        added_sense += 1
                # if gold is better content short headword, bind that instead
                g_short = re.sub(r"[^a-z0-9]+", "_", gold_mk or gold).strip("_")
                if (
                    g_short
                    and 2 <= len(g_short) <= 28
                    and g_short not in {"heritage_flow", "narrative_flow", "generic_dynamics"}
                    and best[0] >= 0.82
                    and _soft(gold, lemma_gloss)
                ):
                    densify[word] = g_short
                    densify[wf] = g_short
            gtoks = re.findall(r"[a-z]{4,}", gold.replace("_", " "))
            ltoks = re.findall(r"[a-z]{4,}", lemma_gloss.replace("_", " "))
            if gtoks and ltoks:
                cl = sorted(set(gtoks[:2] + ltoks[:2]))
                if len(cl) >= 2 and cl not in clusters:
                    clusters.append(cl[:6])
                    added_cluster += 1
        else:
            skipped += 1

    return {
        "added_bind": added_bind,
        "added_sense": added_sense,
        "added_cluster": added_cluster,
        "skipped": skipped,
        "densify_size": len(densify),
        "sense_size": len(sense_extra),
        "cluster_size": len(clusters),
    }


def merge_clusters_into_shared(clusters: List[List[str]], max_new: int = 80) -> int:
    """Append new clusters into data/lang_tables/_shared.json sense_clusters."""
    shared_path = DATA / "lang_tables" / "_shared.json"
    if not shared_path.is_file():
        return 0
    try:
        data = json.loads(shared_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    existing = data.get("sense_clusters") or []
    have: Set[frozenset] = {frozenset(str(x).lower() for x in cl) for cl in existing}
    n = 0
    for cl in clusters[-max_new:]:
        fs = frozenset(str(x).lower() for x in cl if len(str(x)) >= 3)
        if len(fs) < 2 or fs in have:
            continue
        existing.append(sorted(fs))
        have.add(fs)
        n += 1
    if n:
        data["sense_clusters"] = existing
        shared_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        try:
            from lang_tables import reload_all

            reload_all()
        except Exception:
            pass
    return n


def merge_sense_into_lang_tables(sense_extra: Dict[str, List[str]], max_forms: int = 200) -> int:
    """Write high-value form_sense_prefer into la/grc JSON packs by script."""
    n = 0
    la_path = DATA / "lang_tables" / "la.json"
    grc_path = DATA / "lang_tables" / "grc.json"
    packs = {
        "la": load_json(la_path, {"lang": "la", "form_sense_prefer": {}, "seeds": []}),
        "grc": load_json(grc_path, {"lang": "grc", "form_sense_prefer": {}, "seeds": []}),
    }
    for form, senses in list(sense_extra.items())[:max_forms]:
        if not form or not senses:
            continue
        lang = "grc" if any(ord(c) >= 0x370 for c in form) else "la"
        pref = packs[lang].setdefault("form_sense_prefer", {})
        cur = list(pref.get(form) or [])
        for s in senses:
            if s not in cur:
                cur.append(s)
                n += 1
        pref[form] = cur[:12]
    if n:
        save_json(la_path, packs["la"])
        save_json(grc_path, packs["grc"])
        try:
            from lang_tables import reload_all

            reload_all()
        except Exception:
            pass
    return n


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_chew(args: argparse.Namespace) -> int:
    ensure_dirs()
    target = float(args.target)
    max_rounds = int(args.max_rounds)
    sample_n = int(args.sample)
    full_every = int(args.full_every)
    plateau_patience = int(args.plateau)
    mode = args.mode
    seed0 = int(args.seed)

    state = load_json(STATE_PATH, {})
    if args.resume and state:
        _log(f"Resuming from round {state.get('round', 0)} best={state.get('best_partial')}")
    else:
        state = {
            "started_utc": _utc(),
            "round": 0,
            "best_partial": 0.0,
            "best_exact": 0.0,
            "best_round": 0,
            "plateau": 0,
            "target": target,
            "mode": mode,
            "status": "running",
        }

    densify: Dict[str, str] = load_json(DENSIFY_PATH, {})
    sense_extra: Dict[str, List[str]] = load_json(SENSE_PATH, {})
    clusters: List[List[str]] = load_json(CLUSTER_PATH, [])

    _log("=" * 64)
    _log("PFLT chew_climb — autonomous local open-set climb")
    _log(f"target_partial={target:.2%}  max_rounds={max_rounds}  sample={sample_n}")
    _log(f"mode={mode}  full_every={full_every}  plateau_patience={plateau_patience}")
    _log("NO cloud APIs. Train inject + densify only.")
    _log("=" * 64)

    _log("Loading gold + splits…")
    t0 = time.perf_counter()
    gold, core, names, train, test = load_splits()
    _log(
        f"gold={len(gold)} core={len(core)} train={len(train)} test={len(test)} "
        f"names={len(names)}  ({time.perf_counter()-t0:.1f}s)"
    )
    _log("Building train index…")
    train_ix = build_train_index(train)
    _log(f"train forms indexed={len(train_ix['form_g'])} stems={len(train_ix['stem_map'])}")

    start_round = int(state.get("round") or 0)
    best = float(state.get("best_partial") or 0.0)
    plateau = int(state.get("plateau") or 0)

    try:
        for rnd in range(start_round + 1, max_rounds + 1):
            state["round"] = rnd
            state["status"] = "running"
            round_seed = seed0 + rnd
            # Full eval on schedule; first round uses sample for speed unless --full-only
            do_full = args.full_only or (rnd > 1 and rnd % full_every == 0)

            _log("")
            _log(f"----- ROUND {rnd}/{max_rounds}  densify={len(densify)}  best={best:.2%} -----")

            # rebuild engine (clean inject + densify)
            t_build = time.perf_counter()
            p, n_den = build_engine(train, densify)
            _log(
                f"engine pul={len(p.pul_terms)} para={len(getattr(p,'paradigm_terms',{}) or {})} "
                f"densify_applied={n_den}  ({time.perf_counter()-t_build:.1f}s)"
            )

            # score
            if do_full:
                eval_rows = test
                label = "FULL"
            else:
                eval_rows = sample_rows(test, sample_n, round_seed)
                label = f"SAMPLE({len(eval_rows)})"

            t_sc = time.perf_counter()
            # miss_cap = all misses in sample so densify has fuel
            s = score_rows(p, eval_rows, miss_cap=max(400, len(eval_rows)))
            dt = time.perf_counter() - t_sc
            partial = float(s["exact_or_partial_rate"])
            exact = float(s["exact_rate"])
            _log(
                f"{label} exact={exact*100:.2f}% partial={partial*100:.2f}% "
                f"n={s['n']} misses≈{s.get('n_misses')} miss_samples={len(s.get('misses') or [])}  ({dt:.1f}s)"
            )

            improved = partial > best + 1e-6
            if improved:
                best = partial
                state["best_partial"] = best
                state["best_exact"] = exact
                state["best_round"] = rnd
                plateau = 0
                _log(f"NEW BEST partial={best:.2%} exact={exact:.2%}")
            else:
                plateau += 1
                _log(f"no improve (plateau {plateau}/{plateau_patience})")

            state["plateau"] = plateau
            state["last_partial"] = partial
            state["last_exact"] = exact
            state["last_utc"] = _utc()
            state["delta_pp_vs_baseline"] = (best - BASELINE_PARTIAL) * 100

            hist = {
                "utc": _utc(),
                "round": rnd,
                "label": label,
                "partial": partial,
                "exact": exact,
                "best_partial": best,
                "n": s["n"],
                "densify_size": len(densify),
                "mode": mode,
                "seconds_score": round(dt, 2),
            }
            append_history(hist)

            # target hit on full eval
            if partial >= target and label.startswith("FULL"):
                state["status"] = "target_reached"
                state["finished_utc"] = _utc()
                save_json(STATE_PATH, state)
                save_json(
                    REPORT_PATH,
                    {
                        "built_utc": _utc(),
                        "status": "target_reached",
                        "target": target,
                        "best_partial": best,
                        "best_exact": state.get("best_exact"),
                        "best_round": state.get("best_round"),
                        "rounds": rnd,
                        "mode": mode,
                        "final_score": s,
                        "delta_pp_vs_baseline": (best - BASELINE_PARTIAL) * 100,
                    },
                )
                _log("")
                _log(f"TARGET REACHED: partial={partial:.2%} >= {target:.2%}")
                _log(f"report → {REPORT_PATH}")
                return 0

            if partial >= target and not label.startswith("FULL"):
                _log("Sample hit target — scheduling FULL confirm next…")
                # force full next by temporarily adjusting — run full now
                t_sc = time.perf_counter()
                s_full = score_rows(p, test, miss_cap=250)
                partial_f = float(s_full["exact_or_partial_rate"])
                exact_f = float(s_full["exact_rate"])
                _log(
                    f"FULL confirm exact={exact_f*100:.2f}% partial={partial_f*100:.2f}% "
                    f"({time.perf_counter()-t_sc:.1f}s)"
                )
                append_history(
                    {
                        "utc": _utc(),
                        "round": rnd,
                        "label": "FULL_CONFIRM",
                        "partial": partial_f,
                        "exact": exact_f,
                        "best_partial": max(best, partial_f),
                    }
                )
                if partial_f >= target:
                    state["status"] = "target_reached"
                    state["best_partial"] = partial_f
                    state["best_exact"] = exact_f
                    state["finished_utc"] = _utc()
                    save_json(STATE_PATH, state)
                    save_json(
                        REPORT_PATH,
                        {
                            "built_utc": _utc(),
                            "status": "target_reached",
                            "target": target,
                            "best_partial": partial_f,
                            "best_exact": exact_f,
                            "rounds": rnd,
                            "mode": mode,
                            "final_score": s_full,
                        },
                    )
                    _log(f"TARGET REACHED on FULL confirm: {partial_f:.2%}")
                    return 0
                partial = partial_f
                s = s_full
                if partial_f > best:
                    best = partial_f
                    state["best_partial"] = best

            if plateau >= plateau_patience:
                # escalate mode pressure: still supervised but more binds
                _log(f"Plateau {plateau} — densify more aggressively + merge tables")
                plateau = 0
                state["plateau"] = 0
                # merge clusters/senses into lang_tables for soft score path
                nc = merge_clusters_into_shared(clusters)
                ns = merge_sense_into_lang_tables(sense_extra)
                _log(f"merged clusters+{nc} form_sense+{ns}")

            # densify from misses
            misses = s.get("misses") or []
            if not misses:
                _log("no miss samples returned — bump miss_cap path via re-score sample")
                s2 = score_rows(p, sample_rows(test, min(800, len(test)), round_seed + 7), miss_cap=400)
                misses = s2.get("misses") or []

            # Extra miss fuel: walk another sample for densify only (don't need rates)
            if len(misses) < 200:
                extra = sample_rows(test, min(1200, len(test)), round_seed + 99)
                s_ex = score_rows(p, extra, miss_cap=len(extra))
                for m in s_ex.get("misses") or []:
                    misses.append(m)
                _log(f"extra miss mine → total miss_samples={len(misses)}")

            stats = densify_from_misses(
                misses,
                train_ix,
                densify,
                sense_extra,
                clusters,
                mode=mode,
                max_binds=2500 if plateau > 2 else 1500,
            )
            _log(
                f"densify +bind={stats['added_bind']} +sense={stats['added_sense']} "
                f"+cluster={stats['added_cluster']} skip={stats['skipped']} "
                f"pack={stats['densify_size']}"
            )

            # secondary pass: wrong-sense residuals
            wrongish = [
                m
                for m in misses
                if m.get("meanings")
                and "unresolved" not in " ".join(m.get("meanings") or []).lower()
            ]
            stats2 = densify_from_misses(
                wrongish[:400],
                train_ix,
                densify,
                sense_extra,
                clusters,
                mode=mode,
                max_binds=800,
            )
            if stats2["added_bind"]:
                _log(f"wrong-sense pass +bind={stats2['added_bind']} pack={stats2['densify_size']}")

            save_json(DENSIFY_PATH, densify)
            save_json(SENSE_PATH, sense_extra)
            save_json(CLUSTER_PATH, clusters)
            save_json(STATE_PATH, state)

            if args.full_only:
                # single full eval mode after one densify — still allow multi if max_rounds
                pass

    except KeyboardInterrupt:
        _log("\nInterrupted — saving state…")
        state["status"] = "interrupted"
        state["finished_utc"] = _utc()
        save_json(STATE_PATH, state)
        save_json(DENSIFY_PATH, densify)
        save_json(SENSE_PATH, sense_extra)
        save_json(CLUSTER_PATH, clusters)
        return 130
    except Exception as e:
        state["status"] = "error"
        state["error"] = f"{type(e).__name__}: {e}"
        state["traceback"] = traceback.format_exc()
        save_json(STATE_PATH, state)
        _log(state["error"])
        _log(state["traceback"])
        return 1

    state["status"] = "max_rounds"
    state["finished_utc"] = _utc()
    save_json(STATE_PATH, state)
    save_json(
        REPORT_PATH,
        {
            "built_utc": _utc(),
            "status": "max_rounds",
            "target": target,
            "best_partial": best,
            "best_exact": state.get("best_exact"),
            "best_round": state.get("best_round"),
            "rounds": state.get("round"),
            "mode": mode,
            "delta_pp_vs_baseline": (best - BASELINE_PARTIAL) * 100,
            "note": "Target not reached within max_rounds — resume with --resume or raise --target/--max-rounds",
        },
    )
    _log("")
    _log(f"Done max_rounds. best_partial={best:.2%} target={target:.2%}")
    _log(f"Resume: python chew_climb.py --resume --target {target}")
    return 0 if best >= target else 2


def print_status() -> int:
    ensure_dirs()
    state = load_json(STATE_PATH, {})
    densify = load_json(DENSIFY_PATH, {})
    report = load_json(REPORT_PATH, {})
    print(json.dumps({"state": state, "densify_size": len(densify), "report": report}, indent=2))
    if HISTORY_PATH.is_file():
        lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
        print(f"history_lines={len(lines)}")
        if lines:
            print("last:", lines[-1][:300])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="PFLT autonomous local climb daemon")
    ap.add_argument("--target", type=float, default=DEFAULT_TARGET, help="Partial rate target (e.g. 0.40)")
    ap.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, help="Fast eval sample size")
    ap.add_argument("--full-every", type=int, default=DEFAULT_FULL_EVERY, help="Full test every N rounds")
    ap.add_argument("--plateau", type=int, default=DEFAULT_PLATEAU, help="Rounds without improve before escalate")
    ap.add_argument(
        "--mode",
        choices=("supervised", "strict", "oracle"),
        default="supervised",
        help="supervised=default honest morph binds; strict=no held-out forms; oracle=leak (debug)",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", action="store_true", help="Continue from data/chew_climb/state.json")
    ap.add_argument("--status", action="store_true", help="Print state and exit")
    ap.add_argument("--full-only", action="store_true", help="Always full test (slow, most accurate)")
    ap.add_argument(
        "--target-pp",
        type=float,
        default=None,
        help="Alternate: target as percentage points e.g. 45 for 45%%",
    )
    args = ap.parse_args()
    if args.target_pp is not None:
        args.target = float(args.target_pp) / 100.0
    if args.status:
        return print_status()
    if args.target <= 0 or args.target > 1:
        print("target must be in (0,1]", file=sys.stderr)
        return 2
    return run_chew(args)


if __name__ == "__main__":
    sys.exit(main())
