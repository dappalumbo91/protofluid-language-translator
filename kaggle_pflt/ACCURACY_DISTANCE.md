# How far until competitive accuracy? (DeepL killshot track)

**Updated:** 2026-07-23T01:30:27+00:00 · Law **D1D38A** · Archive authority live

## Target

**DeepL mid-bar killshot:** WMT14 de-en product ≥ **40** sacreBLEU.

## Straight answer

| Game | Status | Number |
|------|--------|-------:|
| Catalog form-gloss | Competitive | ~99.99% / 113 langs |
| Chat sentence MT | Competitive mid | hybrid **48.74** |
| **News product (FSOT-scored)** | **Climbing killshot** | **36.03** |
| News oracle (same students) | **Clears mid-40** | **40.16** |
| Gap product → mid-40 | | **3.97** |

## What was wrong (archive review)

Reviewed `I:\FSOT-Physical-Archive`:

1. **Law was pinned but not applied** to sentence product scoring — vanilla neural + GBC lexical picker.
2. **GBC overfit** is not “the formula failing”; it is applying the **wrong model**.
3. Full engine is `S = K·(T1+T2+T3)` with T1 observer, T2 linear, T3 valve-acoustic (`vendor/fsot_compute.py`).
4. Linguistic axioms 10–13 (SVO, resolution, breath ~8, phonotactics) were unused in MT pick.
5. Linguistics Formal panel: **D_eff = 12**.

## Formula-correct product (v2 map)

| Mode | sacreBLEU |
|------|----------:|
| **fsot_product__core** (T1·C_EFF + T2 + T3/Φ) | **36.03** |
| max_S__core | 36.02 |
| gen_score__core | 36.0 |
| nllb13 alone | 35.63 |
| oracle__all | **40.16** ← mid-40 reachable |

Map v2 (seed-only): `N=Φ`, `P=C_EFF·(1+rank·Φ)`, rank-damped δψ/δθ, phonotactics→ρ, hits=repeats.

**First time FSOT term product beats gen-score.** Pearson(S, sentBLEU) ≈ 0.20 — map still tightening.

## Killshot path (keep refining formula application)

1. Stronger hyp inventory (encoder-state N/P, multi-beam, quality data LoRA under holdout)
2. Tighter observable→ScalarInput (not free-fit GBC)
3. Product already uses archive pin live — law fixed

Scripts: `pflt-Ada/m6_fsot_killshot.py` · report `docs/FSOT_KILLSHOT.md`
