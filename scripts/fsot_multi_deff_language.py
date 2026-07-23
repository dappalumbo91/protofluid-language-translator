#!/usr/bin/env python3
"""
FSOT multi-D_eff language ranking — intrinsic domain spectrum.

Like particle physics vs cosmology, language is not one D_eff.
Archive domains already encode that spectrum. We evaluate each hyp under
several language-related D_eff values from the domain *table only*, then
associate with seed weights.

No free-fit of D. No new knobs. No LLM judges.

Spectrum (from archive DOMAINS, language-adjacent):
  Acoustics 10, Optics 10, Quantum_Optics 11, Biology 12,
  Neuroscience 14, Psychology 16, Sociology 18 (culture/symbolism)

For each hyp:
  S(D) = K(T1+T2+T3) at that D_eff (seed map of observables)
  S_maxD  = max_D S(D)           # which dimensional regime fits this hyp
  S_spec  = Σ_i S(D_i) / φ^i  / Z  # golden spectrum association
  S_tri   = (S_mean + S_ac/φ + S_vis/φ²)/2  # prior 3-aspect

Product candidates: argmax each; report best under law.
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
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
FEAT = ROOT / "pflt-Ada" / "data" / "fsot_feat_cache"
REP = ROOT / "pflt-Ada" / "reports"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
LETTER_RE = re.compile(r"[A-Za-zÀ-ÿ]")

NLLB33_KEYS = [
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
]

# Language-adjacent domains: (name, role) — D_eff taken from archive table only
LANG_DOMAIN_NAMES = [
    "Acoustics",  # sound / vibration
    "Optics",  # written / visual
    "Quantum_Optics",  # fine structure of form
    "Biology",  # living meaning baseline
    "Neuroscience",  # understanding / mind
    "Psychology",  # culture / affect
    "Sociology",  # shared symbolism
]


def toks(t: str) -> List[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def load_authority():
    from fsot_law_bridge import AUTHORITY_SHA256, find_authority_compute

    path = find_authority_compute()
    if path is None:
        raise RuntimeError("fsot_compute missing")
    dig = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    pin_ok = dig == AUTHORITY_SHA256
    spec = importlib.util.spec_from_file_location("fsot_compute_authority", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["fsot_compute_authority"] = mod
    spec.loader.exec_module(mod)
    return mod, path, pin_ok, dig


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
    T3 = valve * acoustic * (1 + s_in.B_in * s_in.P_var)
    S = mod.K * (T1 + T2 + T3)
    return float(S), float(T1), float(T2), float(T3)


def rank01(vals: List[float], *, higher_better: bool) -> List[float]:
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-15:
        return [0.5] * len(vals)
    if higher_better:
        return [(v - lo) / (hi - lo) for v in vals]
    return [(hi - v) / (hi - lo) for v in vals]


def map_at_D(
    mod,
    *,
    D_eff: float,
    nll_rank: float,
    enc_rank: float,
    gen_rank: float,
    enc_norm: float,
    spm_ent_norm: float,
    spm_mean_len: float,
    spm_n_pieces: int,
    spm_unk_frac: float,
    hyp_len_tok: int,
    src_len_tok: int,
    letter_frac: float,
):
    """Seed-only ScalarInput at a given archive D_eff."""
    from mpmath import mpf

    PHI = float(mod.PHI)
    E = float(mod.E)
    C_EFF = float(mod.C_EFF)
    PI = float(mod.PI)
    BREATH = PHI * E

    n_abs = enc_norm / (enc_norm + PHI + 1e-15)
    N = PHI * (C_EFF + enc_rank + n_abs) / (1.0 + C_EFF)
    w_nll = PHI / (1.0 + PHI)
    w_gen = 1.0 / (1.0 + PHI)
    rank_p = w_nll * nll_rank + w_gen * gen_rank
    P = C_EFF * (1.0 + rank_p * PHI)

    ls, lh = max(1, src_len_tok), max(1, hyp_len_tok)
    len_phase = abs(math.log1p(lh) - math.log1p(ls)) / PHI
    nll_stress = (1.0 - nll_rank) / PHI
    # meaning stress softens with confidence; visual letter mass via 1/φ
    vis_stress = abs(letter_frac - 1.0 / PHI) / PHI
    delta_psi = min(
        (len_phase + nll_stress + vis_stress) * (1.0 - gen_rank / PHI),
        PI / 2,
    )
    breath = abs(spm_mean_len - BREATH) / max(BREATH, 1e-9)
    delta_theta = min(
        (breath + (1.0 - spm_ent_norm) / PHI + spm_unk_frac * PHI)
        * (1.0 - gen_rank / (PHI + 1.0)),
        PI / 2,
    )
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


def spectrum_S(Ss: List[float], PHI: float) -> float:
    """Σ S_i / φ^i  normalized by Σ 1/φ^i (seed geometric series)."""
    num = 0.0
    den = 0.0
    w = 1.0
    for S in Ss:
        num += S * w
        den += w
        w /= PHI
    return num / max(den, 1e-15)


def load_rows(key: str, n: int):
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["rows"] if "rows" in d and d.get("n_src") == n else None


def load_feats(name: str, n: int):
    p = FEAT / f"{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    feats = d.get("feats")
    return feats if feats and len(feats) == n else None


def main() -> None:
    t0 = time.perf_counter()
    print("=== FSOT multi-D_eff language spectrum ===", flush=True)
    mod, path, pin_ok, dig = load_authority()
    PHI, K = float(mod.PHI), float(mod.K)
    domains = getattr(mod, "DOMAINS", {}) or {}

    # Resolve D_eff list strictly from archive table
    spectrum: List[Tuple[str, float]] = []
    for name in LANG_DOMAIN_NAMES:
        if name in domains:
            spectrum.append((name, float(domains[name].D_eff)))
    # unique D values keep first name
    seen = set()
    spectrum_u: List[Tuple[str, float]] = []
    for name, D in spectrum:
        if D not in seen:
            seen.add(D)
            spectrum_u.append((name, D))
    spectrum = spectrum_u
    print(f"pin_ok={pin_ok} spectrum={spectrum}", flush=True)

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
                pools[i].append({"hyp": h, "gen": float(s)})
    for i in range(n):
        best = {}
        for c in pools[i]:
            h = c["hyp"]
            if h not in best or c["gen"] > best[h]["gen"]:
                best[h] = c
        pools[i] = list(best.values())

    feats = load_feats("feat_nllb33_v3", n) or load_feats("feat_nllb33_v2", n)
    if feats is None:
        raise RuntimeError("feat cache required")
    feat_by_hyp = [{f["hyp"]: f for f in feats[i] if f.get("hyp")} for i in range(n)]

    hyps_maxD, hyps_spec, hyps_gen = [], [], []
    # also meaning-only at Biology D for comparison
    hyps_bio = []
    mean_Smax = mean_Sspec = 0.0
    n_scored = 0
    domain_win = {name: 0 for name, _ in spectrum}
    samples = []

    for i in range(n):
        cands = pools[i]
        if not cands:
            hyps_maxD.append("")
            hyps_spec.append("")
            hyps_gen.append("")
            hyps_bio.append("")
            continue

        nlls, encs, gens = [], [], []
        for c in cands:
            f = feat_by_hyp[i].get(c["hyp"], {})
            nlls.append(float(f.get("tf_nll", 5.0)))
            encs.append(float(f.get("enc_norm", 1.0)))
            gens.append(c["gen"])
        nr = rank01(nlls, higher_better=False)
        er = rank01(encs, higher_better=True)
        gr = rank01(gens, higher_better=True)

        scored = []
        for j, c in enumerate(cands):
            f = feat_by_hyp[i].get(c["hyp"], {})
            hyp = c["hyp"]
            letter_frac = len(LETTER_RE.findall(hyp)) / max(1, len(hyp))
            kw = dict(
                nll_rank=nr[j],
                enc_rank=er[j],
                gen_rank=gr[j],
                enc_norm=float(f.get("enc_norm", encs[j])),
                spm_ent_norm=float(f.get("spm_ent_norm", 1 / PHI)),
                spm_mean_len=float(f.get("spm_mean_len", PHI * float(mod.E))),
                spm_n_pieces=int(f.get("spm_n_pieces", max(1, len(toks(hyp))))),
                spm_unk_frac=float(f.get("spm_unk_frac", 0.0)),
                hyp_len_tok=int(f.get("hyp_len_tok", len(toks(hyp)))),
                src_len_tok=int(f.get("src_len_tok", len(toks(srcs[i])))),
                letter_frac=letter_frac,
            )
            S_by_D = []
            S_by_name = {}
            for name, D in spectrum:
                s_in = map_at_D(mod, D_eff=D, **kw)
                S, T1, T2, T3 = split_terms(mod, s_in)
                S_by_D.append(S)
                S_by_name[name] = S
            S_max = max(S_by_D)
            win_name = spectrum[S_by_D.index(S_max)][0]
            S_sp = spectrum_S(S_by_D, PHI)
            S_bio = S_by_name.get("Biology", S_max)
            scored.append(
                {
                    "hyp": hyp,
                    "S_maxD": S_max,
                    "S_spec": S_sp,
                    "S_bio": S_bio,
                    "win_domain": win_name,
                    "gen": c["gen"],
                    "S_by_name": S_by_name,
                }
            )
            mean_Smax += S_max
            mean_Sspec += S_sp
            n_scored += 1

        bmax = max(scored, key=lambda x: x["S_maxD"])
        bspec = max(scored, key=lambda x: x["S_spec"])
        bbio = max(scored, key=lambda x: x["S_bio"])
        bgen = max(scored, key=lambda x: x["gen"])
        hyps_maxD.append(bmax["hyp"])
        hyps_spec.append(bspec["hyp"])
        hyps_bio.append(bbio["hyp"])
        hyps_gen.append(bgen["hyp"])
        domain_win[bmax["win_domain"]] = domain_win.get(bmax["win_domain"], 0) + 1

        if i < 2 or i in (1000, 2000):
            samples.append(
                {
                    "i": i,
                    "S_maxD": bmax["S_maxD"],
                    "win_domain": bmax["win_domain"],
                    "S_spec": bspec["S_spec"],
                    "pick": bmax["hyp"][:80],
                }
            )
        if i % 500 == 0:
            print(
                f"  {i}/{n} maxD={bmax['S_maxD']:.4f} @{bmax['win_domain']} "
                f"spec={bspec['S_spec']:.4f}",
                flush=True,
            )

    s_max = sacrebleu.corpus_bleu(hyps_maxD, [refs]).score
    s_spec = sacrebleu.corpus_bleu(hyps_spec, [refs]).score
    s_bio = sacrebleu.corpus_bleu(hyps_bio, [refs]).score
    s_gen = sacrebleu.corpus_bleu(hyps_gen, [refs]).score
    # seed lin at best single D from previous work was Biology — keep
    products = {
        "FSOT_product_maxD": s_max,
        "FSOT_product_spectrum": s_spec,
        "FSOT_product_biology_D": s_bio,
        "student_gen_max": s_gen,
    }
    best_name = max(
        ("FSOT_product_maxD", s_max),
        ("FSOT_product_spectrum", s_spec),
        ("FSOT_product_biology_D", s_bio),
        key=lambda x: x[1],
    )

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "FSOT multi-D_eff language — spectrum from archive domains",
        "formula": "S=K(T1+T2+T3) at each table D_eff; associate via φ spectrum or max_D",
        "pin": "D1D38A",
        "pin_ok": pin_ok,
        "authority_path": str(path),
        "spectrum": [{"domain": n, "D_eff": D} for n, D in spectrum],
        "domain_win_counts": domain_win,
        "no_free_parameters": True,
        "n": n,
        "mean_S_maxD": mean_Smax / max(1, n_scored),
        "mean_S_spectrum": mean_Sspec / max(1, n_scored),
        "results": {
            "FSOT_product_maxD": {
                "sacrebleu": round(s_max, 2),
                "note": "argmax max_D S(D) — hyp lives in best dimensional regime",
            },
            "FSOT_product_spectrum": {
                "sacrebleu": round(s_spec, 2),
                "note": "argmax golden spectrum Σ S(D_i)/φ^i",
            },
            "FSOT_product_biology_D": {
                "sacrebleu": round(s_bio, 2),
                "note": "argmax S at Biology D_eff only",
            },
            "student_gen_max": {
                "sacrebleu": round(s_gen, 2),
                "note": "NLLB-3.3B gen baseline",
            },
        },
        "best_product": {"name": best_name[0], "sacrebleu": round(best_name[1], 2)},
        "gap_to_DeepL_mid40": round(40.0 - best_name[1], 2),
        "gap_to_student_gen": round(s_gen - best_name[1], 2),
        "samples": samples,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "honesty": (
            "D_eff values only from archive DOMAINS table. Different language aspects "
            "live at different D like physics domains. No free-fit D. No LLM."
        ),
    }

    REP.mkdir(parents=True, exist_ok=True)
    outj = REP / "FSOT_MULTI_DEFF.json"
    outj.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# FSOT multi-D_eff language spectrum

**Built:** {report['built_utc']}  
**Pin D1D38A:** {pin_ok}  

Language is not one \(D_{{\\mathrm{{eff}}}}\). Like particle physics vs cosmology,
meaning / sound / culture sit at different archive dimensions.

## Spectrum (table only)

| Domain | D_eff | Wins (maxD pick) |
|--------|------:|-----------------:|
"""
    for name, D in spectrum:
        md += f"| {name} | {D} | {domain_win.get(name, 0)} |\n"
    md += f"""
## Association

- **maxD:** \(S = \\max_{{D \\in \\mathrm{{table}}}} S(D)\) — which regime fits this hyp  
- **spectrum:** \(S = \\sum_i S(D_i)\\,/\\,\\varphi^i\\; /\\; Z\) — golden stack across regimes  

## Results

| System | sacreBLEU |
|--------|----------:|
| **{best_name[0]}** | **{best_name[1]:.2f}** |
| FSOT_product_maxD | {s_max:.2f} |
| FSOT_product_spectrum | {s_spec:.2f} |
| FSOT_product_biology_D | {s_bio:.2f} |
| student gen | {s_gen:.2f} |

Gap → DeepL mid-40: **{report['gap_to_DeepL_mid40']}** · vs student: **{report['gap_to_student_gen']}**

No free parameters. Arrange domains; do not invent D.
"""
    (REP / "FSOT_MULTI_DEFF.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["results"], indent=2), flush=True)
    print(f"domain_wins {domain_win}", flush=True)
    print(f"BEST {report['best_product']}", flush=True)
    print(f"WROTE {outj}", flush=True)


if __name__ == "__main__":
    main()
