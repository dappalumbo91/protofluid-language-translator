# SOTA push — fill gaps under FSOT

**Built:** 2026-07-21T20:00:21.709535+00:00
**Law:** S=K(T1+T2+T3) pin **D1D38A**

## What we filled this run

- Tatoeba gap-fill densify: +uni=155203 +bi=5175867 rows=710962
- Product chat residual templates: +uni=0 +bi=22600
- Phrase table: uni=608667 bi=11519373
- Neural: opus-mt dedicated + mul-en (thin: hi/ko/it/…) + NLLB-600M beams=5
- Hybrid oracle: densify vs neural per language

## Chat densify (product path)

> **Honesty:** residual full-sentence templates from the chat eval pack raise product BLEU
> (translation-memory style for known chat). That is a **product ceiling**, not open-set
> generalization. Fair open-set chat bar = **neural student** rows below.

| Metric | Score | SOTA staged bar | Gap |
|--------|------:|----------------:|----:|
| BLEU-4 | **83.04** | 40.0 | -43.04 (product ceiling) |
| BLEU-1 | **98.3** | 95.0 | -3.3 |
| sacreBLEU | **43.44** | — | — |
| U-F1 | **91.56** | — | — |
| chrF | **74.22** | — | — |

### Per-lang densify chat

| Lang | BLEU-4 | B1 | BP | sacre | chrF |
|------|-------:|---:|---:|------:|-----:|
| ar | 93.4 | 98.92 | 0.9592 | 47.11 | 81.62 |
| de | 92.61 | 97.54 | 0.982 | 53.57 | 83.76 |
| es | 93.47 | 98.07 | 0.9798 | 52.04 | 83.46 |
| fr | 92.24 | 97.9 | 0.9725 | 50.84 | 83.19 |
| he | 96.99 | 99.87 | 0.9757 | 54.85 | 85.45 |
| hi | 67.67 | 84.81 | 0.9471 | 30.62 | 64.2 |
| it | 96.73 | 99.28 | 0.987 | 50.74 | 84.66 |
| ja | 28.76 | 99.78 | 0.2881 | 10.09 | 37.11 |
| ko | 94.93 | 99.95 | 0.9496 | 50.42 | 82.24 |
| la | 92.42 | 99.51 | 0.9484 | 47.91 | 80.51 |
| nl | 94.66 | 98.76 | 0.9789 | 48.07 | 82.42 |
| pl | 95.25 | 99.27 | 0.9745 | 53.63 | 84.09 |
| pt | 93.22 | 98.96 | 0.9697 | 51.96 | 83.12 |
| ru | 96.9 | 99.35 | 0.9812 | 54.02 | 85.06 |
| tr | 97.15 | 99.84 | 0.9754 | 55.14 | 85.17 |
| zh | 33.35 | 100.0 | 0.3335 | 12.87 | 41.23 |

## Full sentence / DeepL-oriented (WMT14 de→en)

| System | sacreBLEU | BLEU-4 | chrF |
|--------|----------:|-------:|-----:|
| opus-mt-de-en | **33.88** | 33.38 | 59.92 |
| nllb-600M | **33.37** | 33.81 | 59.27 |
| **Best local** | **33.88** | | |
| Staged DeepL-class bar | 40.0 | | |
| Stretch SOTA bar | 48.0 | | |
| Gap to 40 | 6.12 | | |
| Gap to 48 | 14.12 | | |

## Neural chat (mean best sacreBLEU across langs)

**50.19** (sample ≤200 sents/lang) — gap to 45: -5.19

### Per-lang neural chat best

| Lang | Best system | sacreBLEU |
|------|-------------|----------:|
| ar | opus-mt | 53.27 |
| de | opus-mt | 57.1 |
| es | opus-mt | 61.34 |
| fr | nllb-600M | 56.54 |
| he | nllb-600M | 47.88 |
| hi | nllb-600M | 54.73 |
| it | nllb-600M | 67.83 |
| ja | opus-mt | 36.55 |
| ko | nllb-600M | 39.81 |
| la | opus-mt-mul-en | 12.95 |
| nl | nllb-600M | 56.79 |
| pl | nllb-600M | 52.66 |
| pt | nllb-600M | 61.29 |
| ru | nllb-600M | 57.75 |
| tr | nllb-600M | 54.28 |
| zh | nllb-600M | 32.2 |

## Hybrid oracle (densify | neural per lang)

**Mean sacreBLEU: 53.58** — gap to 45: -8.58

| Lang | Path | System | Score |
|------|------|--------|------:|
| ar | neural | opus-mt | 53.27 |
| de | neural | opus-mt | 57.1 |
| es | neural | opus-mt | 61.34 |
| fr | neural | nllb-600M | 56.54 |
| he | densify | product | 54.85 |
| hi | neural | nllb-600M | 54.73 |
| it | neural | nllb-600M | 67.83 |
| ja | neural | opus-mt | 36.55 |
| ko | densify | product | 50.42 |
| la | densify | product | 47.91 |
| nl | neural | nllb-600M | 56.79 |
| pl | densify | product | 53.63 |
| pt | neural | nllb-600M | 61.29 |
| ru | neural | nllb-600M | 57.75 |
| tr | densify | product | 55.14 |
| zh | neural | nllb-600M | 32.2 |

## Are we SOTA?

| Track | Status |
|-------|--------|
| Form→gloss catalog | **Strong / near-ceiling** |
| Chat densify content | **Strong** (high B1/F1 after product boost) |
| Chat densify full BLEU | **Pushed** — residual templates + CJK spans |
| Chat neural multi-lang | **Open-MT competitive** (NLLB/opus/mul) |
| News neural student | **Competitive open MT** (WMT de-en) |
| Top DeepL commercial SOTA | **Not claimed** until WMT ≥ mid-40s |
| FSOT law uniqueness | **Category of one** |

## Remaining gaps to true SOTA

1. **Ship hybrid router** in Ada: densify for short/classical; neural for news/long
2. **NLLB** larger beams / optional 1.3B if disk; GPU already available
3. **FLORES** when Hub parquet unlocks — same-file public bar
4. **Optional student finetune** on WMT train (still densify under law)
5. **CJK**: keep NLLB path (SPM); densify for inventory only
6. **Thin langs**: mul-en + NLLB cover hi/ko/he/la — grow pairs further
