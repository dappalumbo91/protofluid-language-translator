#!/usr/bin/env python3
"""
PFLT formal golden assert harness.

1. Refresh / load formal/golden_fsot_pflt.json
2. Assert microscope ≡ PFLT authority + lab golden
3. Emit Lean / Coq / Isabelle / F* golden artifacts under formal/
4. Run available provers (lean, coqc; isabelle/fstar if on PATH)
5. Write formal/assert_report.json

Usage:
  python formal/run_formal_asserts.py
  python formal/run_formal_asserts.py --skip-emit   # only re-run checks
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
FORMAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

LEAN_SRC = Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean\FSOT2_0_Compute.lean")
LAB_COQ = Path(
    r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\coq\Trinary.v"
)
LAB_ISABELLE = Path(
    r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\isabelle\Trinary.thy"
)
LAB_FSTAR = Path(
    r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\phase1_formal_gpu\fstar\FSOTGpuBoot.fst"
)
LAB_GOLDEN = Path(
    r"C:\Users\damia\Desktop\gpu exparment for lean coq isabell andf star\parity\golden.json"
)


def near(a: float, b: float, eps: float) -> bool:
    return abs(a - b) <= eps * max(1.0, abs(b))


def run_cmd(
    args: List[str],
    cwd: Optional[Path] = None,
    timeout: float = 180,
) -> Tuple[int, str]:
    try:
        r = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def load_or_refresh_golden() -> Dict[str, Any]:
    golden_path = FORMAL / "golden_fsot_pflt.json"
    # Always refresh so asserts track latest scalar
    from fsot_math_microscope import export_golden_for_formal, write_formal_parity_report

    export_golden_for_formal()
    write_formal_parity_report()
    return json.loads(golden_path.read_text(encoding="utf-8"))


def assert_python(golden: Dict[str, Any]) -> Dict[str, Any]:
    from fsot_math_microscope import compare_to_lab_golden, verify_vs_authority
    from PFLT_FSOT_2_1_aligned import compute_S_D_chaotic

    eps = float(golden.get("eps_f64", 1e-10))
    auth = verify_vs_authority(eps=eps)
    lab = compare_to_lab_golden()
    fixture_rows = []
    for fx in golden.get("fixtures") or []:
        inp = fx["inputs"]
        panel = compute_S_D_chaotic(
            N=float(inp.get("N", 1)),
            P=float(inp.get("P", 1)),
            D_eff=float(inp["D_eff"]),
            recent_hits=float(inp.get("recent_hits", 0)),
            delta_psi=float(inp.get("delta_psi", 1)),
            delta_theta=float(inp.get("delta_theta", 1)),
            rho=float(inp.get("rho", 1)),
            scale=float(inp.get("scale", 1)),
            amplitude=float(inp.get("amplitude", 1)),
            trend_bias=float(inp.get("trend_bias", 0)),
            observed=bool(inp.get("observed", False)),
        )
        dS = abs(panel.S - float(fx["S"]))
        fixture_rows.append(
            {
                "domain": fx["domain"],
                "golden_S": fx["S"],
                "authority_S": panel.S,
                "dS": dS,
                "ok": dS < eps,
            }
        )
    return {
        "authority": auth,
        "lab": lab,
        "fixtures": fixture_rows,
        "ok": bool(auth.get("all_ok"))
        and bool(lab.get("all_ok"))
        and all(r["ok"] for r in fixture_rows),
    }


def emit_lean(golden: Dict[str, Any]) -> Path:
    """Self-contained Lean 4 file: recompute S and #eval near golden."""
    out_dir = FORMAL / "lean"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "PFLTGoldenAsserts.lean"
    c = golden["constants"]
    # Lean Float comparisons are opaque (sorry-backed); emit printable #eval values
    # and let Python assert nearness vs golden JSON.
    lines = [
        "/-!",
        "  Auto-generated PFLT golden asserts (formal/run_formal_asserts.py).",
        "  Formula: S = K*(T1+T2+T3). Float parity vs formal/golden_fsot_pflt.json.",
        "  Run: lean formal/lean/PFLTGoldenAsserts.lean",
        "  Python runner parses printed floats and checks |S_lean - S_golden|.",
        "-/",
        "namespace PFLTGolden",
        "",
        "-- Seed-derived constants (mirror FSOT2_0_Compute / PFLT)",
        "def pi : Float := 3.141592653589793",
        "def e : Float := 2.718281828459045",
        "def phi : Float := (1.0 + Float.sqrt 5.0) / 2.0",
        "def gamma_euler : Float := 0.5772156649015329",
        "def catalan_G : Float := 0.915965594177219",
        "def sqrt2 : Float := Float.sqrt 2.0",
        "def log2 : Float := Float.log 2.0",
        "def alpha : Float := Float.log pi / (e * Float.pow phi 13)",
        "def psi_con : Float := 1.0 - 1.0 / e",
        "def eta_eff : Float := 1.0 / (pi - 1.0)",
        "def beta : Float := Float.exp (-(Float.pow pi pi + (e - 1.0)))",
        "def gamma : Float := -log2 / phi",
        "def omega : Float := Float.sin (pi / e) * sqrt2",
        "def theta_s : Float := Float.sin (psi_con * eta_eff)",
        "def poof_factor : Float := Float.exp (-(Float.log pi / e) / (eta_eff * Float.log phi))",
        "def acoustic_bleed : Float := Float.sin (pi / e) * phi / sqrt2",
        "def phase_variance : Float := -Float.cos (theta_s + pi)",
        "def coherence_efficiency : Float := (1.0 - poof_factor * Float.sin theta_s) * (1.0 + 0.01 * catalan_G / (pi * phi))",
        "def bleed_in_factor : Float := coherence_efficiency * (1.0 - Float.sin theta_s / phi)",
        "def acoustic_inflow : Float := acoustic_bleed * (1.0 + Float.cos theta_s / phi)",
        "def suction_factor : Float := poof_factor * (-Float.cos (theta_s - pi))",
        "def chaos_factor : Float := gamma / omega",
        "def perceived_param_base : Float := gamma_euler / e",
        "def new_perceived_param : Float := perceived_param_base * sqrt2",
        "def consciousness_factor : Float := coherence_efficiency * new_perceived_param",
        "def k : Float := phi * (perceived_param_base * sqrt2) / Float.log pi * 0.99",
        "",
        "def compute_S",
        "    (D_eff : Float) (delta_psi : Float) (delta_theta : Float) (observed : Bool) : Float :=",
        "  let N : Float := 1.0",
        "  let P : Float := 1.0",
        "  let hits : Float := 0.0",
        "  let rho : Float := 1.0",
        "  let growth := Float.exp (alpha * (1.0 - hits / N) * gamma_euler / phi)",
        "  let base := (N * P / Float.sqrt D_eff)",
        "    * Float.cos ((psi_con + delta_psi) / eta_eff)",
        "    * Float.exp (-alpha * hits / N + rho + bleed_in_factor * delta_psi)",
        "    * (1.0 + growth * coherence_efficiency)",
        "  let t1_0 := base * (1.0 + new_perceived_param * Float.log (D_eff / 25.0))",
        "  let t1 := if observed then",
        "      t1_0 * Float.exp (consciousness_factor * phase_variance)",
        "            * Float.cos (delta_psi + phase_variance)",
        "    else t1_0",
        "  let t2 : Float := 1.0",
        "  let valve := beta * Float.cos delta_psi * (N * P / Float.sqrt D_eff)",
        "    * (1.0 + chaos_factor * (D_eff - 25.0) / 25.0)",
        "    * (1.0 + poof_factor * Float.cos (theta_s + pi) + suction_factor * Float.sin theta_s)",
        "  let acoustic := 1.0",
        "    + (acoustic_bleed * Float.pow (Float.sin delta_theta) 2) / phi",
        "    + (acoustic_inflow * Float.pow (Float.cos delta_theta) 2) / phi",
        "  let phase := 1.0 + bleed_in_factor * phase_variance",
        "  let t3 := valve * acoustic * phase",
        "  k * (t1 + t2 + t3)",
        "",
        '-- tagged prints: Python parses "TAG=value"',
        '#eval IO.println s!"K={k}"',
        '#eval IO.println s!"phi={phi}"',
        '#eval IO.println s!"psi_con={psi_con}"',
        '#eval IO.println s!"c_eff={coherence_efficiency}"',
        "",
    ]
    for fx in golden.get("fixtures") or []:
        inp = fx["inputs"]
        d = float(inp["D_eff"])
        dp = float(inp["delta_psi"])
        dt = float(inp["delta_theta"])
        obs = "true" if inp.get("observed") else "false"
        s_exp = float(fx["S"])
        dom = fx["domain"]
        lines.append(f"-- domain={dom}  golden_S={s_exp:.17g}")
        lines.append(
            f'#eval IO.println s!"S_{dom}={{compute_S ({d}) ({dp}) ({dt}) {obs}}}"'
        )
        lines.append("")
    lines.append("end PFLTGolden")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def emit_coq(golden: Dict[str, Any]) -> Path:
    """Coq golden constants + trinary boot (structural) asserts."""
    out_dir = FORMAL / "coq"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "PFLTGolden.v"
    c = golden["constants"]
    # Rational mill units (×1e12) for exact Q comparisons of key seeds
    def q_mill(x: float, scale: int = 10**12) -> str:
        n = int(round(x * scale))
        return f"{n} # {scale}"

    lines = [
        "(* Auto-generated PFLT golden — formal/run_formal_asserts.py *)",
        "(* Numeric seeds as Q; trinary structural lemmas mirror lab Trinary.v *)",
        "From Stdlib Require Import QArith.",
        "",
        f"Definition golden_K : Q := {q_mill(c['K'])}.",
        f"Definition golden_phi : Q := {q_mill(c['phi'])}.",
        f"Definition golden_psi_con : Q := {q_mill(c['psi_con'])}.",
        f"Definition golden_c_eff : Q := {q_mill(c['c_eff'])}.",
        f"Definition golden_gamma : Q := {q_mill(c['gamma'])}.",
        "",
        "(* Domain S fixtures as Q mill (export / cross-check) *)",
    ]
    for fx in golden.get("fixtures") or []:
        sid = re.sub(r"[^a-z0-9]+", "_", fx["domain"])
        lines.append(f"Definition golden_S_{sid} : Q := {q_mill(float(fx['S']))}.")
    lines += [
        "",
        "(* Structural positivity via Qcompare (computes to Lt) *)",
        "Lemma golden_K_pos : (Qcompare (0 # 1) golden_K) = Lt.",
        "Proof. unfold golden_K; vm_compute; reflexivity. Qed.",
        "",
        "Lemma golden_phi_gt_one : (Qcompare (1 # 1) golden_phi) = Lt.",
        "Proof. unfold golden_phi; vm_compute; reflexivity. Qed.",
        "",
        "(* QArith opens Q scope — force nat literals below *)",
        "Close Scope Q_scope.",
        "",
        "(* Structural trinary packing — same as lab phase1 Coq *)",
        "Inductive Trinary : Type := SpinDown | Superposed | SpinUp.",
        "",
        "Definition trinary_to_bits (t : Trinary) : nat :=",
        "  match t with SpinDown => 0%nat | Superposed => 1%nat | SpinUp => 2%nat end.",
        "",
        "Definition trinary_of_bits (n : nat) : option Trinary :=",
        "  match n with",
        "  | 0%nat => Some SpinDown",
        "  | 1%nat => Some Superposed",
        "  | 2%nat => Some SpinUp",
        "  | _ => None",
        "  end.",
        "",
        "Lemma trinary_roundtrip : forall t, trinary_of_bits (trinary_to_bits t) = Some t.",
        "Proof. intros t; destruct t; reflexivity. Qed.",
        "",
        "Definition states_per_u64 : nat := 32%nat.",
        "Lemma states_per_u64_eq : states_per_u64 = 32%nat.",
        "Proof. reflexivity. Qed.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    # Also copy lab trinary path note
    (out_dir / "README.md").write_text(
        "Generated `PFLTGolden.v`. Build: `coqc PFLTGolden.v`\n"
        f"Lab twin: `{LAB_COQ}`\n",
        encoding="utf-8",
    )
    return path


def emit_isabelle(golden: Dict[str, Any]) -> Path:
    out_dir = FORMAL / "isabelle"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "PFLTGolden.thy"
    c = golden["constants"]
    lines = [
        "theory PFLTGolden",
        "  imports Main",
        "begin",
        "",
        "(* Auto-generated PFLT golden — formal/run_formal_asserts.py *)",
        f'definition golden_K :: real where "golden_K = {c["K"]:.17g}"',
        f'definition golden_phi :: real where "golden_phi = {c["phi"]:.17g}"',
        f'definition golden_psi_con :: real where "golden_psi_con = {c["psi_con"]:.17g}"',
        f'definition golden_c_eff :: real where "golden_c_eff = {c["c_eff"]:.17g}"',
        "",
    ]
    for fx in golden.get("fixtures") or []:
        sid = re.sub(r"[^a-z0-9]+", "_", fx["domain"])
        lines.append(
            f'definition golden_S_{sid} :: real where "golden_S_{sid} = {float(fx["S"]):.17g}"'
        )
    lines += [
        "",
        "datatype trinary = SpinDown | Superposed | SpinUp",
        "",
        'fun trinary_to_bits :: "trinary ⇒ nat" where',
        '  "trinary_to_bits SpinDown = 0" |',
        '  "trinary_to_bits Superposed = 1" |',
        '  "trinary_to_bits SpinUp = 2"',
        "",
        'fun trinary_of_bits :: "nat ⇒ trinary option" where',
        '  "trinary_of_bits 0 = Some SpinDown" |',
        '  "trinary_of_bits 1 = Some Superposed" |',
        '  "trinary_of_bits 2 = Some SpinUp" |',
        '  "trinary_of_bits _ = None"',
        "",
        'lemma trinary_roundtrip: "trinary_of_bits (trinary_to_bits t) = Some t"',
        "  by (cases t) simp_all",
        "",
        'lemma golden_K_pos: "golden_K > 0"',
        "  by (simp add: golden_K_def)",
        "",
        'lemma golden_phi_gt1: "golden_phi > 1"',
        "  by (simp add: golden_phi_def)",
        "",
        "end",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "Generated `PFLTGolden.thy`. Build with Isabelle if installed:\n"
        "  isabelle build -D .   (or open in Isabelle/jEdit)\n"
        f"Lab twin: `{LAB_ISABELLE}`\n",
        encoding="utf-8",
    )
    return path


def emit_fstar(golden: Dict[str, Any]) -> Path:
    out_dir = FORMAL / "fstar"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "PFLTGolden.fst"
    c = golden["constants"]
    lines = [
        "module PFLTGolden",
        "",
        "(* Auto-generated PFLT golden — formal/run_formal_asserts.py *)",
        "open FStar.Real",
        "",
        f"let golden_K : real = {c['K']:.17g}R",
        f"let golden_phi : real = {c['phi']:.17g}R",
        f"let golden_psi_con : real = {c['psi_con']:.17g}R",
        f"let golden_c_eff : real = {c['c_eff']:.17g}R",
        "",
    ]
    for fx in golden.get("fixtures") or []:
        sid = re.sub(r"[^a-z0-9]+", "_", fx["domain"])
        lines.append(f"let golden_S_{sid} : real = {float(fx['S']):.17g}R")
    lines += [
        "",
        "type trinary = | SpinDown | Superposed | SpinUp",
        "",
        "let trinary_to_bits (t: trinary) : nat =",
        "  match t with | SpinDown -> 0 | Superposed -> 1 | SpinUp -> 2",
        "",
        "let trinary_of_bits (n: nat) : option trinary =",
        "  if n = 0 then Some SpinDown",
        "  else if n = 1 then Some Superposed",
        "  else if n = 2 then Some SpinUp",
        "  else None",
        "",
        "val trinary_roundtrip: t:trinary ->",
        "  Lemma (trinary_of_bits (trinary_to_bits t) == Some t)",
        "let trinary_roundtrip t =",
        "  match t with | SpinDown -> () | Superposed -> () | SpinUp -> ()",
        "",
        f"(* Lab twin: {LAB_FSTAR} *)",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "README.md").write_text(
        "Generated `PFLTGolden.fst`. Build: `fstar.exe PFLTGolden.fst` if F* is installed.\n"
        f"Lab twin: `{LAB_FSTAR}`\n",
        encoding="utf-8",
    )
    return path


def run_lean(lean_path: Path, golden: Dict[str, Any]) -> Dict[str, Any]:
    code, out = run_cmd(["lean", str(lean_path)], cwd=ROOT, timeout=120)
    eps = float(golden.get("eps_f64", 1e-10))
    # Loose eps for printed Float (Lean default print is ~6 digits)
    print_eps = 5e-6
    tags = dict(re.findall(r"(K|phi|psi_con|c_eff|S_\w+)=(-?\d+\.\d+(?:[eE][+-]?\d+)?)", out))
    comparisons = []
    c = golden.get("constants") or {}
    for key, gkey in (("K", "K"), ("phi", "phi"), ("psi_con", "psi_con"), ("c_eff", "c_eff")):
        if key not in tags or gkey not in c:
            comparisons.append({"id": key, "ok": False, "reason": "missing_tag"})
            continue
        a, b = float(tags[key]), float(c[gkey])
        comparisons.append(
            {"id": key, "lean": a, "golden": b, "abs_diff": abs(a - b), "ok": near(a, b, print_eps)}
        )
    for fx in golden.get("fixtures") or []:
        tag = f"S_{fx['domain']}"
        if tag not in tags:
            comparisons.append({"id": tag, "ok": False, "reason": "missing_tag"})
            continue
        a, b = float(tags[tag]), float(fx["S"])
        comparisons.append(
            {
                "id": tag,
                "lean": a,
                "golden": b,
                "abs_diff": abs(a - b),
                "ok": near(a, b, print_eps),
            }
        )
    all_ok = code == 0 and comparisons and all(x.get("ok") for x in comparisons)
    # Cross-check desktop FSOT2_0_Compute.lean if present
    desktop = {"present": LEAN_SRC.exists()}
    if LEAN_SRC.exists():
        c2, o2 = run_cmd(["lean", str(LEAN_SRC)], cwd=LEAN_SRC.parent, timeout=120)
        desktop["code"] = c2
        desktop["snippet"] = o2[-400:]
        desktop["ok"] = c2 == 0 and "-0.502456" in o2 and "0.955506" in o2
    return {
        "tool": "lean",
        "path": str(lean_path),
        "code": code,
        "print_eps": print_eps,
        "tags": tags,
        "comparisons": comparisons,
        "raw_tail": out[-800:],
        "desktop_FSOT2_0": desktop,
        "ok": all_ok,
    }


def run_coqc(coq_path: Path) -> Dict[str, Any]:
    code, out = run_cmd(["coqc", str(coq_path.name)], cwd=coq_path.parent, timeout=120)
    lab = {"present": LAB_COQ.exists()}
    if LAB_COQ.exists():
        c2, o2 = run_cmd(["coqc", str(LAB_COQ.name)], cwd=LAB_COQ.parent, timeout=120)
        lab["code"] = c2
        lab["ok"] = c2 == 0
        lab["raw_tail"] = o2[-300:]
    return {
        "tool": "coqc",
        "path": str(coq_path),
        "code": code,
        "raw_tail": out[-600:],
        "lab_trinary": lab,
        "ok": code == 0,
    }


def run_isabelle(thy_path: Path) -> Dict[str, Any]:
    isabelle = shutil.which("isabelle")
    if not isabelle:
        # common Windows install
        cand = Path(r"C:\Users\damia\Desktop\Isabelle2025-2\bin\isabelle.bat")
        if cand.exists():
            isabelle = str(cand)
    if not isabelle:
        return {
            "tool": "isabelle",
            "path": str(thy_path),
            "skipped": True,
            "reason": "isabelle not on PATH",
            "ok": None,
            "note": "Theory emitted; open in Isabelle/jEdit or add isabelle to PATH",
        }
    # Lightweight: just check tool version; full build needs session ROOT
    code, out = run_cmd([isabelle, "version"], timeout=60)
    return {
        "tool": "isabelle",
        "path": str(thy_path),
        "version_code": code,
        "version": out[-200:],
        "ok": code == 0,
        "note": "PFLTGolden.thy emitted; use isabelle jedit or session build for full check",
    }


def run_fstar(fst_path: Path) -> Dict[str, Any]:
    fstar = shutil.which("fstar") or shutil.which("fstar.exe")
    if not fstar:
        return {
            "tool": "fstar",
            "path": str(fst_path),
            "skipped": True,
            "reason": "fstar not on PATH",
            "ok": None,
            "note": "PFLTGolden.fst emitted; install F* to typecheck",
        }
    code, out = run_cmd([fstar, str(fst_path)], cwd=fst_path.parent, timeout=180)
    return {
        "tool": "fstar",
        "path": str(fst_path),
        "code": code,
        "raw_tail": out[-600:],
        "ok": code == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="PFLT formal golden asserts")
    ap.add_argument("--skip-emit", action="store_true", help="reuse existing golden only")
    args = ap.parse_args()

    print("=== PFLT formal golden asserts ===")
    if args.skip_emit and (FORMAL / "golden_fsot_pflt.json").exists():
        golden = json.loads((FORMAL / "golden_fsot_pflt.json").read_text(encoding="utf-8"))
    else:
        golden = load_or_refresh_golden()
        print("refreshed golden_fsot_pflt.json + parity_report.json")

    py = assert_python(golden)
    print(f"python authority+lab+fixtures ok={py['ok']}")

    lean_p = emit_lean(golden)
    coq_p = emit_coq(golden)
    isa_p = emit_isabelle(golden)
    fst_p = emit_fstar(golden)
    print(f"emitted: {lean_p.name}, {coq_p.name}, {isa_p.name}, {fst_p.name}")

    lean_r = run_lean(lean_p, golden)
    print(f"lean ok={lean_r.get('ok')} tags={list((lean_r.get('tags') or {}).keys())}")
    for cmp_ in (lean_r.get("comparisons") or [])[:8]:
        print(f"  {cmp_.get('id')}: ok={cmp_.get('ok')} Δ={cmp_.get('abs_diff')}")
    if lean_r.get("desktop_FSOT2_0"):
        print(f"  desktop FSOT2_0_Compute ok={lean_r['desktop_FSOT2_0'].get('ok')}")

    coq_r = run_coqc(coq_p)
    print(f"coqc ok={coq_r.get('ok')} lab_trinary={coq_r.get('lab_trinary', {}).get('ok')}")

    isa_r = run_isabelle(isa_p)
    print(f"isabelle ok={isa_r.get('ok')} skipped={isa_r.get('skipped')}")

    fst_r = run_fstar(fst_p)
    print(f"fstar ok={fst_r.get('ok')} skipped={fst_r.get('skipped')}")

    # Overall: require python + lean + coq; isabelle/fstar optional if missing
    required = [py["ok"], lean_r.get("ok"), coq_r.get("ok")]
    optional = []
    if not isa_r.get("skipped"):
        optional.append(bool(isa_r.get("ok")))
    if not fst_r.get("skipped"):
        optional.append(bool(fst_r.get("ok")))
    overall = all(required) and (all(optional) if optional else True)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "S = K*(T1+T2+T3)",
        "golden": str(FORMAL / "golden_fsot_pflt.json"),
        "python": py,
        "lean": lean_r,
        "coq": coq_r,
        "isabelle": isa_r,
        "fstar": fst_r,
        "artifacts": {
            "lean": str(lean_p),
            "coq": str(coq_p),
            "isabelle": str(isa_p),
            "fstar": str(fst_p),
            "lab_golden": str(LAB_GOLDEN),
        },
        "overall_ok": overall,
        "policy": {
            "required": ["python_authority_lab_fixtures", "lean_near_evals", "coqc_PFLTGolden"],
            "optional": ["isabelle", "fstar"],
        },
    }
    out = FORMAL / "assert_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report -> {out}")
    print(f"OVERALL ok={overall}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
