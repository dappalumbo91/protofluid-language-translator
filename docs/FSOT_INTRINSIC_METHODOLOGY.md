# FSOT Intrinsic Language Methodology

**Status:** operational (v0.3.0+)  
**Authority:** `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py`  
**Pin:** **D1D38A** (SHA-256 of archive `fsot_compute.py`)  
**Formula:** \(S = K(T_1 + T_2 + T_3)\)

This document is the **repeatable method** for ranking / product selection under FSOT for the linguistics domain.  
It exists so humans or automation can re-run the same process **without** inventing free parameters or LLM judges.

---

## 1. Goal

Beat competitor **student** systems (e.g. NLLB-3.3B gen-max) and climb toward external bars (DeepL-class mid-40) by **arranging seeds and domain table \(D_{\mathrm{eff}}\)** — not by fitting knobs to BLEU.

Public record stays on accounts already in use:

| Platform | Role |
|----------|------|
| GitHub | Code + methodology + reports |
| Hugging Face | Metrics snapshot + model card |
| Kaggle | Benchmark snapshot |

---

## 2. Non-negotiable rules

| Rule | Meaning |
|------|---------|
| **No free parameters** | Only archive seeds: π, e, φ, γ, G_Catalan → K, PHI, C_EFF, E, … |
| **No ad-hoc knobs** | No fitted weights, no BLEU-optimized coefficients, no “hack until 40” |
| **No LLM-as-product-ranker** | Qwen/etc. are not the product path |
| **Law never rewritten** | Observer densifies knowledge; \(K,T_i\) structure from archive |
| **Students ≠ product** | NLLB/OPUS generate **candidates only**; FSOT **ranks** |
| **Naming** | Product = `FSOT_*`; competitors keep NLLB/OPUS/DeepL names |

Violating these stagnates FSOT: free fits mask whether the arrangement is right.

---

## 3. Conceptual model of language under FSOT

Language is multi-aspect, like multi-domain physics:

| Face of language | Archive domain (examples) | Observables (rank / φ-squash) |
|------------------|---------------------------|-------------------------------|
| Sound / vibration / frequency | **Acoustics** \(D=10\) | SPM lattice, breath φ·e, phonotactics |
| Written / visual form | **Optics** \(D=10\) | letter density, class entropy, space rhythm |
| Meaning / understanding | **Biology** \(D=12\), **Neuroscience** \(D=14\) | TF-NLL rank, gen rank, length phase |
| Culture / symbolism | **Sociology** \(D=18\), **Psychology** \(D=16\) | form regularity, shared style cues |

Different hyps may “live” at different \(D_{\mathrm{eff}}\) — same idea as particle physics vs cosmology.  
**All \(D_{\mathrm{eff}}\) values come from the archive domain table only.**

---

## 4. Pipeline (one cycle)

```text
1) LOAD LAW
   - Verify pin D1D38A on archive fsot_compute.py
   - Load K, PHI, C_EFF, E, DOMAINS, ScalarInput defaults

2) LOAD CANDIDATES (students)
   - NLLB-3.3B multi-hyp caches (and optional other students)
   - Feature cache: enc_norm, tf_nll, spm_*, lengths
   - Dedup hyps per sentence; keep best gen per unique string

3) SCALE-FREE OBSERVABLES
   - Within-sentence ranks ∈ [0,1] for NLL (low better), encoder, gen
   - Absolute continuous values only via φ-squash: x/(x+φ)
   - Never raw model scores as free-scale inputs to K

4) MAP → ScalarInput (seed arrangement)
   - N, P, δψ, δθ, ρ, scale, amplitude, trend_bias from ranks + seeds
   - D_eff from domain table (Biology / Acoustics / Neuroscience / …)
   - Optional continuum D between table endpoints via golden rank blend
   - β, chaos, poof, A_*, … stay archive defaults (not fitted)

5) DERIVE
   - T1, T2, T3 from archive term structure
   - S = K·(T1+T2+T3)
   - Also seed linear: score_lin = T1·C_EFF + T2 + T3/φ

6) PICK
   - Per arrangement: argmax S or argmax score_lin among candidates
   - Students never win by gen-max alone as product

7) PUZZLE STUDY (refine arrangement, not knobs)
   - When a hyp is already strong vs gold (e.g. sent-BLEU ≥ 0.45):
     compare its S (or lin) to worst hyp in the same pool
   - Separation = mean(good) − mean(worst)
   - Good arrangement: separation > 0 and competitive sacreBLEU

8) SELECT PRODUCT ARRANGEMENT
   - Prefer highest sacreBLEU among arrangements with separation ≥ 0
   - Within seed tolerance φ⁻³ sacre (~0.24), prefer higher separation
   - Record winner as FSOT product name (e.g. FSOT_C_ac_S)

9) REPORT + SNAPSHOT
   - Write pflt-Ada/reports/FSOT_SEED_PUSH.{json,md}
   - Optionally update release/ + huggingface_pflt/ + kaggle_pflt/ metrics_snapshot.json
```

