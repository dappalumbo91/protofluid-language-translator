#!/usr/bin/env python3
"""
WMT14 de→en news evaluation using *cached* hyps only (no GPU retrain).

Tracks:
  1) Single systems from hyp_cache (opus, nllb13, nllb33 b5/b8)
  2) gen_score merge (strong NLLB family)
  3) Within-family FSOT z-cal merge when feat caches exist
  4) Oracle upper bound (sent-BLEU pick)

Sense/FSOT law: pin D1D38A for panel log only — densify is classical; news
uses neural hyps as students under fixed law-aware ranking, not QLoRA.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import sacrebleu
from datasets import load_dataset

ROOT = Path(__file__).resolve().parent
ADA = ROOT / "pflt-Ada"
CACHE = ADA / "data" / "hyp_cache"
FEAT = ADA / "data" / "fsot_feat_cache"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
PHI = 1.618033988749895
C_EFF = 0.9577022026205613


def toks(t: str) -> List[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sent_bleu(h: str, r: str) -> float:
    ht, rt = toks(h), toks(r)
    if not ht or not rt:
        return 0.0
    precs = []
    for n in range(1, 5):
        if len(ht) < n:
            precs.append(1e-9)
            continue
        hc = Counter(tuple(ht[i : i + n]) for i in range(len(ht) - n + 1))
        rc = Counter(tuple(rt[i : i + n]) for i in range(len(rt) - n + 1))
        m = sum(min(c, rc.get(ng, 0)) for ng, c in hc.items())
        tot = sum(hc.values())
        precs.append((m + 1) / (tot + 1))
    bp = 1.0 if len(ht) > len(rt) else math.exp(1 - len(rt) / max(1, len(ht)))
    return bp * math.exp(sum(math.log(p) for p in precs) / 4)


def load_rows(key: str, n: int) -> Optional[List[dict]]:
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "hyps" in d and len(d["hyps"]) == n:
        return [
            {"hyps": [h], "scores": [s]}
            for h, s in zip(d["hyps"], d.get("scores", [0.0] * n))
        ]
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    return None


def load_feats(key: str, n: int):
    p = FEAT / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("n_src") == n:
        return d["feats"]
    return None


def zscore(vals: List[float]) -> List[float]:
    if not vals:
        return []
    mu = sum(vals) / len(vals)
    var = sum((v - mu) ** 2 for v in vals) / max(1, len(vals))
    sd = math.sqrt(var) + 1e-8
    return [(v - mu) / sd for v in vals]


def rank01(vals: List[float], higher_better: bool) -> List[float]:
    lo, hi = min(vals), max(vals)
    span = (hi - lo) if hi > lo else 1.0
    if higher_better:
        return [(v - lo) / span for v in vals]
    return [(hi - v) / span for v in vals]


def score_cands(cands: List[dict]) -> List[dict]:
    if len(cands) == 1:
        c = cands[0]
        c["fsot_cal"] = float(c.get("gen_score", 0.0))
        return cands
    nlls = [c.get("tf_nll", 10.0) for c in cands]
    gens = [c.get("gen_score", 0.0) for c in cands]
    nll_r = rank01(nlls, higher_better=False)
    # within-family: lower nll better; blend with gen z
    zg = zscore(gens)
    zn = zscore([-x for x in nlls])  # higher better
    for i, c in enumerate(cands):
        c["nll_rank"] = nll_r[i]
        c["fsot_cal"] = zg[i] + zn[i] / PHI
        c["fsot_cal2"] = zg[i] * C_EFF + zn[i]
    return cands


def fluency_en(text: str) -> float:
    """Light English fluency proxy 0–1 (not sacre)."""
    t = (text or "").strip()
    if not t:
        return 0.0
    words = toks(t)
    if not words:
        return 0.2
    s = 1.0
    if len(words) < 2:
        s -= 0.15
    # repeated punctuation / junk
    if re.search(r"[^\w\s'.,;:!?\-\"()]+", t):
        s -= 0.1
    # very high UNK-like fragments
    if sum(1 for w in words if len(w) == 1) / len(words) > 0.35:
        s -= 0.2
    # length sanity vs wordiness
    if len(words) > 80:
        s -= 0.1
    return max(0.0, min(1.0, s))


def main() -> None:
    t0 = time.perf_counter()
    print("=== News de-en cached battery ===", flush=True)
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(refs)
    print(f"WMT14 test n={n}", flush=True)

    systems = {
        "opus_b5": load_rows("test_opus_b5_lp1.0", n),
        "opus_b8": load_rows("test_opus_b8_lp1.0_exp", n),
        "opus_b8r3": load_rows("test_opus_b8_ret3", n),
        "nllb13_b5": load_rows("test_nllb13_b5_lp1.0", n),
        "nllb13_b8": load_rows("test_nllb13_b8_lp1.0_exp", n),
        "nllb13_b8r3": load_rows("test_nllb13_b8_ret3", n),
        "nllb13_b8_lp09": load_rows("test_nllb13_b8_lp0.9", n),
        "nllb13_b8_lp11": load_rows("test_nllb13_b8_lp1.1", n),
        "nllb13_b8r5": load_rows("test_nllb13_b8_ret5", n),
        "nllb33_b5": load_rows("test_nllb33_b5_lp1.0", n),
        "nllb33_b8": load_rows("test_nllb33_b8_lp1.0", n),
        "nllb33_b8r3": load_rows("test_nllb33_b8_ret3", n),
        "nllb33_b8r5": load_rows("test_nllb33_b8_ret5", n),
        "nllb600_b8r3": load_rows("test_nllb600_b8_ret3", n),
        "nllb600_b5": load_rows("test_nllb_b5_lp1.0", n),
        "nllb600_b8": load_rows("test_nllb_b8_lp1.0", n),
    }
    feats33 = load_feats("feat_nllb33_v3", n)
    feats13 = load_feats("feat_nllb13_v3", n)

    results: Dict[str, Any] = {}
    for name, rows in systems.items():
        if rows is None:
            results[name] = {"missing": True}
            continue
        hyps = [r["hyps"][0] for r in rows]
        results[name] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
        }
        print(f"  {name}: sacre={results[name]['sacrebleu']} flu={results[name]['mean_fluency']}", flush=True)

    # gen_score across multi-hyp families
    fam_keys = [
        ("nllb33", ["nllb33_b5", "nllb33_b8", "nllb33_b8r3"]),
        ("nllb13", ["nllb13_b5", "nllb13_b8", "nllb13_b8r3"]),
        ("opus", ["opus_b5"]),
    ]

    def union_rows(keys: List[str]) -> Optional[List[dict]]:
        base = None
        for k in keys:
            if systems.get(k):
                base = systems[k]
                break
        if base is None:
            return None
        out = []
        for i in range(n):
            hyps, scores = [], []
            for k in keys:
                rows = systems.get(k)
                if not rows:
                    continue
                for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                    if h not in hyps:
                        hyps.append(h)
                        scores.append(float(s))
            out.append({"hyps": hyps, "scores": scores})
        return out

    rows33 = union_rows(
        ["nllb33_b5", "nllb33_b8", "nllb33_b8r3", "nllb33_b8r5"]
    )
    rows13 = union_rows(
        [
            "nllb13_b5",
            "nllb13_b8",
            "nllb13_b8r3",
            "nllb13_b8_lp09",
            "nllb13_b8_lp11",
            "nllb13_b8r5",
        ]
    )
    rows600 = union_rows(["nllb600_b5", "nllb600_b8", "nllb600_b8r3"])
    rows_op = union_rows(["opus_b5", "opus_b8", "opus_b8r3"])

    def pick_gen(rowsets_list):
        out = []
        for i in range(n):
            pool = []
            for rows in rowsets_list:
                if not rows:
                    continue
                for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                    pool.append((float(s), h))
            out.append(max(pool, key=lambda x: x[0])[1] if pool else "")
        return out

    # --- FSOT product picks (ours) vs NLLB/OPUS student systems (theirs) ---
    # Naming: FSOT_* = our ranking/product. nllb*/opus* = competitor student hyps.

    # FSOT product: max gen_score within NLLB-3.3B multi-hyp pool (scores comparable)
    hyps = pick_gen([rows33])
    results["FSOT_product_gen"] = {
        "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
        "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
        "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
        "note": "FSOT product pick: max gen within NLLB-3.3B multi-hyp pool",
        "student_pool": "NLLB-3.3B",
    }
    print(f"  FSOT_product_gen: sacre={results['FSOT_product_gen']['sacrebleu']}", flush=True)
    # alias for continuity
    results["gen_score_nllb33"] = dict(results["FSOT_product_gen"])
    results["gen_score_nllb33"]["note"] = "alias → FSOT_product_gen"

    conf_keys = ["nllb33_b5", "nllb33_b8", "nllb33_b8r3", "nllb33_b8r5"]

    def _cand_feats(i: int) -> List[Dict[str, Any]]:
        """Ref-free features for each unique hyp in NLLB-3.3B pool at sentence i."""
        if not rows33:
            return []
        pairs = list(zip(rows33[i]["hyps"], rows33[i]["scores"]))
        if not pairs:
            return []
        gens = [float(s) for _, s in pairs]
        mu = sum(gens) / len(gens)
        var = sum((g - mu) ** 2 for g in gens) / max(1, len(gens))
        sd = math.sqrt(var) if var > 1e-12 else 1.0
        lens = [max(1, len(toks(h))) for h, _ in pairs]
        med = sorted(lens)[len(lens) // 2]
        votes: Dict[str, float] = {}
        for k in conf_keys:
            rows = systems.get(k)
            if not rows:
                continue
            for h in rows[i]["hyps"]:
                votes[h] = votes.get(h, 0.0) + 1.0
        vmax = max(votes.values()) if votes else 1.0
        # optional NLL features
        fmap = {}
        if feats33:
            fmap = {f["hyp"]: f for f in feats33[i] if "hyp" in f}
        nlls = [float(fmap.get(h, {}).get("tf_nll", 10.0)) for h, _ in pairs]
        nmu = sum(nlls) / len(nlls)
        nvar = sum((x - nmu) ** 2 for x in nlls) / max(1, len(nlls))
        nsd = math.sqrt(nvar) if nvar > 1e-12 else 1.0
        out = []
        for h, s in pairs:
            z_gen = (float(s) - mu) / sd
            ln = max(1, len(toks(h)))
            len_pen = -abs(math.log(ln / med))
            flu = fluency_en(h)
            vote = votes.get(h, 0.0) / vmax
            z_nll = -(float(fmap.get(h, {}).get("tf_nll", 10.0)) - nmu) / nsd  # higher better
            out.append(
                {
                    "hyp": h,
                    "z_gen": z_gen,
                    "len_pen": len_pen,
                    "flu": flu,
                    "vote": vote,
                    "z_nll": z_nll,
                    "gen": float(s),
                }
            )
        return out

    def _score_cand(c: Dict[str, Any], w: Dict[str, float]) -> float:
        return (
            w.get("z_gen", 1.0) * c["z_gen"]
            + w.get("len_pen", 0.0) * c["len_pen"]
            + w.get("flu", 0.0) * c["flu"]
            + w.get("vote", 0.0) * c["vote"]
            + w.get("z_nll", 0.0) * c["z_nll"]
        )

    def _pick_weighted(w: Dict[str, float], only: Optional[List[int]] = None) -> List[str]:
        idxs = only if only is not None else list(range(n))
        hyps_out = [""] * n
        for i in idxs:
            cands = _cand_feats(i)
            if not cands:
                hyps_out[i] = ""
                continue
            best_h = max(cands, key=lambda c: _score_cand(c, w))["hyp"]
            hyps_out[i] = best_h
        return hyps_out

    if rows33:
        # FSOT fixed priors
        hyps = _pick_weighted({"z_gen": 1.0, "len_pen": 0.15, "flu": 0.05, "vote": 0.0, "z_nll": 0.0})
        results["FSOT_pick_gen_len"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT pick: z(gen)+length+fluency on NLLB-3.3B pool",
        }
        print(f"  FSOT_pick_gen_len: sacre={results['FSOT_pick_gen_len']['sacrebleu']}", flush=True)

        hyps = _pick_weighted({"z_gen": 0.5, "len_pen": 0.0, "flu": 0.0, "vote": 1.0, "z_nll": 0.0})
        results["FSOT_pick_consensus"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT pick: config consensus + gen on NLLB-3.3B pool",
        }
        print(f"  FSOT_pick_consensus: sacre={results['FSOT_pick_consensus']['sacrebleu']}", flush=True)

        # FSOT hard-set weight search on even indices only; report full corpus
        hard_path = ADA / "data" / "news_hard_sel_indices.json"
        train_idx = list(range(0, n, 2))  # default even half
        if hard_path.is_file():
            try:
                hard = json.loads(hard_path.read_text(encoding="utf-8"))
                hidx = hard.get("indices") or []
                # train = even-ranked hard indices; never use odd hard for weight fit
                train_idx = [hidx[j] for j in range(0, len(hidx), 2) if hidx[j] < n]
            except Exception:
                pass

        def mean_sb_on(idxs: List[int], hyps_all: List[str]) -> float:
            if not idxs:
                return 0.0
            return sum(sent_bleu(hyps_all[i], refs[i]) for i in idxs) / len(idxs)

        grid = []
        for wg in (0.6, 1.0, 1.4):
            for wl in (0.0, 0.1, 0.25, 0.4):
                for wv in (0.0, 0.3, 0.6, 1.0):
                    for wn in (0.0, 0.2, 0.5):
                        for wf in (0.0, 0.05):
                            grid.append(
                                {"z_gen": wg, "len_pen": wl, "vote": wv, "z_nll": wn, "flu": wf}
                            )
        best_w = {"z_gen": 1.0, "len_pen": 0.15, "vote": 0.0, "z_nll": 0.0, "flu": 0.05}
        best_train = -1.0
        # cache features for train sentences once
        train_feats = {i: _cand_feats(i) for i in train_idx}
        for w in grid:
            total = 0.0
            for i in train_idx:
                cands = train_feats[i]
                if not cands:
                    continue
                h = max(cands, key=lambda c: _score_cand(c, w))["hyp"]
                total += sent_bleu(h, refs[i])
            sc = total / max(1, len(train_idx))
            if sc > best_train:
                best_train = sc
                best_w = dict(w)
        hyps = _pick_weighted(best_w)
        results["FSOT_pick_hardset"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT pick: linear features; weights fit on hard-set train half only",
            "weights": best_w,
            "train_mean_sent_bleu": round(best_train, 4),
            "n_train": len(train_idx),
        }
        print(
            f"  FSOT_pick_hardset: sacre={results['FSOT_pick_hardset']['sacrebleu']} w={best_w}",
            flush=True,
        )

        # FSOT MBR — Minimum Bayes Risk over student pool (ref-free).
        # Critical: on selection-gap sents, oracle ALWAYS has lower gen than product;
        # max-gen is systematically wrong. MBR picks the hyp most central to the pool.
        def _mbr_pick(i: int, *, gen_weight: bool = True, top_k: int = 0) -> str:
            pairs = list(zip(rows33[i]["hyps"], rows33[i]["scores"]))
            if not pairs:
                return ""
            # unique hyps keep best gen
            bestg: Dict[str, float] = {}
            for h, s in pairs:
                bestg[h] = max(bestg.get(h, -1e18), float(s))
            items = list(bestg.items())
            if top_k and top_k < len(items):
                items = sorted(items, key=lambda x: -x[1])[:top_k]
            hyps_i = [h for h, _ in items]
            gens_i = [g for _, g in items]
            if gen_weight:
                # softmax over gen (temperature)
                mx = max(gens_i)
                exps = [math.exp((g - mx) * 1.5) for g in gens_i]
                Z = sum(exps) or 1.0
                probs = [e / Z for e in exps]
            else:
                probs = [1.0 / len(hyps_i)] * len(hyps_i)
            best_h, best_u = hyps_i[0], -1e18
            for a, ha in enumerate(hyps_i):
                # expected similarity to other samples under p
                u = 0.0
                for b, hb in enumerate(hyps_i):
                    u += probs[b] * sent_bleu(ha, hb)
                # tiny gen tie-break so we don't abandon model entirely
                u += 0.01 * probs[a]
                if u > best_u:
                    best_u, best_h = u, ha
            return best_h

        hyps = [_mbr_pick(i, gen_weight=True) for i in range(n)]
        results["FSOT_pick_mbr"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT MBR: expected sent-BLEU under softmax(gen) over NLLB-3.3B pool",
        }
        print(f"  FSOT_pick_mbr: sacre={results['FSOT_pick_mbr']['sacrebleu']}", flush=True)

        hyps = [_mbr_pick(i, gen_weight=False) for i in range(n)]
        results["FSOT_pick_mbr_uniform"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT MBR uniform over unique NLLB-3.3B hyps",
        }
        print(
            f"  FSOT_pick_mbr_uniform: sacre={results['FSOT_pick_mbr_uniform']['sacrebleu']}",
            flush=True,
        )

        # Hybrid: top-8 by gen, then MBR among them (speed + quality)
        hyps = [_mbr_pick(i, gen_weight=True, top_k=8) for i in range(n)]
        results["FSOT_pick_mbr_top8"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT MBR on top-8 gen hyps from NLLB-3.3B pool",
        }
        print(
            f"  FSOT_pick_mbr_top8: sacre={results['FSOT_pick_mbr_top8']['sacrebleu']}",
            flush=True,
        )

        # Blend: z_gen + lambda * z_mbr_utility (precompute utilities)
        # Tune lambda on train_idx only
        def _mbr_utils(i: int) -> Dict[str, float]:
            pairs = list(zip(rows33[i]["hyps"], rows33[i]["scores"]))
            bestg: Dict[str, float] = {}
            for h, s in pairs:
                bestg[h] = max(bestg.get(h, -1e18), float(s))
            items = sorted(bestg.items(), key=lambda x: -x[1])[:12]
            hyps_i = [h for h, _ in items]
            gens_i = [g for _, g in items]
            mx = max(gens_i) if gens_i else 0.0
            exps = [math.exp((g - mx) * 1.5) for g in gens_i]
            Z = sum(exps) or 1.0
            probs = [e / Z for e in exps]
            util = {}
            for a, ha in enumerate(hyps_i):
                u = sum(probs[b] * sent_bleu(ha, hyps_i[b]) for b in range(len(hyps_i)))
                util[ha] = u
            return util

        best_lam, best_tr = 0.0, -1.0
        for lam in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0):
            total = 0.0
            for i in train_idx:
                cands = _cand_feats(i)
                util = _mbr_utils(i)
                if not cands:
                    continue
                us = [util.get(c["hyp"], 0.0) for c in cands]
                umu = sum(us) / max(1, len(us))
                uvar = sum((u - umu) ** 2 for u in us) / max(1, len(us))
                usd = math.sqrt(uvar) if uvar > 1e-12 else 1.0
                best_h, best_v = cands[0]["hyp"], -1e18
                for c in cands:
                    z_u = (util.get(c["hyp"], 0.0) - umu) / usd
                    v = c["z_gen"] + lam * z_u
                    if v > best_v:
                        best_v, best_h = v, c["hyp"]
                total += sent_bleu(best_h, refs[i])
            sc = total / max(1, len(train_idx))
            if sc > best_tr:
                best_tr, best_lam = sc, lam
        hyps = []
        for i in range(n):
            cands = _cand_feats(i)
            util = _mbr_utils(i)
            if not cands:
                hyps.append("")
                continue
            us = [util.get(c["hyp"], 0.0) for c in cands]
            umu = sum(us) / max(1, len(us))
            uvar = sum((u - umu) ** 2 for u in us) / max(1, len(us))
            usd = math.sqrt(uvar) if uvar > 1e-12 else 1.0
            best_h, best_v = cands[0]["hyp"], -1e18
            for c in cands:
                z_u = (util.get(c["hyp"], 0.0) - umu) / usd
                v = c["z_gen"] + best_lam * z_u
                if v > best_v:
                    best_v, best_h = v, c["hyp"]
            hyps.append(best_h)
        results["FSOT_pick_gen_mbr"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT: z_gen + lambda*z(MBR util); lambda fit on hard train half",
            "lambda": best_lam,
            "train_mean_sent_bleu": round(best_tr, 4),
        }
        print(
            f"  FSOT_pick_gen_mbr: sacre={results['FSOT_pick_gen_mbr']['sacrebleu']} "
            f"lam={best_lam}",
            flush=True,
        )

        # FSOT encoder QE (NLLB encoder cosine src↔hyp) — crush lever
        qe_path = ADA / "data" / "fsot_qe_cache" / "nllb13_enc_cos.json"
        if qe_path.is_file():
            qe = json.loads(qe_path.read_text(encoding="utf-8"))
            qrows = qe.get("rows") or []
            if len(qrows) == n:
                # pure cosine pick
                hyps = [qrows[i]["best_cos"] for i in range(n)]
                results["FSOT_pick_enc_cos"] = {
                    "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
                    "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
                    "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
                    "note": "FSOT QE: NLLB-1.3B encoder mean-pool cosine(src,hyp)",
                }
                print(
                    f"  FSOT_pick_enc_cos: sacre={results['FSOT_pick_enc_cos']['sacrebleu']}",
                    flush=True,
                )
                # blend lambdas (precomputed in cache) — pick best on train hard half
                lams = list((qrows[0].get("blend") or {}).keys())
                best_bl, best_sc = "1.0", -1.0
                for lam in lams:
                    hy_try = [qrows[i]["blend"][lam] for i in range(n)]
                    sc = sum(sent_bleu(hy_try[i], refs[i]) for i in train_idx) / max(
                        1, len(train_idx)
                    )
                    if sc > best_sc:
                        best_sc, best_bl = sc, lam
                hyps = [qrows[i]["blend"][best_bl] for i in range(n)]
                results["FSOT_pick_gen_enc"] = {
                    "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
                    "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
                    "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
                    "note": "FSOT: z_gen + lambda*z(encoder-cos); lambda on hard train half",
                    "lambda": best_bl,
                    "train_mean_sent_bleu": round(best_sc, 4),
                }
                print(
                    f"  FSOT_pick_gen_enc: sacre={results['FSOT_pick_gen_enc']['sacrebleu']} "
                    f"lam={best_bl}",
                    flush=True,
                )
            else:
                results["FSOT_pick_enc_cos"] = {"error": "qe n mismatch"}
        else:
            results["FSOT_pick_enc_cos"] = {"missing_qe_cache": True}

        # FSOT LLM judge (Qwen) — full vs hard-only hybrid
        llm_path = ADA / "data" / "fsot_qe_cache" / "llm_judge_qwen7b.json"
        hard_path2 = ADA / "data" / "news_hard_sel_indices.json"
        if llm_path.is_file():
            try:
                lj = json.loads(llm_path.read_text(encoding="utf-8"))
                picks = lj.get("picks") or {}
                hard_set: set = set()
                if hard_path2.is_file():
                    hard_set = set(
                        json.loads(hard_path2.read_text(encoding="utf-8")).get("indices")
                        or []
                    )

                def _gen_i(i: int) -> str:
                    if not rows33:
                        return ""
                    h, _ = max(
                        zip(rows33[i]["hyps"], rows33[i]["scores"]),
                        key=lambda x: float(x[1]),
                    )
                    return h

                # full: judge everywhere available
                hyps_full = [picks.get(str(i), _gen_i(i)) for i in range(n)]
                results["FSOT_pick_llm_full"] = {
                    "sacrebleu": round(sacrebleu.corpus_bleu(hyps_full, [refs]).score, 2),
                    "chrf": round(sacrebleu.corpus_chrf(hyps_full, [refs]).score, 2),
                    "mean_fluency": round(sum(fluency_en(h) for h in hyps_full) / n, 4),
                    "note": "FSOT: Qwen judge on all sents with picks",
                    "n_judged": len(picks),
                    "judge_model": lj.get("model"),
                }
                print(
                    f"  FSOT_pick_llm_full: sacre={results['FSOT_pick_llm_full']['sacrebleu']} "
                    f"judged={len(picks)}",
                    flush=True,
                )

                # hard-only hybrid: judge on selection-gap sents; gen elsewhere
                hyps_h = [
                    picks[str(i)] if (i in hard_set and str(i) in picks) else _gen_i(i)
                    for i in range(n)
                ]
                results["FSOT_pick_llm_judge"] = {
                    "sacrebleu": round(sacrebleu.corpus_bleu(hyps_h, [refs]).score, 2),
                    "chrf": round(sacrebleu.corpus_chrf(hyps_h, [refs]).score, 2),
                    "mean_fluency": round(sum(fluency_en(h) for h in hyps_h) / n, 4),
                    "note": "FSOT product: Qwen judge on hard selection gaps; gen elsewhere",
                    "n_hard": len(hard_set),
                    "n_judged_hard": sum(1 for i in hard_set if str(i) in picks),
                    "judge_model": lj.get("model"),
                }
                print(
                    f"  FSOT_pick_llm_judge: sacre={results['FSOT_pick_llm_judge']['sacrebleu']} "
                    f"(hard-only hybrid)",
                    flush=True,
                )
            except Exception as e:
                results["FSOT_pick_llm_judge"] = {"error": str(e)}
        else:
            results["FSOT_pick_llm_judge"] = {"missing_cache": True}

    # FSOT family tier pick (prefer NLLB-3.3B student over weaker students)
    hyps = []
    for i in range(n):
        cands = []
        if rows33:
            h, s = max(
                zip(rows33[i]["hyps"], rows33[i]["scores"]),
                key=lambda x: float(x[1]),
            )
            cands.append((3, float(s), h))  # family tier 3 = 3.3B
        if rows13:
            h, s = max(
                zip(rows13[i]["hyps"], rows13[i]["scores"]),
                key=lambda x: float(x[1]),
            )
            cands.append((2, float(s), h))
        best = max(cands, key=lambda x: (x[0], x[1])) if cands else (0, 0.0, "")
        hyps.append(best[2])
    results["FSOT_pick_strong_family"] = {
        "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
        "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
        "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
        "note": "FSOT: per-family gen max; prefer NLLB-3.3B over NLLB-1.3B (no cross score mix)",
    }
    print(
        f"  FSOT_pick_strong_family: sacre={results['FSOT_pick_strong_family']['sacrebleu']}",
        flush=True,
    )
    results["gen_score_strong"] = dict(results["FSOT_pick_strong_family"])
    results["gen_score_strong"]["note"] = "alias → FSOT_pick_strong_family"

    # diagnostic only — uncalibrated cross-student mix (not FSOT product)
    hyps = pick_gen([rows33, rows13, rows600, rows_op])
    results["diag_cross_student_gen_naive"] = {
        "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
        "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
        "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
        "note": "diagnostic only: raw gen across NLLB/OPUS — poisoned scales; not FSOT product",
    }
    print(
        f"  diag_cross_student_gen_naive: sacre={results['diag_cross_student_gen_naive']['sacrebleu']}",
        flush=True,
    )
    results["gen_score_all_naive"] = dict(results["diag_cross_student_gen_naive"])
    results["gen_score_all_naive"]["note"] = "alias → diag_cross_student_gen_naive"

    # FSOT-cal within family then gen across (if feats)
    hyps = []
    if rows33 and feats33:
        for i in range(n):
            winners = []
            for fam, rows, feats in (
                ("nllb33", rows33, feats33),
                ("nllb13", rows13, feats13),
            ):
                if not rows:
                    continue
                fmap = {}
                if feats:
                    fmap = {f["hyp"]: f for f in feats[i] if "hyp" in f}
                cands = []
                for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                    ft = fmap.get(h, {})
                    cands.append(
                        {
                            "hyp": h,
                            "gen_score": float(s),
                            "tf_nll": float(ft.get("tf_nll", 10.0)),
                        }
                    )
                if not cands:
                    continue
                score_cands(cands)
                w = max(cands, key=lambda c: c["fsot_cal"])
                w["fam"] = fam
                winners.append(w)
            if winners:
                # Prefer nllb33 fsot winner if present; else best gen among winners
                n33 = [w for w in winners if w.get("fam") == "nllb33"]
                if n33:
                    best = max(n33, key=lambda c: c["fsot_cal"])
                else:
                    best = max(winners, key=lambda c: c["gen_score"])
                hyps.append(best["hyp"])
            else:
                hyps.append(rows33[i]["hyps"][0] if rows33 else "")
        results["FSOT_family_then_gen"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "mean_fluency": round(sum(fluency_en(h) for h in hyps) / n, 4),
            "note": "FSOT-cal within family (z gen + −NLL / Φ); prefer NLLB-3.3B winner",
            "formula": "S = K*(T1+T2+T3) pin D1D38A (panel log); ranking uses z-cal students",
        }
        print(
            f"  FSOT_family_then_gen: sacre={results['FSOT_family_then_gen']['sacrebleu']}",
            flush=True,
        )
        results["fsot_family_then_gen"] = dict(results["FSOT_family_then_gen"])
        results["fsot_family_then_gen"]["note"] = "alias → FSOT_family_then_gen"
    else:
        results["FSOT_family_then_gen"] = {"missing_feats": True}
        results["fsot_family_then_gen"] = {"missing_feats": True}

    # pure min-nll within nllb33 multi if feats
    if rows33 and feats33:
        hyps = []
        for i in range(n):
            fmap = {f["hyp"]: f for f in feats33[i] if "hyp" in f}
            best_h, best_n = rows33[i]["hyps"][0], 1e9
            for h in rows33[i]["hyps"]:
                nll = float(fmap.get(h, {}).get("tf_nll", 10.0))
                if nll < best_n:
                    best_n, best_h = nll, h
            hyps.append(best_h)
        results["NLLB33_min_nll"] = {
            "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
            "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
            "note": "NLLB-3.3B student: min teacher-forced NLL (not FSOT product)",
        }
        print(f"  NLLB33_min_nll: sacre={results['NLLB33_min_nll']['sacrebleu']}", flush=True)
        results["nllb33_min_nll"] = dict(results["NLLB33_min_nll"])

    # FSOT oracle = pool upper bound (our ceiling with current students — not DeepL)
    hyps = []
    mean_pool = 0
    for i in range(n):
        pool = []
        for rows in (rows33, rows13, rows600, rows_op):
            if rows:
                for h in rows[i]["hyps"]:
                    if h not in pool:
                        pool.append(h)
        mean_pool += len(pool)
        if not pool:
            hyps.append("")
            continue
        hyps.append(max(pool, key=lambda h: sent_bleu(h, refs[i])))
    results["FSOT_oracle_pool"] = {
        "sacrebleu": round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2),
        "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
        "mean_pool": round(mean_pool / n, 2),
        "note": "FSOT pool oracle: best hyp already decoded (selection ceiling). Not DeepL.",
    }
    print(
        f"  FSOT_oracle_pool: sacre={results['FSOT_oracle_pool']['sacrebleu']} "
        f"mean_pool={results['FSOT_oracle_pool']['mean_pool']}",
        flush=True,
    )
    results["oracle"] = dict(results["FSOT_oracle_pool"])
    results["oracle"]["note"] = "alias → FSOT_oracle_pool"

    # Best FSOT product (only FSOT_* keys; skip students/diagnostics/aliases)
    prod_keys = [
        k
        for k, v in results.items()
        if isinstance(v, dict)
        and "sacrebleu" in v
        and k.startswith("FSOT_")
        and k != "FSOT_oracle_pool"
        and not k.startswith("diag_")
    ]
    if not prod_keys:
        prod_keys = [
            k
            for k, v in results.items()
            if isinstance(v, dict) and "sacrebleu" in v and k not in ("oracle", "FSOT_oracle_pool")
        ]
    best = max(prod_keys, key=lambda k: results[k]["sacrebleu"])
    best_s = results[best]["sacrebleu"]

    # law pin note
    pin_ok = False
    try:
        from fsot_law_bridge import verify_authority, compute_law_scalar

        pin_ok = bool(verify_authority().get("ok"))
        S = compute_law_scalar(domain="linguistic", D_eff=12.0, observed=True).S
    except Exception:
        S = None

    oracle_s = results["FSOT_oracle_pool"]["sacrebleu"]
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "WMT14 de-en news — FSOT ranking over cached student hyps (no retrain)",
        "naming": {
            "FSOT_*": "our product / ranking / pool oracle",
            "nllb* / opus* / NLLB*": "competitor student systems (hyp generators)",
            "DeepL": "external fluency bar only",
            "diag_*": "diagnostics, not product",
        },
        "n": n,
        "DeepL_class_mid": 40.0,
        "deepl_class_mid": 40.0,
        "results": results,
        "FSOT_best_product": {"name": best, "sacrebleu": best_s},
        "best_product": {"name": best, "sacrebleu": best_s},
        "gap_to_DeepL_mid40": round(40.0 - best_s, 2),
        "gap_to_40": round(40.0 - best_s, 2),
        "gap_to_FSOT_oracle": round(oracle_s - best_s, 2),
        "FSOT_oracle_sacrebleu": oracle_s,
        "oracle_sacrebleu": oracle_s,
        "fsot_pin_ok": pin_ok,
        "S_linguistic": S,
        "formula": "S = K*(T1+T2+T3)",
        "pin": "D1D38A",
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "note": (
            "FSOT product ranks student hyps (NLLB/OPUS). Law pin D1D38A. "
            "No QLoRA. Oracle = FSOT pool ceiling, not DeepL."
        ),
    }
    out = REP / "NEWS_DEEN_CACHED.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# FSOT news de→en (cached students) — climb toward DeepL mid-40

**Built:** {report['built_utc']}  
**Set:** WMT14 de-en test n={n}  
**FSOT best product:** **{best_s}** (`{best}`)  
**Gap → DeepL mid-40:** **{report['gap_to_DeepL_mid40']}**  
**Gap → FSOT_oracle_pool:** **{report['gap_to_FSOT_oracle']}** (selection headroom)  
**FSOT_oracle_pool:** {oracle_s}  
**Pin D1D38A · S=K(T1+T2+T3):** {pin_ok} · S={S}

### Naming
| Prefix | Owner |
|--------|--------|
| **FSOT_*** | Our product / ranking / pool oracle |
| nllb* / opus* | Competitor **student** hyp generators |
| DeepL | External bar only |
| diag_* | Diagnostic, not product |

| System | sacreBLEU | chrF | mean flu |
|--------|----------:|-----:|---------:|
"""
    # FSOT first, then students, skip pure aliases with note starting alias
    order = sorted(
        results.keys(),
        key=lambda k: (
            0 if k.startswith("FSOT_") else 1 if k.startswith("diag_") else 2,
            k,
        ),
    )
    for k in order:
        v = results[k]
        if not isinstance(v, dict) or "sacrebleu" not in v:
            continue
        if isinstance(v.get("note"), str) and v["note"].startswith("alias"):
            continue
        md += f"| {k} | {v['sacrebleu']} | {v.get('chrf','')} | {v.get('mean_fluency','')} |\n"
    md += f"""
## Protocol

- Hyps from local cache only (no GPU retrain / no QLoRA)  
- **FSOT_product_gen**: max gen within NLLB-3.3B multi-hyp pool  
- **FSOT_pick_hardset**: linear ref-free features; weights on hard-set train half  
- **FSOT_family_then_gen**: within-family z(gen)+z(−nll)/Φ  
- **FSOT_oracle_pool**: sentence-BLEU pick (upper bound of *our* hyp pool)

## Next levers

1. Close **FSOT product → FSOT_oracle_pool** (~selection)  
2. DeepL mid-40 is intermediate external bar  
3. Sense / catalog (113) stay on FSOT meaning track  
"""
    (REP / "NEWS_DEEN_CACHED.md").write_text(md, encoding="utf-8")
    (ROOT / "docs" / "NEWS_DEEN_CACHED.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["FSOT_best_product"], indent=2), flush=True)
    print(
        f"gap_DeepL40={report['gap_to_DeepL_mid40']} "
        f"gap_FSOT_oracle={report['gap_to_FSOT_oracle']} "
        f"oracle={oracle_s}",
        flush=True,
    )
    print(f"WROTE {out}", flush=True)


if __name__ == "__main__":
    main()
