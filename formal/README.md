# Formal cross-verification for PFLT FSOT math

PFLT’s scalar authority is **Python mpmath (dps=50)** in `PFLT_FSOT_2_1_aligned.py` /
`fsot_math_microscope.py`, aligned with **Lean FSOT.Scalar**, GPU-lab `parity/golden.json`,
and your Isabelle / Coq / F* trinary stack.

The **Mathematica** layer is the formula microscope: every intermediate of

```
S = K · (T1 + T2 + T3)
```

is named, printable, and re-evaluable so reasoning pathways can be inspected granularly
(seeds → L1 → L2 → T1/T2/T3 → S) and checked against the formal backends.

## Quick start

```bash
cd Desktop/pflt
python fsot_math_microscope.py
python formal/run_formal_asserts.py   # Lean + Coq (+ Isabelle/F* if installed)
```

Produces:

| Artifact | Role |
|----------|------|
| `formal/golden_fsot_pflt.json` | Constants + domain fixtures (`S,T1,T2,T3`) for provers |
| `formal/parity_report.json` | Lab golden + microscope-vs-authority bundle |
| `formal/assert_report.json` | Full multi-prover assert ledger (`overall_ok`) |
| `formal/lean/PFLTGoldenAsserts.lean` | Lean `#eval near` vs golden S/K |
| `formal/coq/PFLTGolden.v` | Coq Q seeds + trinary roundtrip (`coqc`) |
| `formal/isabelle/PFLTGolden.thy` | Isabelle golden defs + trinary |
| `formal/fstar/PFLTGolden.fst` | F* golden + trinary lemma |
| `data/math_microscope/trace_*.json` | Full step lists (microscope JSON) |
| `data/math_microscope/lab_cross_verify.json` | vs GPU-lab `parity/golden.json` |
| `data/math_microscope/authority_cross_verify.json` | microscope ≡ `compute_S_D_chaotic` |
| `data/math_microscope/core_misses/` | Dual-track held-out **core** miss microscope logs |
| `mathematica/FSOT_Symbolic_Microscope.wl` | Rebuild seeds→derived→S in Wolfram |
| `mathematica/trace_*.wl` | Domain numeric recompute + `FSOTDiff[]` |
| `mathematica/FSOT_PFLT_Microscope.wl` | Master loader |

## Backends (this machine)

| Backend | Local path (hint) | Role |
|---------|-------------------|------|
| **Mathematica** | `pflt/mathematica/` | Formula microscope, step prints, numeric Δ |
| **Lean 4** | `Desktop/FSOT-2.1-Lean` + lab `phase1_formal_gpu/lean` | Scalar / trinary parity |
| **Coq** | `…/phase1_formal_gpu/coq/Trinary.v` | Trinary / boot lemmas |
| **Isabelle** | `…/phase1_formal_gpu/isabelle/Trinary.thy` | Theory export compare |
| **F\*** | `…/phase1_formal_gpu/fstar/FSOTGpuBoot.fst` | Extract + numeric check |
| **Lab golden** | `…/parity/golden.json` | Shared multi-language seed + sample S |

## Workflow

1. Run `python fsot_math_microscope.py` after any scalar change.
2. Run `python formal/run_formal_asserts.py` — requires Python authority + Lean + Coq;
   Isabelle/F* are optional if not on PATH. Check `formal/assert_report.json` → `overall_ok`.
3. In Mathematica / Wolfram Engine:
   ```wolfram
   Get["…/mathematica/FSOT_PFLT_Microscope.wl"]
   (* FSOTDiff[] should be ~0 vs Python panel *)
   ```
4. **Dual-track core misses** — `python dual_track_eval.py` auto-traces held-out **core**
   misses (not name track) into `data/math_microscope/core_misses/` with full T1/T2/T3
   pathways for failure diagnosis.
5. **Ad-hoc translation failure microscope**:
   ```python
   from PFLT_FSOT_2_1_aligned import PFLT
   p = PFLT(enable_math_trace=True)
   r = p.translate("obscure_token", context="historical",
                   math_trace=True, math_trace_failures=True)
   # r["math_microscope"]  → pathway summary (T1/T2/T3 chains)
   # r["math_failure_logs"] → data/math_microscope/fail_*.json
   ```

## Formula (FSOT 2.1)

```
S = K · (T1 + T2 + T3)
```

Seeds: `π, e, φ, γ_Euler, G_Catalan` — zero free parameters beyond seeds.

### Microscope layers

| Layer | Contents |
|-------|----------|
| `seed` | π, e, φ, γ, G_Catalan |
| `L1` | α, ψ_con, η_eff, β, γ_c, ω |
| `L2` | θ_s, poof, c_eff, K, … |
| `input` | N, P, D_eff, Δψ, Δθ, observed, … |
| `T1` | growth → base → d_scale → quirk_mod → T1 |
| `T2` | scale·amplitude + trend_bias |
| `T3` | valve · acoustic · phase |
| `combine` | raw = T1+T2+T3 ; S = K·raw |

## Notes

- Default bulk eval keeps `math_trace` **off** so held-out runs stay fast and disk-clean.
- Enable the microscope when refining against Isabelle/Coq/Lean/F* or when reading failure logs.
- GitHub push policy still requires a **meaningful accuracy gain**; this tooling ships locally
  for verification depth without claiming a metric release.
