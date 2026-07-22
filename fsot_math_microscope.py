#!/usr/bin/env python3
"""
FSOT 2.1 Math Microscope for PFLT.

Traces every intermediate of S = K·(T1+T2+T3) with named steps so reasoning
pathways can be inspected like a formula microscope, exported to Mathematica,
and cross-checked against Lean / Coq / Isabelle / F* golden values.

Authority: PFLT_FSOT_2_1_aligned.compute_S_D_chaotic (mpmath dps=50).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mpmath import mp, mpf, sqrt, cos, sin, exp, ln, pi as MP_PI, e as MP_E

mp.dps = 50

DATA = Path(__file__).resolve().parent / "data"
OUT_DIR = DATA / "math_microscope"
FORMAL_DIR = Path(__file__).resolve().parent / "formal"
MATHEMATICA_DIR = Path(__file__).resolve().parent / "mathematica"

# ---------------------------------------------------------------------------
# Seed constants + Layer-1/2 (same expressions as PFLT_FSOT_2_1_aligned)
# ---------------------------------------------------------------------------
PI = MP_PI
E = MP_E
PHI = (1 + sqrt(5)) / 2
GAMMA = mpf("0.57721566490153286060651209008240243104215933593992")
G_CAT = mpf("0.91596559417721901505460351493238411077414937428167")

ALPHA = ln(PI) / (E * PHI**13)
PSI_CON = 1 - 1 / E
ETA_EFF = 1 / (PI - 1)
BETA = exp(-(PI**PI + (E - 1)))
GAMMA_C = -ln(2) / PHI
OMEGA = sin(PI / E) * sqrt(2)
THETA_S = sin(PSI_CON * ETA_EFF)
POOF = exp((-ln(PI) / E) / (ETA_EFF * ln(PHI)))
C_EFF = (1 - POOF * sin(THETA_S)) * (1 + mpf("0.01") * G_CAT / (PI * PHI))
A_BLEED = sin(PI / E) * PHI / sqrt(2)
P_VAR = -cos(THETA_S + PI)
B_IN = C_EFF * (1 - sin(THETA_S) / PHI)
A_IN = A_BLEED * (1 + cos(THETA_S) / PHI)
SUCTION = POOF * (-cos(THETA_S - PI))
CHAOS = GAMMA_C / OMEGA
P_BASE = GAMMA / E
P_NEW = P_BASE * sqrt(2)
C_FACTOR = C_EFF * P_NEW
K = PHI * (GAMMA / E) * sqrt(2) / ln(PI) * mpf("0.99")


def _f(x) -> float:
    return float(x)


@dataclass
class MathStep:
    """One microscope step: name, symbolic expression, numeric value."""
    id: str
    name: str
    expr: str
    value: float
    layer: str  # seed | L1 | L2 | input | T1 | T2 | T3 | combine
    notes: str = ""


@dataclass
class MathTrace:
    """Full granular FSOT trace for one domain/input configuration."""
    built_utc: str
    domain: str
    inputs: Dict[str, Any]
    steps: List[MathStep] = field(default_factory=list)
    panel: Dict[str, float] = field(default_factory=dict)
    formula: str = "S = K * (T1 + T2 + T3)"
    authority: str = "PFLT_FSOT_2_1_aligned + FSOT.Scalar.lean / NeuroLab"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "built_utc": self.built_utc,
            "domain": self.domain,
            "formula": self.formula,
            "authority": self.authority,
            "inputs": self.inputs,
            "panel": self.panel,
            "steps": [asdict(s) for s in self.steps],
        }

    def step_map(self) -> Dict[str, float]:
        return {s.id: s.value for s in self.steps}


def _add(
    steps: List[MathStep],
    sid: str,
    name: str,
    expr: str,
    value,
    layer: str,
    notes: str = "",
) -> None:
    steps.append(
        MathStep(
            id=sid,
            name=name,
            expr=expr,
            value=_f(value),
            layer=layer,
            notes=notes,
        )
    )


def trace_constants() -> List[MathStep]:
    """Microscope over seed + derived constants only."""
    steps: List[MathStep] = []
    _add(steps, "pi", "π", "Pi", PI, "seed")
    _add(steps, "e", "e", "E", E, "seed")
    _add(steps, "phi", "φ golden ratio", "(1+Sqrt[5])/2", PHI, "seed")
    _add(steps, "gamma", "γ Euler-Mascheroni", "EulerGamma", GAMMA, "seed")
    _add(steps, "G_cat", "G Catalan", "Catalan", G_CAT, "seed")
    _add(steps, "alpha", "α damping", "Log[π]/(e·φ^13)", ALPHA, "L1")
    _add(steps, "psi_con", "ψ_con consciousness baseline", "1-1/e", PSI_CON, "L1")
    _add(steps, "eta_eff", "η_eff efficiency", "1/(π-1)", ETA_EFF, "L1")
    _add(steps, "beta", "β perturbation", "Exp[-(π^π+(e-1))]", BETA, "L1")
    _add(steps, "gamma_c", "γ_c perception damping", "-Log[2]/φ", GAMMA_C, "L1")
    _add(steps, "omega", "ω oscillation", "Sin[π/e]·√2", OMEGA, "L1")
    _add(steps, "theta_s", "θ_s phase", "Sin[ψ_con·η_eff]", THETA_S, "L2")
    _add(steps, "poof", "poof / tunnel factor", "Exp[(-Log[π]/e)/(η_eff·Log[φ])]", POOF, "L2")
    _add(steps, "c_eff", "coherence efficiency", "(1-poof·Sin[θ_s])·(1+0.01·G/(π·φ))", C_EFF, "L2")
    _add(steps, "a_bleed", "acoustic bleed", "Sin[π/e]·φ/√2", A_BLEED, "L2")
    _add(steps, "p_var", "phase variance", "-Cos[θ_s+π]", P_VAR, "L2")
    _add(steps, "b_in", "bleed-in factor", "c_eff·(1-Sin[θ_s]/φ)", B_IN, "L2")
    _add(steps, "a_in", "acoustic inflow", "a_bleed·(1+Cos[θ_s]/φ)", A_IN, "L2")
    _add(steps, "suction", "suction factor", "poof·(-Cos[θ_s-π])", SUCTION, "L2")
    _add(steps, "chaos", "chaos factor", "γ_c/ω", CHAOS, "L2")
    _add(steps, "p_base", "perceived param base", "γ/e", P_BASE, "L2")
    _add(steps, "p_new", "new perceived param", "p_base·√2", P_NEW, "L2")
    _add(steps, "c_factor", "consciousness factor", "c_eff·p_new", C_FACTOR, "L2")
    _add(steps, "K", "universal scale K", "φ·(γ/e)·√2/Log[π]·0.99", K, "L2", "≈0.4202")
    return steps


def trace_scalar(
    *,
    domain: str = "linguistic",
    N: float = 1.0,
    P: float = 1.0,
    D_eff: float = 12.0,
    recent_hits: float = 0.0,
    delta_psi: float = 0.8,
    delta_theta: float = 1.0,
    rho: float = 1.0,
    scale: float = 1.0,
    amplitude: float = 1.0,
    trend_bias: float = 0.0,
    observed: bool = True,
) -> MathTrace:
    """Full microscope trace for one scalar evaluation."""
    steps = trace_constants()
    N_m, P_m, D_m = mpf(N), mpf(P), mpf(D_eff)
    hits = mpf(recent_hits)
    dp, dt = mpf(delta_psi), mpf(delta_theta)

    _add(steps, "N", "N agents/tokens", "N", N_m, "input")
    _add(steps, "P", "P pressure/priority", "P", P_m, "input")
    _add(steps, "D_eff", "effective dimension", "D_eff", D_m, "input", f"domain={domain}")
    _add(steps, "recent_hits", "recent hits", "recent_hits", hits, "input")
    _add(steps, "delta_psi", "Δψ phase drive", "delta_psi", dp, "input")
    _add(steps, "delta_theta", "Δθ angle drive", "delta_theta", dt, "input")
    _add(steps, "rho", "ρ density", "rho", rho, "input")
    _add(steps, "observed", "observer flag", "observed", 1 if observed else 0, "input")

    # --- T1 pathway ---
    growth = exp(ALPHA * (1 - hits / N_m) * GAMMA / PHI)
    _add(
        steps,
        "growth",
        "growth term",
        "Exp[α·(1-hits/N)·γ/φ]",
        growth,
        "T1",
    )
    np_over_sqrt = N_m * P_m / sqrt(D_m)
    _add(steps, "np_sqrtD", "N·P/√D_eff", "N*P/Sqrt[D_eff]", np_over_sqrt, "T1")
    cos_term = cos((PSI_CON + dp) / ETA_EFF)
    _add(
        steps,
        "cos_psi",
        "cos((ψ_con+Δψ)/η_eff)",
        "Cos[(ψ_con+Δψ)/η_eff]",
        cos_term,
        "T1",
    )
    exp_term = exp(-ALPHA * hits / N_m + mpf(rho) + B_IN * dp)
    _add(
        steps,
        "exp_damp",
        "exp(-α·hits/N + ρ + b_in·Δψ)",
        "Exp[-α*hits/N + ρ + b_in*Δψ]",
        exp_term,
        "T1",
    )
    coh_term = 1 + growth * C_EFF
    _add(steps, "coh_term", "1+growth·c_eff", "1+growth*c_eff", coh_term, "T1")
    base = np_over_sqrt * cos_term * exp_term * coh_term
    _add(steps, "base", "T1 base (pre D-scale)", "np_sqrtD*cos*exp*coh", base, "T1")
    d_scale = 1 + P_NEW * ln(D_m / 25)
    _add(steps, "d_scale", "1+p_new·ln(D/25)", "1+p_new*Log[D/25]", d_scale, "T1")
    T1 = base * d_scale
    qm = mpf(1)
    if observed:
        qm = exp(C_FACTOR * P_VAR) * cos(dp + P_VAR)
        _add(
            steps,
            "quirk_mod",
            "observer quirk_mod",
            "Exp[c_factor*p_var]*Cos[Δψ+p_var]",
            qm,
            "T1",
            "applied only when observed=True",
        )
        T1 = T1 * qm
    else:
        _add(steps, "quirk_mod", "observer quirk_mod", "1 (unobserved)", 1.0, "T1")
    _add(steps, "T1", "T1 term", "base*d_scale*quirk_mod", T1, "T1")

    # --- T2 pathway ---
    T2 = mpf(scale) * mpf(amplitude) + mpf(trend_bias)
    _add(steps, "T2", "T2 term", "scale*amplitude + trend_bias", T2, "T2")

    # --- T3 pathway ---
    chaos_mod = 1 + CHAOS * (D_m - 25) / 25
    _add(steps, "chaos_mod", "1+chaos·(D-25)/25", "1+chaos*(D-25)/25", chaos_mod, "T3")
    poof_mod = 1 + POOF * cos(THETA_S + PI) + SUCTION * sin(THETA_S)
    _add(
        steps,
        "poof_mod",
        "1+poof·Cos[θ_s+π]+suction·Sin[θ_s]",
        "1+poof*Cos[θs+π]+suction*Sin[θs]",
        poof_mod,
        "T3",
    )
    valve = BETA * cos(dp) * np_over_sqrt * chaos_mod * poof_mod
    _add(steps, "valve", "β·Cos[Δψ]·(N P/√D)·chaos·poof", "valve", valve, "T3")
    acoustic = 1 + (A_BLEED * sin(dt) ** 2) / PHI + (A_IN * cos(dt) ** 2) / PHI
    _add(
        steps,
        "acoustic",
        "1+(a_bleed·Sin²Δθ)/φ+(a_in·Cos²Δθ)/φ",
        "acoustic",
        acoustic,
        "T3",
    )
    phase = 1 + B_IN * P_VAR
    _add(steps, "phase", "1+b_in·p_var", "1+b_in*p_var", phase, "T3")
    T3 = valve * acoustic * phase
    _add(steps, "T3", "T3 term", "valve*acoustic*phase", T3, "T3")

    raw = T1 + T2 + T3
    _add(steps, "raw", "T1+T2+T3", "T1+T2+T3", raw, "combine")
    S = K * raw
    _add(steps, "S", "FSOT coherence scalar", "K*(T1+T2+T3)", S, "combine", "final")

    return MathTrace(
        built_utc=datetime.now(timezone.utc).isoformat(),
        domain=domain,
        inputs={
            "N": N,
            "P": P,
            "D_eff": D_eff,
            "recent_hits": recent_hits,
            "delta_psi": delta_psi,
            "delta_theta": delta_theta,
            "rho": rho,
            "scale": scale,
            "amplitude": amplitude,
            "trend_bias": trend_bias,
            "observed": observed,
        },
        steps=steps,
        panel={
            "S": _f(S),
            "T1": _f(T1),
            "T2": _f(T2),
            "T3": _f(T3),
            "K": _f(K),
            "raw": _f(raw),
            "quirk_mod": _f(qm),
            "growth": _f(growth),
        },
    )


def trace_domain(domain: str = "linguistic") -> MathTrace:
    """Trace using PFLT DOMAIN_PARAMS for the named domain."""
    from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, FSOT21_DOMAINS

    p = DOMAIN_PARAMS.get(domain) or FSOT21_DOMAINS.get(domain) or DOMAIN_PARAMS["linguistic"]
    return trace_scalar(
        domain=domain,
        D_eff=float(p.get("D_eff", 12)),
        observed=bool(p.get("observed", True)),
        delta_psi=float(p.get("delta_psi", 0.8)),
        delta_theta=float(p.get("delta_theta", 1.0)),
        recent_hits=float(p.get("recent_hits") or 0),
    )


def export_mathematica(trace: MathTrace, path: Optional[Path] = None) -> Path:
    """Write a .wl script that recomputes the same pathway with Print steps."""
    MATHEMATICA_DIR.mkdir(parents=True, exist_ok=True)
    path = path or MATHEMATICA_DIR / f"trace_{trace.domain}.wl"
    lines = [
        "(* Auto-generated FSOT 2.1 Math Microscope for PFLT *)",
        f"(* domain = {trace.domain}  built = {trace.built_utc} *)",
        "(* Formula: S = K*(T1+T2+T3)  — zero free params beyond seeds *)",
        "ClearAll[FSOTTrace, FSOTConstants, FSOTScalar];",
        "",
        "FSOTConstants[] := Module[{},",
        "  Association[",
    ]
    for s in trace.steps:
        if s.layer in {"seed", "L1", "L2"}:
            lines.append(f'    "{s.id}" -> {s.value:.17g}, (* {s.expr} *)')
    lines.append("    \"end\" -> True")
    lines.append("  ]];")
    lines.append("")
    lines.append("FSOTTrace[] := Module[{steps = {}, c, add,")
    # inputs
    for k, v in trace.inputs.items():
        if isinstance(v, bool):
            lines.append(f"  {k} = {'True' if v else 'False'};")
        else:
            lines.append(f"  {k} = {float(v):.17g};")
    lines.append("  c = FSOTConstants[];")
    lines.append('  add[id_, val_] := AppendTo[steps, {id, val}];')
    lines.append("  (* --- reconstruct T1/T2/T3 from constants + inputs --- *)")
    lines.append("  phi = c[\"phi\"]; e = c[\"e\"]; pi = c[\"pi\"];")
    lines.append("  alpha = c[\"alpha\"]; psiCon = c[\"psi_con\"]; etaEff = c[\"eta_eff\"];")
    lines.append("  beta = c[\"beta\"]; thetaS = c[\"theta_s\"]; poof = c[\"poof\"];")
    lines.append("  cEff = c[\"c_eff\"]; aBleed = c[\"a_bleed\"]; pVar = c[\"p_var\"];")
    lines.append("  bIn = c[\"b_in\"]; aIn = c[\"a_in\"]; suction = c[\"suction\"];")
    lines.append("  chaos = c[\"chaos\"]; pNew = c[\"p_new\"]; cFactor = c[\"c_factor\"];")
    lines.append("  k = c[\"K\"]; gamma = c[\"gamma\"];")
    lines.append("  growth = Exp[alpha*(1 - recent_hits/N)*gamma/phi]; add[\"growth\", growth];")
    lines.append("  npSqrt = N*P/Sqrt[D_eff]; add[\"np_sqrtD\", npSqrt];")
    lines.append("  cosPsi = Cos[(psiCon + delta_psi)/etaEff]; add[\"cos_psi\", cosPsi];")
    lines.append("  expD = Exp[-alpha*recent_hits/N + rho + bIn*delta_psi]; add[\"exp_damp\", expD];")
    lines.append("  coh = 1 + growth*cEff; add[\"coh_term\", coh];")
    lines.append("  base = npSqrt*cosPsi*expD*coh; add[\"base\", base];")
    lines.append("  dScale = 1 + pNew*Log[D_eff/25]; add[\"d_scale\", dScale];")
    lines.append("  t1 = base*dScale;")
    lines.append("  qm = 1;")
    lines.append("  If[observed, qm = Exp[cFactor*pVar]*Cos[delta_psi + pVar]; t1 = t1*qm];")
    lines.append("  add[\"quirk_mod\", qm]; add[\"T1\", t1];")
    lines.append("  t2 = scale*amplitude + trend_bias; add[\"T2\", t2];")
    lines.append("  chaosMod = 1 + chaos*(D_eff - 25)/25; add[\"chaos_mod\", chaosMod];")
    lines.append("  poofMod = 1 + poof*Cos[thetaS + Pi] + suction*Sin[thetaS]; add[\"poof_mod\", poofMod];")
    lines.append("  valve = beta*Cos[delta_psi]*npSqrt*chaosMod*poofMod; add[\"valve\", valve];")
    lines.append("  acoustic = 1 + (aBleed*Sin[delta_theta]^2)/phi + (aIn*Cos[delta_theta]^2)/phi; add[\"acoustic\", acoustic];")
    lines.append("  phase = 1 + bIn*pVar; add[\"phase\", phase];")
    lines.append("  t3 = valve*acoustic*phase; add[\"T3\", t3];")
    lines.append("  raw = t1 + t2 + t3; add[\"raw\", raw];")
    lines.append("  S = k*raw; add[\"S\", S];")
    lines.append("  Association[\"domain\" -> \"" + trace.domain + "\", \"S\" -> S, \"T1\" -> t1, \"T2\" -> t2, \"T3\" -> t3, \"steps\" -> steps]")
    lines.append("];")
    lines.append("")
    lines.append("(* Python microscope reference panel for cross-check *)")
    lines.append(f'FSOTPythonPanel = <|"S" -> {trace.panel["S"]:.17g}, "T1" -> {trace.panel["T1"]:.17g}, "T2" -> {trace.panel["T2"]:.17g}, "T3" -> {trace.panel["T3"]:.17g}|>;')
    lines.append("FSOTDiff[] := Module[{m = FSOTTrace[]},")
    lines.append('  Association["dS" -> Abs[m["S"] - FSOTPythonPanel["S"]],')
    lines.append('    "dT1" -> Abs[m["T1"] - FSOTPythonPanel["T1"]],')
    lines.append('    "dT2" -> Abs[m["T2"] - FSOTPythonPanel["T2"]],')
    lines.append('    "dT3" -> Abs[m["T3"] - FSOTPythonPanel["T3"]]]];')
    lines.append("")
    lines.append("(* Usage: FSOTTrace[]  or  FSOTDiff[] *)")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_golden_for_formal(
    domains: Optional[Sequence[str]] = None,
    path: Optional[Path] = None,
) -> Path:
    """
    Golden numeric fixtures for Lean / Coq / Isabelle / F* parity.
    """
    FORMAL_DIR.mkdir(parents=True, exist_ok=True)
    domains = list(domains or ("linguistic", "historical", "mythological", "quantum", "cosmological"))
    fixtures = []
    for d in domains:
        tr = trace_domain(d)
        fixtures.append(
            {
                "domain": d,
                "inputs": tr.inputs,
                "panel": tr.panel,
                "step_ids": [s.id for s in tr.steps],
                "K": tr.panel["K"],
                "S": tr.panel["S"],
                "T1": tr.panel["T1"],
                "T2": tr.panel["T2"],
                "T3": tr.panel["T3"],
            }
        )
    # also constant snapshot
    const_steps = {s.id: s.value for s in trace_constants()}
    payload = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "S = K*(T1+T2+T3)",
        "eps_f64": 1e-10,
        "eps_mp50_to_f64": 1e-12,
        "constants": const_steps,
        "fixtures": fixtures,
        "formal_backends": {
            "lean": {
                "path_hint": r"C:\Users\damia\Desktop\FSOT-2.1-Lean",
                "entry": "FSOT2_0.compute_S_D_chaotic / FSOT.Scalar",
                "check": "compare S,T1,T2,T3 within eps_f64",
            },
            "coq": {
                "path_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\coq",
                "entry": "Trinary.v (+ scalar stubs)",
                "check": "extract float or Q compare vs golden",
            },
            "isabelle": {
                "path_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\isabelle",
                "entry": "Trinary.thy",
                "check": "value/export compare vs golden.json",
            },
            "fstar": {
                "path_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\fstar",
                "entry": "FSOTGpuBoot.fst",
                "check": "extract OCaml/F# compare vs golden",
            },
            "mathematica": {
                "path_hint": str(MATHEMATICA_DIR),
                "entry": "FSOT_PFLT_Microscope.wl + trace_*.wl",
                "check": "FSOTDiff[] vs FSOTPythonPanel",
            },
        },
        "lab_parity_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\parity\golden.json",
    }
    path = path or FORMAL_DIR / "golden_fsot_pflt.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def compare_to_lab_golden(lab_path: Optional[Path] = None) -> Dict[str, Any]:
    """Cross-check key constants against GPU-lab golden.json if present."""
    lab_path = lab_path or Path(
        r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\parity\golden.json"
    )
    ours = {s.id: s.value for s in trace_constants()}
    report: Dict[str, Any] = {
        "lab_path": str(lab_path),
        "lab_present": lab_path.exists(),
        "comparisons": [],
    }
    if not lab_path.exists():
        report["note"] = "lab golden.json not found"
        return report
    lab = json.loads(lab_path.read_text(encoding="utf-8"))
    seeds = lab.get("seeds") or {}
    mapping = {
        "phi": "phi",
        "gamma": "gamma",
        "K": "k",
        "c_eff": "c_eff",
        "p_var": "p_var",
        "psi_con": "psi_con",
    }
    for our_id, lab_key in mapping.items():
        if lab_key not in seeds:
            continue
        a, b = ours[our_id], float(seeds[lab_key])
        report["comparisons"].append(
            {
                "id": our_id,
                "pflt": a,
                "lab": b,
                "abs_diff": abs(a - b),
                "ok": abs(a - b) < 1e-9,
            }
        )
    # scalar sample if present
    if "scalar_observed_D8_dp0_7" in lab:
        tr = trace_scalar(
            domain="lab_sample",
            D_eff=8,
            delta_psi=0.7,
            observed=True,
        )
        report["scalar_sample"] = {
            "pflt_S": tr.panel["S"],
            "lab_S": lab["scalar_observed_D8_dp0_7"],
            "abs_diff": abs(tr.panel["S"] - lab["scalar_observed_D8_dp0_7"]),
        }
    report["all_ok"] = all(c.get("ok") for c in report["comparisons"]) if report["comparisons"] else False
    return report


def layer_groups(trace: MathTrace) -> Dict[str, List[Dict[str, Any]]]:
    """Group steps by layer for microscope-style inspection."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for s in trace.steps:
        groups.setdefault(s.layer, []).append(
            {"id": s.id, "name": s.name, "expr": s.expr, "value": s.value, "notes": s.notes}
        )
    return groups