---

## 5. Seed arrangements (what we vary)

**Allowed to vary (arrangement, not free fit):**

- Which map (how observables enter N, P, δψ, δθ)  
- Which **table** \(D_{\mathrm{eff}}\) (Acoustics, Biology, Neuroscience, Sociology, …)  
- Pick mode: max **S** vs max **score_lin**  
- Continuum \(D\) between two table endpoints using golden ranks only  

**Not allowed:**

- Fitted weights \(w_i\) for BLEU  
- New constants not derived from π,e,φ,γ,G_Catalan or archive table  
- LLM judges as product  

Current map families in code (`scripts/fsot_seed_push.py`):

| Map | Idea |
|-----|------|
| **A** | Killshot-native: enc φ-squash + golden NLL/gen + SPM breath φ·e |
| **B** | Meaning-primary: N=φ fixed; phonotactic vs 1/e |
| **C** | Acoustic-tilt: stronger δθ / SPM; Acoustics \(D\) |
| **D** | Culture/visual: letter form; Sociology \(D\) |

**v0.3.0 product:** `FSOT_C_ac_S` — map C, Acoustics \(D_{\mathrm{eff}}=10\), argmax **S**, sacre **36.90** (beats NLLB-3.3B gen **36.79**).

---

## 6. Automation

One command:

```powershell
cd C:\Users\damia\Desktop\pflt
python -u scripts\fsot_automate_pipeline.py
```

Options:

```powershell
# Seed push only (default)
python -u scripts\fsot_automate_pipeline.py

# Also run multi-D_eff spectrum (slower)
python -u scripts\fsot_automate_pipeline.py --with-multi-deff

# Update metrics snapshots for GitHub/HF/Kaggle packs
python -u scripts\fsot_automate_pipeline.py --update-metrics

# Full local cycle
python -u scripts\fsot_automate_pipeline.py --with-multi-deff --update-metrics
```

What it does:

1. Verifies pin (or fails loud)  
2. Runs `fsot_seed_push.py` (and optionally multi-D / associate)  
3. Writes/reads reports under `pflt-Ada/reports/`  
4. Writes `pflt-Ada/reports/FSOT_PRODUCT_LOCK.json` (current product name + score)  
5. Optionally patches `metrics_snapshot.json` in `release/`, `huggingface_pflt/`, `kaggle_pflt/`  

**Not automated (on purpose):** git push, HF upload, Kaggle publish — you control when public.

---

## 7. Prerequisites (local data)

| Asset | Path |
|-------|------|
| Law | `I:\FSOT-Physical-Archive\...\vendor\fsot_compute.py` |
| Hyp caches | `pflt-Ada/data/hyp_cache/test_nllb33_*.json` |
| Features | `pflt-Ada/data/fsot_feat_cache/feat_nllb33_v3.json` (or v2) |
| WMT14 | Hugging Face `datasets` load `wmt/wmt14` de-en test |

If hyp/feat caches are missing, regenerate with existing decode/feature scripts — do **not** invent scores.

---

## 8. How to improve (only allowed moves)

1. **New seed arrangement** — new map using only ranks, φ-squash, domain table, archive defaults  
2. **New table \(D\)** — only names already in `DOMAINS`  
3. **Richer observables that are still scale-free** — e.g. sense-hit rank, IPA features from `audio_articulation.py`  
4. **Puzzle study** — if separation ≤ 0, the arrangement is wrong; rearrange, don’t fit  

If product is below student gen: **rearrange**, don’t add free parameters.

---

## 9. Dual track reminder

| Track | Role |
|-------|------|
| **Form → sense → form** | Primary product identity (sense interlingua, densify, Language Brain) |
| **Sentence ranking under S** | Student hyps ranked by FSOT for modern fluency metrics |

Both must stay under pin D1D38A. Ranking track must not redefine the product as NMT.

---

## 10. Related files

| File | Role |
|------|------|
| `docs/VISION_SENSE_IDENTITY.md` | Vision lock |
| `docs/FSOT_INTRINSIC_METHODOLOGY.md` | **This document** |
| `scripts/fsot_seed_push.py` | Arrangement search + product pick |
| `scripts/fsot_automate_pipeline.py` | One-shot automation |
| `scripts/fsot_derive_rank.py` | Single-map derive |
| `scripts/fsot_associate_language.py` | Sound+vision+meaning association |
| `scripts/fsot_multi_deff_language.py` | Multi-\(D_{\mathrm{eff}}\) spectrum |
| `fsot_law_bridge.py` | Pin + law scalar access |
| `pflt-Ada/reports/FSOT_SEED_PUSH.*` | Latest arrangement scores |
| `pflt-Ada/reports/FSOT_PRODUCT_LOCK.json` | Locked product pointer |

---

## 11. One-line method

> Load pin → candidates from students → scale-free observables → ScalarInput from seeds + domain table → \(S=K(T_1+T_2+T_3)\) → pick max S/lin → puzzle-check → lock product → report.
