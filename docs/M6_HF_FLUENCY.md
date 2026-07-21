# M6 HF fluency climb

**Built:** 2026-07-21T17:37:54.286348+00:00
**Train rows:** 748703 (OPUS Books + Tatoeba held-out)
**Phrase table:** uni=116791 bi=347552

## FSOT

Law \(S=K(T1+T2+T3)\) pin **D1D38A** unchanged. Hugging Face supplies parallel **data** (and later teacher models). Densify only.

## Overall (Tatoeba held-out eval)

| Metric | Score |
|--------|------:|
| n | 6400 |
| BLEU-4 | 2.2 |
| BLEU-1 | 45.87 |
| U-F1 | 34.81 |
| chrF | 25.07 |
| sacreBLEU | 0.89 |
| Coverage | 91.3% |

## Per language

| Lang | n | BLEU | B1 | F1 | chrF | sacre | Cov% |
|------|--:|-----:|---:|---:|-----:|------:|-----:|
| ar | 400 | 2.58 | 40.41 | 35.07 | 25.77 | 1.14 | 96.94 |
| de | 400 | 2.29 | 44.33 | 36.41 | 26.02 | 0.86 | 99.71 |
| es | 400 | 4.11 | 53.55 | 42.68 | 33.05 | 2.02 | 99.95 |
| fr | 400 | 4.46 | 47.39 | 39.43 | 29.82 | 2.27 | 99.83 |
| he | 400 | 2.5 | 50.61 | 40.68 | 28.29 | 0.94 | 95.62 |
| hi | 400 | 0.86 | 31.74 | 31.84 | 24.25 | 0.36 | 99.77 |
| it | 400 | 6.28 | 53.33 | 44.77 | 35.48 | 2.37 | 99.88 |
| ja | 400 | 0.08 | 24.66 | 8.68 | 3.99 | 0.01 | 45.04 |
| ko | 400 | 1.19 | 40.54 | 32.56 | 22.19 | 0.49 | 82.05 |
| la | 400 | 2.24 | 52.94 | 41.15 | 29.25 | 0.32 | 99.98 |
| nl | 400 | 3.84 | 51.23 | 44.11 | 35.26 | 1.14 | 99.74 |
| pl | 400 | 2.46 | 52.52 | 40.93 | 30.72 | 1.17 | 98.72 |
| pt | 400 | 4.0 | 55.06 | 45.81 | 35.98 | 1.47 | 99.94 |
| ru | 400 | 2.37 | 50.74 | 40.53 | 28.76 | 0.87 | 97.8 |
| tr | 400 | 1.58 | 45.41 | 35.39 | 25.94 | 0.48 | 99.1 |
| zh | 400 | 0.07 | 20.58 | 7.08 | 4.39 | 0.01 | 46.77 |

## Hugging Face leverage

| Asset | Status |
|-------|--------|
| OPUS Books | **used** for densify |
| Tatoeba (D:) | **used** |
| FLORES-200 | **blocked gated** — accept on Hub |
| NLLB-600M teacher | **next** offline densify |
| Gradio Space | needs HF PRO; model pack live |

See `docs/HF_SENTENCE_FLUENCY_PLAN.md`.