def pathway_summary(trace: MathTrace) -> Dict[str, Any]:
    """Compact T1/T2/T3 pathway view for failure logs (readable microscope)."""
    sm = trace.step_map()
    return {
        "formula": trace.formula,
        "domain": trace.domain,
        "inputs": trace.inputs,
        "panel": trace.panel,
        "pathway": {
            "seeds": {k: sm[k] for k in ("pi", "e", "phi", "gamma", "G_cat") if k in sm},
            "K": sm.get("K"),
            "T1_chain": {
                "growth": sm.get("growth"),
                "np_sqrtD": sm.get("np_sqrtD"),
                "cos_psi": sm.get("cos_psi"),
                "exp_damp": sm.get("exp_damp"),
                "coh_term": sm.get("coh_term"),
                "base": sm.get("base"),
                "d_scale": sm.get("d_scale"),
                "quirk_mod": sm.get("quirk_mod"),
                "T1": sm.get("T1"),
            },
            "T2": sm.get("T2"),
            "T3_chain": {
                "chaos_mod": sm.get("chaos_mod"),
                "poof_mod": sm.get("poof_mod"),
                "valve": sm.get("valve"),
                "acoustic": sm.get("acoustic"),
                "phase": sm.get("phase"),
                "T3": sm.get("T3"),
            },
            "combine": {"raw": sm.get("raw"), "S": sm.get("S")},
        },
        "layer_counts": {layer: len(items) for layer, items in layer_groups(trace).items()},
    }


