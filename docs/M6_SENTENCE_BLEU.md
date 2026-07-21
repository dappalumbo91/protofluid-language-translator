# M6 — Competitive climb (BLEU-style bars under FSOT)

**Built:** 2026-07-21T16:31:24.952348+00:00
**Decoder:** bigram longest-match + Tatoeba unigrams + closed-class + densify + peels + CJK chars
**Train pairs (held-out from eval):** 391340 (cap 25000/lang)

## What no one else has (already shipping)

Intrinsic free-parameter FSOT model: translation is a surface of law-backed intelligence — densify without rewriting law. No competitor ships offline classical/visual + live scalar pin + form→gloss catalog under the same constitution.

- Law: `S=K(T1+T2+T3)` · pin **D1D38A**
- Offline densify + classical/visual + converse + cert gate
- Form→gloss catalog: OPEN/PRODUCT **100%** on covered languages

## Honest framing

Not claiming Google/DeepL neural parity yet. Climbing toward competitive sentence bars offline (phrase table + templates + CJK). M1 form→gloss catalog remains 100% on covered langs.

Corpora on `D:\training data\pflt_linguistics` — not GitHub.

## Overall (Tatoeba src→en, n=6400 held-out)

| Metric | Score |
|--------|------:|
| n sentences | 6400 |
| BLEU-4 (smoothed) | 2.44 |
| BLEU-1 | 43.87 |
| Unigram F1 | 34.31 |
| chrF-ish | 25.18 |
| Token coverage | 90.33% |

## Per language

| Lang | n | BLEU | B1 | U-F1 | chrF | Cov% | Label |
|------|--:|-----:|---:|-----:|-----:|-----:|-------|
| ar | 400 | 1.71 | 38.74 | 34.06 | 24.67 | 95.3 | Arabic→English |
| de | 400 | 2.77 | 44.16 | 39.01 | 28.92 | 99.29 | German→English |
| es | 400 | 6.53 | 53.21 | 45.2 | 36.95 | 99.88 | Spanish→English |
| fr | 400 | 3.45 | 46.01 | 40.52 | 31.98 | 99.54 | French→English |
| he | 400 | 2.16 | 46.62 | 38.46 | 26.77 | 93.78 | Hebrew→English |
| hi | 400 | 0.86 | 31.78 | 31.86 | 24.2 | 99.58 | Hindi→English |
| it | 400 | 6.46 | 49.94 | 42.9 | 33.84 | 99.88 | Italian→English |
| ja | 400 | 0.08 | 22.9 | 8.08 | 3.88 | 43.16 | Japanese→English |
| ko | 400 | 1.14 | 39.3 | 31.58 | 21.66 | 79.97 | Korean→English |
| la | 400 | 2.6 | 49.44 | 39.44 | 28.01 | 99.84 | Latin→English |
| nl | 400 | 4.54 | 49.78 | 44.03 | 36.54 | 99.57 | Dutch→English |
| pl | 400 | 3.13 | 49.38 | 39.46 | 29.76 | 98.05 | Polish→English |
| pt | 400 | 4.52 | 52.13 | 44.99 | 35.63 | 99.88 | Portuguese→English |
| ru | 400 | 2.07 | 45.6 | 37.44 | 26.15 | 95.37 | Russian→English |
| tr | 400 | 1.19 | 41.35 | 32.91 | 24.13 | 97.46 | Turkish→English |
| zh | 400 | 0.07 | 19.11 | 6.58 | 4.19 | 44.66 | Chinese→English |

## Competitor lens

| Dimension | Google / DeepL / NLLB | **PFLT (FSOT)** |
|-----------|----------------------|-----------------|
| Sentence BLEU/COMET | Strong (neural, cloud) | Climbing offline (this report) |
| Intrinsic free-parameter law | None | **FSOT S=K(T1+T2+T3) D1D38A** |
| Offline classical/visual | Weak/absent | **Core product** |
| Form→gloss catalog honesty | Opaque train | **100% open+product on catalog** |
| Law-backed converse / cert | No | **Yes** |

## Next levers

- Larger phrase mass (50k+/lang) + IBM-2 order models
- Morphological analyzers for TR/FI/HU
- Sentencepiece/BPE for JA/ZH
- Optional offline neural student distilled into Ada pathway (law stays master)
- FLORES-200 sample on D: when available
