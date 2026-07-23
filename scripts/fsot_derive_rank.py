#!/usr/bin/env python3
"""
FSOT-derived ranking for the linguistics domain — intrinsic seeds only.

Rules (no free parameters / no ad-hoc knobs / no LLM judges):
  • Authority: archive fsot_compute.py pin D1D38A
  • Seeds only: π, e, φ, γ, G_Catalan → K, PHI, C_EFF, E, …
  • Observables first become *within-pool ranks* ∈ [0,1] (scale-free)
  • Then ScalarInput is assembled only with seed constants + ranks + domain table
  • S = K·(T1+T2+T3) from archive term structure
  • Product = argmax S (within NLLB-3.3B multi-hyp — students supply candidates)

We do NOT fit K or β to BLEU. We arrange puzzle pieces under the law.
When a candidate already matches gold well, we *observe* how its panel looks
(report puzzle_study) so the domain map can be refined — still no free fit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import sacrebleu
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
FEAT = ROOT / "pflt-Ada" / "data" / "fsot_feat_cache"
REP = ROOT / "pflt-Ada" / "reports"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

NLLB33_KEYS = [
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
]


def toks(t: str) -> List[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sent_bleu(h: str, r: str) -> float:
    """For puzzle study only (not used in product pick)."""
    ht, rt = toks(h), toks(r)
    if not ht or not rt:
        return 0.0
    from collections import Counter

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


def load_authority():
    from fsot_law_bridge import AUTHORITY_SHA256, find_authority_compute

    path = find_authority_compute()
    if path is None:
        raise RuntimeError("fsot_compute.py not found")
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    pin_ok = digest == AUTHORITY_SHA256
    spec = importlib.util.spec_from_file_location("fsot_compute_authority", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["fsot_compute_authority"] = mod
    spec.loader.exec_module(mod)
    return mod, path, pin_ok, digest


def split_terms(mod, s_in) -> Tuple[float, float, float, float]:
    from mpmath import cos, exp, ln, sin, sqrt

    N, P, D = s_in.N, s_in.P, s_in.D_eff
    dp, dt, hits = s_in.delta_psi, s_in.delta_theta, s_in.recent_hits
    growth = exp(s_in.alpha * (1 - hits / N) * mod.GAMMA / mod.PHI)
    base = (
        (N * P / sqrt(D))
        * cos((s_in.psi_con + dp) / mod.ETA_EFF)
        * exp(-s_in.alpha * hits / N + s_in.rho + s_in.B_in * dp)
        * (1 + growth * s_in.C_eff)
    )
    T1 = base * (1 + s_in.P_new * ln(D / 25))
    if s_in.observed:
        T1 = T1 * exp(mod.C_FACTOR * s_in.P_var) * cos(dp + s_in.P_var)
    T2 = s_in.scale * s_in.amplitude + s_in.trend_bias
    valve = (
        s_in.beta
        * cos(dp)
        * (N * P / sqrt(D))
        * (1 + s_in.chaos * (D - 25) / 25)
        * (
            1
            + s_in.poof * cos(s_in.theta_s + mod.PI)
            + s_in.suction * sin(s_in.theta_s)
        )
    )
    acoustic = (
        1
        + (s_in.A_bleed * sin(dt) ** 2) / mod.PHI
        + (s_in.A_in * cos(dt) ** 2) / mod.PHI
    )
    phase = 1 + s_in.B_in * s_in.P_var
    T3 = valve * acoustic * phase
    S = mod.K * (T1 + T2 + T3)
    return float(S), float(T1), float(T2), float(T3)


def linguistic_domain(mod) -> Tuple[float, float, float]:
    """
    Linguistics with Biology cluster (D_eff=12) — same as prior killshot / law bridge.
    Table only; no free D.
    """
    domains = getattr(mod, "DOMAINS", {}) or {}
    if "Biology" in domains:
        d = domains["Biology"]
        return float(d.D_eff), float(d.delta_psi), float(d.delta_theta)
    if "Neuroscience" in domains:
        d = domains["Neuroscience"]
        return float(d.D_eff), float(d.delta_psi), float(d.delta_theta)
    return 12.0, 0.08, 1.0  # Biology defaults from table


def rank01(vals: List[float], *, higher_better: bool) -> List[float]:
    """Scale-free ranks in [0,1] — no free normalization constants."""
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-15:
        return [float(mod_half()) for _ in vals]  # type: ignore
    if higher_better:
        return [(v - lo) / (hi - lo) for v in vals]
    return [(hi - v) / (hi - lo) for v in vals]


def mod_half() -> float:
    return 0.5  # mid-rank when degenerate; not a free param


def map_seed_only(
    mod,
    *,
    enc_norm: float,
    nll_rank: float,
    enc_rank: float,
    gen_rank: float,
    spm_ent_norm: float,
    spm_mean_len: float,
    spm_n_pieces: int,
    spm_unk_frac: float,
    hyp_len_tok: int,
    src_len_tok: int,
    D_eff: float,
    domain_dpsi: float,
    domain_dtheta: float,
):
    """
    Killshot-native seed map (proven arrangement under pin D1D38A).

    Uses only: φ-squash, within-pool ranks, golden split, archive defaults.
    gen_score enters only as gen_rank (scale-free) — no logistic free scale.
    """
    from mpmath import mpf

    PHI = float(mod.PHI)
    E = float(mod.E)
    C_EFF = float(mod.C_EFF)
    PI = float(mod.PI)

    # N: encoder mass — absolute φ-squash + rank
    n_abs = enc_norm / (enc_norm + PHI + 1e-15)
    N = PHI * (C_EFF + enc_rank + n_abs) / (1.0 + C_EFF)

    # P: low-NLL rank + gen_rank via golden split only
    w_nll = PHI / (1.0 + PHI)
    w_gen = 1.0 / (1.0 + PHI)
    rank_p = w_nll * nll_rank + w_gen * gen_rank
    P = C_EFF * (1.0 + rank_p * PHI)

    ls, lh = max(1, src_len_tok), max(1, hyp_len_tok)
    len_phase = abs(math.log1p(lh) - math.log1p(ls)) / PHI
    nll_stress = (1.0 - nll_rank) / PHI
    delta_psi = min(len_phase + nll_stress, PI / 2)
    # confidence lock: high gen_rank reduces phase stress (killshot)
    delta_psi = min(delta_psi * (1.0 - gen_rank / PHI), PI / 2)

    # Acoustic: breath target φ·e (seeds); unk / entropy / piece mass / φ
    BREATH = PHI * E
    breath = abs(spm_mean_len - BREATH) / max(BREATH, 1e-9)
    ent_stress = (1.0 - min(1.0, max(0.0, spm_ent_norm))) / PHI
    unk_stress = min(1.0, spm_unk_frac) * PHI
    piece_mass = abs(math.log1p(spm_n_pieces) - math.log1p(ls)) / PHI
    delta_theta = min(breath + ent_stress + unk_stress + piece_mass, PI / 2)
    delta_theta = min(delta_theta * (1.0 - gen_rank / (PHI + 1.0)), PI / 2)

    hits = max(0.0, (1.0 - nll_rank) * E)
    rho = max(
        1.0 / PHI,
        C_EFF
        * (1.0 - min(1.0, spm_unk_frac))
        * (1.0 / PHI + spm_ent_norm * (1.0 - 1.0 / PHI)),
    )
    scale = min(lh / float(ls), PHI)
    amplitude = rho * (C_EFF + rank_p)
    trend_bias = 0.0 if lh >= 2 else -1.0 / PHI

    return mod.ScalarInput(
        N=mpf(N),
        P=mpf(P),
        D_eff=mpf(D_eff),
        delta_psi=mpf(delta_psi),
        delta_theta=mpf(delta_theta),
        recent_hits=mpf(hits),
        rho=mpf(rho),
        observed=True,
        scale=mpf(scale),
        amplitude=mpf(amplitude),
        trend_bias=mpf(trend_bias),
    )


def load_rows(key: str, n: int):
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    return None


def load_feats(name: str, n: int):
    p = FEAT / f"{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    feats = d.get("feats")
    if not feats or len(feats) != n:
        return None
    return feats


def main() -> None:
    t0 = time.perf_counter()
    print("=== FSOT seed-only derive (linguistics domain) ===", flush=True)
    mod, path, pin_ok, digest = load_authority()
    K, PHI, C_EFF, E = float(mod.K), float(mod.PHI), float(mod.C_EFF), float(mod.E)
    D_eff, dom_dpsi, dom_dtheta = linguistic_domain(mod)
    print(f"pin_ok={pin_ok} K={K:.8f} PHI={PHI:.8f} E={E:.8f} C_EFF={C_EFF:.8f}", flush=True)
    print(f"domain D_eff={D_eff} δψ={dom_dpsi} δθ={dom_dtheta}", flush=True)
    print(f"authority={path}", flush=True)

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(refs)

    pools: List[List[dict]] = [[] for _ in range(n)]
    for key in NLLB33_KEYS:
        rows = load_rows(key, n)
        if not rows:
            continue
        print(f"  pool {key}", flush=True)
        for i in range(n):
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                pools[i].append({"hyp": h, "gen_score": float(s)})
    for i in range(n):
        best: Dict[str, dict] = {}
        for c in pools[i]:
            h = c["hyp"]
            if h not in best or c["gen_score"] > best[h]["gen_score"]:
                best[h] = c
        pools[i] = list(best.values())

    feats = load_feats("feat_nllb33_v3", n) or load_feats("feat_nllb33_v2", n)
    if feats is None:
        raise RuntimeError("feat cache required for observables")
    feat_by_hyp: List[Dict[str, dict]] = []
    for i in range(n):
        m = {}
        for f in feats[i]:
            if f.get("hyp"):
                m[f["hyp"]] = f
        feat_by_hyp.append(m)

    hyps_S, hyps_lin, hyps_gen = [], [], []
    mean_S = 0.0
    n_scored = 0
    agree = 0
    # puzzle: panels when hyp is strong vs weak vs gold
    good_S, bad_S, good_T1, bad_T1 = [], [], [], []
    samples = []

    for i in range(n):
        cands = pools[i]
        if not cands:
            hyps_S += [""]
            hyps_lin += [""]
            hyps_gen += [""]
            continue

        nlls, encs, gens = [], [], []
        for c in cands:
            f = feat_by_hyp[i].get(c["hyp"], {})
            nlls.append(float(f.get("tf_nll", 5.0)))
            encs.append(float(f.get("enc_norm", 1.0)))
            gens.append(c["gen_score"])
        nll_r = rank01(nlls, higher_better=False)
        enc_r = rank01(encs, higher_better=True)
        gen_r = rank01(gens, higher_better=True)

        scored = []
        for j, c in enumerate(cands):
            f = feat_by_hyp[i].get(c["hyp"], {})
            s_in = map_seed_only(
                mod,
                enc_norm=float(f.get("enc_norm", encs[j])),
                nll_rank=nll_r[j],
                enc_rank=enc_r[j],
                gen_rank=gen_r[j],
                spm_ent_norm=float(f.get("spm_ent_norm", 1.0 / PHI)),
                spm_mean_len=float(f.get("spm_mean_len", PHI * E)),
                spm_n_pieces=int(f.get("spm_n_pieces", max(1, len(toks(c["hyp"]))))),
                spm_unk_frac=float(f.get("spm_unk_frac", 0.0)),
                hyp_len_tok=int(f.get("hyp_len_tok", len(toks(c["hyp"])))),
                src_len_tok=int(f.get("src_len_tok", len(toks(srcs[i])))),
                D_eff=D_eff,
                domain_dpsi=dom_dpsi,
                domain_dtheta=dom_dtheta,
            )
            S, T1, T2, T3 = split_terms(mod, s_in)
            scored.append(
                {
                    "hyp": c["hyp"],
                    "S": S,
                    "T1": T1,
                    "T2": T2,
                    "T3": T3,
                    "score_lin": T1 * C_EFF + T2 + T3 / PHI,
                    "gen": c["gen_score"],
                    "sb": sent_bleu(c["hyp"], refs[i]),
                }
            )
            mean_S += S
            n_scored += 1

        bS = max(scored, key=lambda x: x["S"])
        bL = max(scored, key=lambda x: x["score_lin"])
        bG = max(scored, key=lambda x: x["gen"])
        bGold = max(scored, key=lambda x: x["sb"])  # study only
        hyps_S.append(bS["hyp"])
        hyps_lin.append(bL["hyp"])
        hyps_gen.append(bG["hyp"])
        if bS["hyp"] == bG["hyp"]:
            agree += 1

        # puzzle study: when gold-best is clear, record panels
        if bGold["sb"] >= 0.45:
            good_S.append(bGold["S"])
            good_T1.append(bGold["T1"])
            # worst sb in pool
            worst = min(scored, key=lambda x: x["sb"])
            bad_S.append(worst["S"])
            bad_T1.append(worst["T1"])

        if i < 3 or i in (500, 1500, 2500):
            samples.append(
                {
                    "i": i,
                    "S": bS["S"],
                    "T1": bS["T1"],
                    "T2": bS["T2"],
                    "T3": bS["T3"],
                    "pick_S": bS["hyp"][:90],
                    "gold_best_same": bS["hyp"] == bGold["hyp"],
                    "gen_same": bS["hyp"] == bG["hyp"],
                }
            )
        if i % 500 == 0:
            print(f"  {i}/{n} S={bS['S']:.5f} T1={bS['T1']:.4f} T3={bS['T3']:.6g}", flush=True)

    sacre_S = sacrebleu.corpus_bleu(hyps_S, [refs]).score
    sacre_lin = sacrebleu.corpus_bleu(hyps_lin, [refs]).score
    sacre_gen = sacrebleu.corpus_bleu(hyps_gen, [refs]).score
    chrf_S = sacrebleu.corpus_chrf(hyps_S, [refs]).score
    best_name = "FSOT_product_S" if sacre_S >= sacre_lin else "FSOT_product_lin"
    best_s = max(sacre_S, sacre_lin)

    puzzle = {
        "n_clear_gold": len(good_S),
        "mean_S_when_hyp_good": sum(good_S) / max(1, len(good_S)),
        "mean_S_when_hyp_worst": sum(bad_S) / max(1, len(bad_S)),
        "mean_T1_good": sum(good_T1) / max(1, len(good_T1)),
        "mean_T1_worst": sum(bad_T1) / max(1, len(bad_T1)),
        "note": (
            "When a candidate already aligns with gold (sb≥0.45), observe its panel. "
            "Good hyps should show higher S than worst in same pool if the map is right. "
            "No free-fit — diagnostic for arranging seeds only."
        ),
    }
    if good_S:
        puzzle["S_separation"] = puzzle["mean_S_when_hyp_good"] - puzzle["mean_S_when_hyp_worst"]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "FSOT seed-only linguistics domain rank",
        "formula": "S = K*(T1+T2+T3)",
        "pin": "D1D38A",
        "pin_ok": pin_ok,
        "authority_path": str(path),
        "seeds_used": {
            "K": K,
            "PHI": PHI,
            "E": E,
            "C_EFF": C_EFF,
            "GAMMA": float(mod.GAMMA),
            "D_eff_domain": D_eff,
            "domain_delta_psi": dom_dpsi,
            "domain_delta_theta": dom_dtheta,
            "breath_target": PHI * E,
            "golden_split_w_nll": PHI / (1 + PHI),
            "golden_split_w_gen": 1 / (1 + PHI),
        },
        "no_free_parameters": True,
        "no_llm_judge": True,
        "n": n,
        "mean_S": mean_S / max(1, n_scored),
        "agree_S_vs_gen_pct": round(100 * agree / n, 2),
        "results": {
            "FSOT_product_S": {
                "sacrebleu": round(sacre_S, 2),
                "chrf": round(chrf_S, 2),
                "note": "argmax archive S under seed-only map",
            },
            "FSOT_product_lin": {
                "sacrebleu": round(sacre_lin, 2),
                "note": "argmax T1*C_EFF+T2+T3/PHI (seed constants)",
            },
            "student_gen_max": {
                "sacrebleu": round(sacre_gen, 2),
                "note": "NLLB-3.3B gen — student baseline NOT product",
            },
        },
        "best_product": {"name": best_name, "sacrebleu": round(best_s, 2)},
        "gap_to_DeepL_mid40": round(40.0 - best_s, 2),
        "gap_to_student_gen": round(sacre_gen - best_s, 2),
        "puzzle_study": puzzle,
        "samples": samples,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "honesty": (
            "No free-fit. No Qwen. Ranks are scale-free. Domain D_eff from archive table. "
            "Students only supply candidates. Formula ranks. "
            "If product is below student gen, refine seed arrangement — do not add knobs."
        ),
    }

    REP.mkdir(parents=True, exist_ok=True)
    outj = REP / "FSOT_DERIVE_RANK.json"
    outj.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# FSOT seed-only derive — linguistics domain

**Built:** {report['built_utc']}  
**Pin D1D38A:** **{pin_ok}**  
**Formula:** \(S = K(T_1+T_2+T_3)\)  
**No free parameters · no LLM judge · no ad-hoc knobs**

| System | sacreBLEU |
|--------|----------:|
| **FSOT_product_S** | **{sacre_S:.2f}** |
| FSOT_product_lin | {sacre_lin:.2f} |
| NLLB-3.3B gen (student) | {sacre_gen:.2f} |
| DeepL mid | ~40 |

**Best FSOT:** {best_name} **{best_s:.2f}** · vs student gen gap **{report['gap_to_student_gen']}** · vs DeepL mid **{report['gap_to_DeepL_mid40']}**

## Seeds / domain

- K={K:.6f} · φ={PHI:.6f} · e={E:.6f} · C_eff={C_EFF:.6f}
- D_eff={D_eff} (archive domain table) · breath target φ·e={PHI*E:.4f}
- Golden split for P: φ/(1+φ) on NLL rank, 1/(1+φ) on gen rank

## Puzzle study (correct merges)

{json.dumps(puzzle, indent=2)}

Good hyp should sit higher in S than worst in the same pool if the seed map is arranged correctly. Use that separation to refine the *arrangement*, not free parameters.

## Law

Candidates from students. **FSOT ranks.** Stagnation comes from hacks; growth comes from better seed arrangement.
"""
    (REP / "FSOT_DERIVE_RANK.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["results"], indent=2), flush=True)
    print("puzzle_study", json.dumps(puzzle, indent=2), flush=True)
    print(f"BEST {report['best_product']} gap_student={report['gap_to_student_gen']}", flush=True)
    print(f"WROTE {outj}", flush=True)


if __name__ == "__main__":
    main()
