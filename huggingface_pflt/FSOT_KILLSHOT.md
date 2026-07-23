# FSOT DeepL killshot — formula-correct scoring

**Built:** 2026-07-23T01:30:27.128480+00:00  
**Mission:** DeepL mid-bar killshot (40 sacre WMT14 de-en)  
**Law:** S = K·(T1+T2+T3) pin D1D38A · **pin_ok=True**  
**Elapsed:** 22.8s

## Archive review (what was wrong)

| Issue | Correction |
|-------|------------|
| Neural product ignored T1/T2/T3 | Score every hyp with full `compute_scalar` panel |
| GBC overfit on lexical features | No free-fit picker — only seed constants (K, C_EFF, Φ) |
| D_eff arbitrary | Linguistics Formal **D_eff=12** from archive benchmark |
| Linguistic axioms unused | Phonotactics, breath length ~8, punctuation → δθ / ρ |

Authority: `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py`

## Distance

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL | 40 | **36.03** (`fsot_product__core`) | **3.97** |
| Stretch | 48 | 36.03 | 11.97 |
| Oracle | — | 40.16 | -0.16 |
| % of mid-40 | | **90.1%** | |
| mid40_cleared | | **False** | |

## All modes

| Mode | sacreBLEU | chrF |
|------|----------:|-----:|
| oracle__all | **40.16** | 63.88 |
| oracle__core | **38.99** | 63.26 |
| fsot_product__core | **36.03** | 61.5 |
| max_S__core | **36.02** | 61.5 |
| gen_score__core | **36.0** | 61.47 |
| max_T3__core | **36.0** | 61.47 |
| fsot_tiebreak__core | **36.0** | 61.47 |
| max_T1__core | **35.91** | 61.38 |
| max_S__all | **35.68** | 61.26 |
| fsot_product__all | **35.68** | 61.27 |
| nllb13 | **35.63** | 61.06 |
| gen_score__all | **35.61** | 61.19 |
| max_T3__all | **35.61** | 61.19 |
| fsot_tiebreak__all | **35.61** | 61.19 |
| max_T1__all | **35.55** | 61.14 |
| opus | **33.88** | 59.92 |
| min_abs_dS__core | **33.58** | 59.57 |
| nllb600 | **33.37** | 59.27 |
| min_abs_dS__all | **32.92** | 58.97 |

## Diagnostics

Pearson(S, sentBLEU) on sample: **0.2031**  
(If near 0, mapping src/hyp→ScalarInput still needs refinement — terms not yet aligned to BLEU geometry.)

## Constants used (zero free params)

K=0.420222 · C_EFF=0.957702 · Φ=1.618034 · D_eff=12.0 · S_ling_ref=0.516296

## Next if gap remains

Refine **observable→ScalarInput** map (still formula-native): better cross-lingual N/P from encoder states, T3 acoustic from SPM lattice, multi-beam hyp expansion. Not GBC.
