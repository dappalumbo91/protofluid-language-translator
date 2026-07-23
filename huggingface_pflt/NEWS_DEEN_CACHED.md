# FSOT news de→en (cached students) — climb toward DeepL mid-40

**Built:** 2026-07-23T18:59:56.010076+00:00  
**Set:** WMT14 de-en test n=3003  
**FSOT best product:** **36.8** (`FSOT_pick_hardset`)  
**Gap → DeepL mid-40:** **3.2**  
**Gap → FSOT_oracle_pool:** **9.32** (selection headroom)  
**FSOT_oracle_pool:** 46.12  
**Pin D1D38A · S=K(T1+T2+T3):** True · S=0.6513247618848969

### Naming
| Prefix | Owner |
|--------|--------|
| **FSOT_*** | Our product / ranking / pool oracle |
| nllb* / opus* | Competitor **student** hyp generators |
| DeepL | External bar only |
| diag_* | Diagnostic, not product |

| System | sacreBLEU | chrF | mean flu |
|--------|----------:|-----:|---------:|
| FSOT_family_then_gen | 36.78 | 61.9 | 0.9972 |
| FSOT_oracle_pool | 46.12 | 67.54 |  |
| FSOT_pick_consensus | 36.76 | 61.89 | 0.9972 |
| FSOT_pick_gen_len | 36.78 | 61.89 | 0.9972 |
| FSOT_pick_hardset | 36.8 | 61.91 | 0.9972 |
| FSOT_pick_strong_family | 36.79 | 61.9 | 0.9972 |
| FSOT_product_gen | 36.79 | 61.9 | 0.9972 |
| diag_cross_student_gen_naive | 36.51 | 61.86 | 0.9968 |
| NLLB33_min_nll | 36.51 | 61.76 |  |
| nllb13_b5 | 35.63 | 61.06 | 0.9974 |
| nllb13_b8 | 35.8 | 61.13 | 0.9975 |
| nllb13_b8_lp09 | 35.73 | 61.08 | 0.9975 |
| nllb13_b8_lp11 | 35.83 | 61.17 | 0.9975 |
| nllb13_b8r3 | 35.78 | 61.12 | 0.9975 |
| nllb13_b8r5 | 35.76 | 61.11 | 0.9974 |
| nllb33_b5 | 36.69 | 61.79 | 0.9972 |
| nllb33_b8 | 36.74 | 61.87 | 0.9972 |
| nllb33_b8r3 | 36.74 | 61.87 | 0.9972 |
| nllb33_b8r5 | 36.74 | 61.87 | 0.9972 |
| nllb33_min_nll | 36.51 | 61.76 |  |
| nllb600_b5 | 33.37 | 59.27 | 0.9974 |
| nllb600_b8 | 33.44 | 59.39 | 0.9975 |
| nllb600_b8r3 | 33.47 | 59.41 | 0.9975 |
| opus_b5 | 33.88 | 59.92 | 0.9958 |
| opus_b8 | 33.8 | 59.9 | 0.9957 |
| opus_b8r3 | 33.79 | 59.91 | 0.9957 |

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
