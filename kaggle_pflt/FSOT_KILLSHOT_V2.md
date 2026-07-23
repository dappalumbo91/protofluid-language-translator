# FSOT DeepL killshot v2 — results

**Mission:** DeepL mid-40 killshot  
**Law:** S=K(T1+T2+T3) pin D1D38A  
**Elapsed:** ~9275.9s

## Headline

| System | sacreBLEU |
|--------|----------:|
| **Product gen_score (nllb33+nllb13)** | **36.88** |
| NLLB-3.3B alone | **36.69** |
| Prior v1 FSOT product | 36.03 |
| NLLB-1.3B alone | 35.63 |
| Multi-hyp oracle | **43.24** |
| Gap product→40 | **3.12** |
| % of mid-40 | **92.2%** |

## Levers delivered

1. **Encoder N + TF-NLL P + SPM T3** — extracted for opus/nllb13/nllb33/nllb600  
2. **Multi-hyp** — beams 5/8, ret3, lp variants + **NLLB-3.3B sequential**  
3. **SPM lattice** — piece entropy, breath length, unk

## Critical lesson (formula application)

Cross-family raw TF-NLL ranks **poison** FSOT product (fell to ~33.9).  
NLL scales differ by model. Fix: **within-family FSOT**, then pick family by gen_score / strong-student prior.

Stronger hyps (3.3B) moved the real needle: **+1.06** single over 1.3B.

## Systems measured

| single | sacre |
|--------|------:|
| nllb33_b5 | 36.69 |
| nllb13_b8 | 35.80 |
| nllb13_b5 | 35.63 |
| nllb13_b5_lp0.9 | 35.57 |
| opus_b5 | 33.88 |
| nllb600 | 33.37 |

Script: pflt-Ada/m6_fsot_killshot_v2.py
