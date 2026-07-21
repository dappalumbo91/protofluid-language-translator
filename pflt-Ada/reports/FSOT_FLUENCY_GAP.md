# FSOT fluency gap solver — compete via mathematics of densify

**Built:** 2026-07-21T18:27:20.793197+00:00

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
| BLEU-4 | 2.2 | 18.82 | 16.62 |
| BLEU-1 | 45.87 | 86.86 | 40.99 |
| U-F1 | 34.81 | 77.78 | 42.97 |
| chrF | 25.07 | 61.47 | 36.4 |
| Coverage | 91.3 | 100.0 | — |

Densify inject: +0 unigrams, +0 bigrams/templates (product path).

## Per-lang priority (ΔS densify budget)

| Lang | ΔS | Priority | Budget | B1 after | BLEU after |
|------|---:|----------|-------:|---------:|-----------:|
| zh | 0.6562 | T1 | 1.2848 | 100.0 | 12.15 |
| ja | 0.6457 | T1 | 1.2642 | 99.61 | 10.82 |
| ko | 0.4289 | T2 | 0.8397 | 95.88 | 28.47 |
| hi | 0.3787 | T2 | 0.7414 | 42.79 | 3.78 |
| tr | 0.3688 | T2 | 0.7221 | 95.2 | 22.16 |
| ar | 0.3533 | T2 | 0.6917 | 92.49 | 26.81 |
| de | 0.3389 | T2 | 0.6636 | 81.11 | 17.05 |
| he | 0.3116 | T2 | 0.6101 | 96.37 | 23.88 |
| ru | 0.3014 | T2 | 0.5900 | 93.09 | 21.08 |
| la | 0.3010 | T2 | 0.5894 | 97.5 | 22.15 |
| fr | 0.2944 | T2 | 0.5764 | 79.65 | 14.62 |
| pl | 0.2858 | T2 | 0.5596 | 95.44 | 20.2 |
| es | 0.2517 | T2 | 0.4927 | 80.74 | 16.25 |
| nl | 0.2341 | T2 | 0.4583 | 81.63 | 20.99 |
| pt | 0.2165 | T2 | 0.4238 | 81.65 | 16.79 |
| it | 0.2139 | T2 | 0.4188 | 85.41 | 21.96 |

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