def verify_vs_authority(
    domains: Optional[Sequence[str]] = None,
    eps: float = 1e-12,
) -> Dict[str, Any]:
    """
    Cross-check microscope numeric panel against PFLT compute_S_D_chaotic.
    Authority remains PFLT_FSOT_2_1_aligned (mpmath dps=50).
    """
    from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, FSOT21_DOMAINS, compute_S_D_chaotic

    domains = list(domains or ("linguistic", "historical", "mythological", "quantum", "cosmological"))
    rows = []
    for d in domains:
        p = DOMAIN_PARAMS.get(d) or FSOT21_DOMAINS.get(d) or DOMAIN_PARAMS["linguistic"]
        kwargs = dict(
            D_eff=float(p.get("D_eff", 12)),
            observed=bool(p.get("observed", True)),
            delta_psi=float(p.get("delta_psi", 0.8)),
            delta_theta=float(p.get("delta_theta", 1.0)),
            recent_hits=float(p.get("recent_hits") or 0),
        )
        panel = compute_S_D_chaotic(**kwargs)
        tr = trace_domain(d)
        row = {
            "domain": d,
            "microscope_S": tr.panel["S"],
            "authority_S": panel.S,
            "dS": abs(tr.panel["S"] - panel.S),
            "dT1": abs(tr.panel["T1"] - panel.T1),
            "dT2": abs(tr.panel["T2"] - panel.T2),
            "dT3": abs(tr.panel["T3"] - panel.T3),
            "ok": (
                abs(tr.panel["S"] - panel.S) < eps
                and abs(tr.panel["T1"] - panel.T1) < eps
                and abs(tr.panel["T2"] - panel.T2) < eps
                and abs(tr.panel["T3"] - panel.T3) < eps
            ),
        }
        rows.append(row)
    return {
        "eps": eps,
        "all_ok": all(r["ok"] for r in rows),
        "domains": rows,
        "authority": "PFLT_FSOT_2_1_aligned.compute_S_D_chaotic",
    }


