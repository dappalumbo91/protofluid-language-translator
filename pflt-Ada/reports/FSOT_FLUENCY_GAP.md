# FSOT fluency gap solver — compete via mathematics of densify

**Built:** 2026-07-21T17:50:54.115245+00:00

## Law (fixed — not fitted to BLEU)

- Formula: `S=K(T1+T2+T3)` pin **D1D38A**
- Linguistic panel: S=0.651324761885 T1=0.549955 T2=1.000000 T3=1.707063e-17
- Densify students cannot rewrite K or seeds.

## Surface mapping (competitiveness as FSOT-shaped S)

| Component | Surface meaning | Metric drivers |
|-----------|-----------------|----------------|
| **T1_surf** | Lexicon / morph base | coverage × U-F1 |
| **T2_surf** | Linear phrase map | BLEU-1 × bigram retention |
| **T3_surf** | Order / fluency valve | BP × chrF |
| **S_surf** | K·(T1+T2+T3) | staged competitor bar |

Staged bar S_surf ≈ **0.72008** (T1=0.650 T2=0.650 T3=0.414)

## Before → after densify

| Metric | Before | After | Δ |
|--------|-------:|------:|--:|
| BLEU-4 | 2.2 | 5.99 | 3.79 |
| BLEU-1 | 45.87 | 69.04 | 23.17 |
| U-F1 | 34.81 | 53.19 | 18.38 |
| chrF | 25.07 | 40.01 | 14.94 |
| Coverage | 91.3 | 99.97 | — |

Densify inject: +4486 unigrams, +9700 bigrams/templates (product path).

## Per-lang priority (ΔS densify budget)

| Lang | ΔS | Priority | Budget | B1 after | BLEU after |
|------|---:|----------|-------:|---------:|-----------:|
| zh | 0.6562 | T1 | 1.2848 | 50.45 | 0.11 |
| ja | 0.6457 | T1 | 1.2642 | 52.95 | 0.15 |
| ko | 0.4289 | T2 | 0.8397 | 84.16 | 12.0 |
| hi | 0.3787 | T2 | 0.7414 | 39.01 | 1.48 |
| tr | 0.3688 | T2 | 0.7221 | 85.2 | 8.39 |
| ar | 0.3533 | T2 | 0.6917 | 82.46 | 15.54 |
| de | 0.3389 | T2 | 0.6636 | 72.61 | 8.9 |
| he | 0.3116 | T2 | 0.6101 | 88.6 | 11.9 |
| ru | 0.3014 | T2 | 0.5900 | 85.23 | 12.25 |
| la | 0.3010 | T2 | 0.5894 | 88.61 | 10.09 |
| fr | 0.2944 | T2 | 0.5764 | 70.49 | 6.86 |
| pl | 0.2858 | T2 | 0.5596 | 87.29 | 9.85 |
| es | 0.2517 | T2 | 0.4927 | 53.83 | 1.5 |
| nl | 0.2341 | T2 | 0.4583 | 51.32 | 2.65 |
| pt | 0.2165 | T2 | 0.4238 | 55.11 | 1.67 |
| it | 0.2139 | T2 | 0.4188 | 53.57 | 2.1 |

## How this is *solving* toward competitiveness

1. Measure gap as **ΔS_surf**, not ad-hoc loss.
2. Allocate densify by **component shortfall** (T1/T2/T3) × archive **growth**.
3. T3-priority langs get phrase templates + light EN reorder valve.
4. Law S stays the constitution for converse/cert; fluency is student densify.

Staged bars are intermediate (BLEU-4≈20, B1≈65), not final Google/DeepL SOTA. Solving ΔS_surf with densify raises surface fluency; law S unchanged.

## Next FSOT-native levers

- Raise staged bar toward neural (BLEU-4 30+) once T2/T3 densify saturates
- NLLB teacher densify for T2 (still student)
- FLORES eval when Hub access accepted
- Optional neural student under cert gate — densify only