def write_failure_math_log(
    *,
    domain: str,
    token: str,
    meaning: str,
    exact: bool,
    resolution: str = "",
    input_text: str = "",
    path: Optional[Path] = None,
    export_wl: bool = True,
) -> Path:
    """
    Attach math microscope to a translation failure for granular debug.

    Writes a failure JSON with full step list + compact pathway summary so you
    can see how S=K(T1+T2+T3) was applied on the domain that routed the miss.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MATHEMATICA_DIR.mkdir(parents=True, exist_ok=True)
    tr = trace_domain(domain)
    safe_tok = re.sub(r"[^\w\-.\u0370-\u03ff]+", "_", token)[:48] or "tok"
    payload = {
        "kind": "translation_failure_math",
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "token": token,
        "meaning": meaning,
        "exact": exact,
        "resolution": resolution or ("exact" if exact else "fallback_or_inferred"),
        "domain": domain,
        "input_text": input_text,
        "pathway": pathway_summary(tr),
        "layers": layer_groups(tr),
        "math_full": tr.to_dict(),
        "formal_cross_verify": {
            "golden": str(FORMAL_DIR / "golden_fsot_pflt.json"),
            "lab_parity": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\parity\golden.json",
            "lean_hint": r"C:\Users\damia\Desktop\FSOT-2.1-Lean",
            "coq_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\coq",
            "isabelle_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\isabelle",
            "fstar_hint": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\fstar",
            "mathematica": str(MATHEMATICA_DIR / f"trace_{domain}.wl"),
            "usage": (
                "1) FSOTDiff[] in Mathematica should be ~0 vs Python panel. "
                "2) Assert |S_formal - S_golden| < eps against formal/golden_fsot_pflt.json "
                "in Lean / Coq / Isabelle / F* runners."
            ),
        },
        "note": (
            "Microscope over S=K(T1+T2+T3) for the routed domain. "
            "Cross-verify seeds/K against lab golden + formal backends (Isabelle, Coq, Lean, F*)."
        ),
    }
    path = path or OUT_DIR / f"fail_{domain}_{safe_tok}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if export_wl:
        export_mathematica(tr, MATHEMATICA_DIR / f"trace_{domain}.wl")
    return path


def export_symbolic_mathematica(path: Optional[Path] = None) -> Path:
    """
    Full symbolic rebuild of seeds → L1/L2 → S from Mathematica primitives.
    This is the true formula microscope (not just numeric dump).
    """
    MATHEMATICA_DIR.mkdir(parents=True, exist_ok=True)
    path = path or MATHEMATICA_DIR / "FSOT_Symbolic_Microscope.wl"
    path.write_text(
        "\n".join(
            [
                "(* FSOT 2.1 Symbolic Math Microscope — rebuild from seeds *)",
                "(* Formula: S = K*(T1 + T2 + T3)  — zero free params beyond seeds *)",
                "ClearAll[FSOTSeeds, FSOTDerived, FSOTScalarSym, FSOTPrintPathway];",
                "",
                "FSOTSeeds[] := Association[",
                "  \"pi\" -> Pi,",
                "  \"e\"  -> E,",
                "  \"phi\" -> (1 + Sqrt[5])/2,",
                "  \"gamma\" -> EulerGamma,",
                "  \"G_cat\" -> Catalan",
                "];",
                "",
                "FSOTDerived[] := Module[{s = FSOTSeeds[], pi, e, phi, gamma, G},",
                "  pi = s[\"pi\"]; e = s[\"e\"]; phi = s[\"phi\"]; gamma = s[\"gamma\"]; G = s[\"G_cat\"];",
                "  Association[",
                "    \"alpha\"    -> Log[pi]/(e*phi^13),",
                "    \"psi_con\"  -> 1 - 1/e,",
                "    \"eta_eff\"  -> 1/(pi - 1),",
                "    \"beta\"     -> Exp[-(pi^pi + (e - 1))],",
                "    \"gamma_c\"  -> -Log[2]/phi,",
                "    \"omega\"    -> Sin[pi/e]*Sqrt[2],",
                "    \"theta_s\"  -> Sin[(1 - 1/e)*(1/(pi - 1))],",
                "    \"poof\"     -> Exp[(-Log[pi]/e)/((1/(pi - 1))*Log[phi])],",
                "    \"c_eff\"    -> (1 - Exp[(-Log[pi]/e)/((1/(pi - 1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])",
                "                   *(1 + 0.01*G/(pi*phi)),",
                "    \"a_bleed\"  -> Sin[pi/e]*phi/Sqrt[2],",
                "    \"p_var\"    -> -Cos[Sin[(1-1/e)*(1/(pi-1))] + pi],",
                "    \"b_in\"     -> With[{ce = (1 - Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])*(1+0.01*G/(pi*phi)),",
                "                        ts = Sin[(1-1/e)*(1/(pi-1))]}, ce*(1 - Sin[ts]/phi)],",
                "    \"a_in\"     -> With[{ab = Sin[pi/e]*phi/Sqrt[2], ts = Sin[(1-1/e)*(1/(pi-1))]}, ab*(1 + Cos[ts]/phi)],",
                "    \"suction\"  -> With[{pf = Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])], ts = Sin[(1-1/e)*(1/(pi-1))]}, pf*(-Cos[ts - pi])],",
                "    \"chaos\"    -> (-Log[2]/phi)/(Sin[pi/e]*Sqrt[2]),",
                "    \"p_base\"   -> gamma/e,",
                "    \"p_new\"    -> (gamma/e)*Sqrt[2],",
                "    \"c_factor\" -> With[{ce = (1 - Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])*(1+0.01*G/(pi*phi))},",
                "                    ce*(gamma/e)*Sqrt[2]],",
                "    \"K\"        -> phi*(gamma/e)*Sqrt[2]/Log[pi]*0.99",
                "  ]",
                "];",
                "",
                "(* Numeric domain scalar: same structure as Python microscope *)",
                "FSOTScalarSym[opts:OptionsPattern[{",
                "  N->1., P->1., DEff->12., RecentHits->0., DeltaPsi->0.8, DeltaTheta->1.,",
                "  Rho->1., Scale->1., Amplitude->1., TrendBias->0., Observed->True",
                "}]] := Module[{",
                "  d = FSOTDerived[], s = FSOTSeeds[],",
                "  n, p, de, hits, dp, dt, rho, sc, amp, tb, obs,",
                "  growth, npSqrt, cosPsi, expD, coh, base, dScale, t1, qm, t2,",
                "  chaosMod, poofMod, valve, acoustic, phase, t3, raw, S, steps = {}",
                "  },",
                "  n = OptionValue[N]; p = OptionValue[P]; de = OptionValue[DEff];",
                "  hits = OptionValue[RecentHits]; dp = OptionValue[DeltaPsi]; dt = OptionValue[DeltaTheta];",
                "  rho = OptionValue[Rho]; sc = OptionValue[Scale]; amp = OptionValue[Amplitude];",
                "  tb = OptionValue[TrendBias]; obs = OptionValue[Observed];",
                "  growth = Exp[d[\"alpha\"]*(1 - hits/n)*s[\"gamma\"]/s[\"phi\"]];",
                "  npSqrt = n*p/Sqrt[de];",
                "  cosPsi = Cos[(d[\"psi_con\"] + dp)/d[\"eta_eff\"]];",
                "  expD = Exp[-d[\"alpha\"]*hits/n + rho + d[\"b_in\"]*dp];",
                "  coh = 1 + growth*d[\"c_eff\"];",
                "  base = npSqrt*cosPsi*expD*coh;",
                "  dScale = 1 + d[\"p_new\"]*Log[de/25];",
                "  t1 = base*dScale; qm = 1;",
                "  If[obs, qm = Exp[d[\"c_factor\"]*d[\"p_var\"]]*Cos[dp + d[\"p_var\"]]; t1 = t1*qm];",
                "  t2 = sc*amp + tb;",
                "  chaosMod = 1 + d[\"chaos\"]*(de - 25)/25;",
                "  poofMod = 1 + d[\"poof\"]*Cos[d[\"theta_s\"] + Pi] + d[\"suction\"]*Sin[d[\"theta_s\"]];",
                "  valve = d[\"beta\"]*Cos[dp]*npSqrt*chaosMod*poofMod;",
                "  acoustic = 1 + (d[\"a_bleed\"]*Sin[dt]^2)/s[\"phi\"] + (d[\"a_in\"]*Cos[dt]^2)/s[\"phi\"];",
                "  phase = 1 + d[\"b_in\"]*d[\"p_var\"];",
                "  t3 = valve*acoustic*phase;",
                "  raw = t1 + t2 + t3; S = d[\"K\"]*raw;",
                "  Association[",
                "    \"K\" -> N[d[\"K\"]], \"T1\" -> N[t1], \"T2\" -> N[t2], \"T3\" -> N[t3],",
                "    \"raw\" -> N[raw], \"S\" -> N[S], \"quirk_mod\" -> N[qm], \"growth\" -> N[growth]",
                "  ]",
                "];",
                "",
                "FSOTPrintPathway[] := Module[{d = N[FSOTDerived[]], panel},",
                "  Print[\"=== FSOT Symbolic Microscope (numeric eval of seeds→derived) ===\"];",
                "  Print[\"K = \", d[\"K\"]];",
                "  Print[\"psi_con, eta_eff, c_eff, p_var = \", d[\"psi_con\"], \", \", d[\"eta_eff\"], \", \", d[\"c_eff\"], \", \", d[\"p_var\"]];",
                "  panel = FSOTScalarSym[DEff -> 12., DeltaPsi -> 0.8, Observed -> True];",
                "  Print[\"linguistic panel: \", panel];",
                "  panel",
                "];",
                "",
                "(* Usage:",
                "     Get[\"…/FSOT_Symbolic_Microscope.wl\"]",
                "     FSOTPrintPathway[]",
                "     FSOTScalarSym[DEff->6., Observed->True]  (* quantum-like *)",
                "*)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_formal_parity_report() -> Path:
    """Bundle lab + authority + golden export into one formal report."""
    FORMAL_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lab = compare_to_lab_golden()
    auth = verify_vs_authority()
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "S = K*(T1+T2+T3)",
        "lab_cross_verify": lab,
        "authority_cross_verify": auth,
        "backends": {
            "mathematica": str(MATHEMATICA_DIR),
            "lean": r"C:\Users\damia\Desktop\FSOT-2.1-Lean",
            "coq": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\coq",
            "isabelle": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\isabelle",
            "fstar": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\fstar",
            "lab_golden": r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\parity\golden.json",
            "pflt_golden": str(FORMAL_DIR / "golden_fsot_pflt.json"),
        },
        "all_ok": bool(lab.get("all_ok")) and bool(auth.get("all_ok")),
    }
    path = FORMAL_DIR / "parity_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT_DIR / "lab_cross_verify.json").write_text(json.dumps(lab, indent=2), encoding="utf-8")
    (OUT_DIR / "authority_cross_verify.json").write_text(json.dumps(auth, indent=2), encoding="utf-8")
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MATHEMATICA_DIR.mkdir(parents=True, exist_ok=True)
    FORMAL_DIR.mkdir(parents=True, exist_ok=True)

    print("=== FSOT Math Microscope ===")
    domains = ["linguistic", "historical", "mythological", "quantum", "cosmological"]
    for d in domains:
        tr = trace_domain(d)
        out = OUT_DIR / f"trace_{d}.json"
        out.write_text(json.dumps(tr.to_dict(), indent=2), encoding="utf-8")
        wl = export_mathematica(tr)
        print(f"  {d}: S={tr.panel['S']:.6f} T1={tr.panel['T1']:.6f} T2={tr.panel['T2']:.6f} T3={tr.panel['T3']:.6f}")
        print(f"    json={out.name}  wl={wl.name}")

    golden = export_golden_for_formal(domains)
    print("golden formal fixtures ->", golden)

    sym = export_symbolic_mathematica()
    print("symbolic mathematica ->", sym)

    parity = write_formal_parity_report()
    print("formal parity report ->", parity)
    lab = json.loads((OUT_DIR / "lab_cross_verify.json").read_text(encoding="utf-8"))
    auth = json.loads((OUT_DIR / "authority_cross_verify.json").read_text(encoding="utf-8"))
    print("lab cross-verify all_ok=", lab.get("all_ok"))
    if lab.get("comparisons"):
        for c in lab["comparisons"]:
            print(f"  {c['id']}: Δ={c['abs_diff']:.3e} ok={c['ok']}")
    if lab.get("scalar_sample"):
        print("  scalar sample Δ=", lab["scalar_sample"]["abs_diff"])
    print("authority cross-verify all_ok=", auth.get("all_ok"))
    for r in auth.get("domains") or []:
        print(f"  {r['domain']}: dS={r['dS']:.3e} ok={r['ok']}")

    # Master Mathematica notebook driver
    master = MATHEMATICA_DIR / "FSOT_PFLT_Microscope.wl"
    master.write_text(
        "\n".join(
            [
                "(* FSOT PFLT Math Microscope — master loader *)",
                "(* Open in Mathematica / Wolfram Engine and evaluate *)",
                f'Get["{MATHEMATICA_DIR.as_posix()}/FSOT_Symbolic_Microscope.wl"];',
                "Print[\"=== Symbolic pathway ===\"];",
                "FSOTPrintPathway[];",
                f'Get["{MATHEMATICA_DIR.as_posix()}/trace_linguistic.wl"];',
                "Print[\"=== Numeric domain trace (linguistic) ===\"];",
                "Print[\"FSOTTrace: \", FSOTTrace[]];",
                "Print[\"Diff vs Python panel: \", FSOTDiff[]];",
                "(* Other domains: Get[\"…/trace_historical.wl\"] etc. *)",
                "(* Formal: compare N[FSOTDerived[][\"K\"]] to formal/golden_fsot_pflt.json constants.K *)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("master wl ->", master)
    print("done")


if __name__ == "__main__":
    main()
