# M6 — Modern sentence quality (BLEU-style bars)

**Built:** 2026-07-21T16:20:54.741851+00:00
**Decoder:** word-by-word form→gloss (densify lexicon + progressive peels)
**Corpus:** Tatoeba parallel (src→English), ≤400 sents/lang

## Honest framing

Not neural MT. Scores measure form-gloss sentence surface vs English refs. Google/DeepL train seq2seq on massive parallel data — different architecture. This bar is the honest offline baseline; climb with densify + morph + future M6 decoder.

Large corpora stay on `D:\training data\pflt_linguistics` — not GitHub.

## Overall

| Metric | Score |
|--------|------:|
| n sentences | 6400 |
| BLEU-4 (smoothed) | 1.91 |
| BLEU-1 | 27.24 |
| Unigram F1 | 24.36 |
| chrF-ish | 18.74 |
| Token coverage (mapped) | 86.85% |

## Per language (src→en)

| Lang | n | BLEU | B1 | U-F1 | chrF | Cov% | Label |
|------|--:|-----:|---:|-----:|-----:|-----:|-------|
| es | 400 | 5.34 | 36.49 | 35.87 | 31.14 | 99.74 | Spanish→English |
| fr | 400 | 4.71 | 32.49 | 33.5 | 28.53 | 99.23 | French→English |
| de | 400 | 2.53 | 29.72 | 30.02 | 22.12 | 99.25 | German→English |
| it | 400 | 3.92 | 30.66 | 30.46 | 23.58 | 99.92 | Italian→English |
| pt | 400 | 3.54 | 33.38 | 33.38 | 27.77 | 99.7 | Portuguese→English |
| ru | 400 | 1.04 | 31.34 | 28.71 | 19.63 | 92.69 | Russian→English |
| nl | 400 | 3.41 | 32.75 | 33.77 | 29.16 | 99.7 | Dutch→English |
| pl | 400 | 2.7 | 32.32 | 28.65 | 21.81 | 97.32 | Polish→English |
| tr | 400 | 0.5 | 21.88 | 18.6 | 11.78 | 90.58 | Turkish→English |
| ja | 400 | 0.07 | 14.97 | 5.26 | 3.51 | 37.25 | Japanese→English |
| ko | 400 | 0.69 | 21.22 | 17.94 | 12.57 | 62.5 | Korean→English |
| zh | 400 | 0.06 | 15.85 | 5.45 | 4.16 | 41.25 | Chinese→English |
| ar | 400 | 0.91 | 24.18 | 22.55 | 16.45 | 88.75 | Arabic→English |
| he | 400 | 1.07 | 26.98 | 24.01 | 16.92 | 87.24 | Hebrew→English |
| hi | 400 | 0.28 | 12.76 | 16.36 | 11.28 | 94.71 | Hindi→English |
| la | 400 | 0.9 | 29.03 | 24.54 | 18.51 | 99.7 | Latin→English |

## Competitor lens

| System | Typical modern sentence bar | Notes |
|--------|----------------------------|-------|
| Google / NLLB / DeepL | High BLEU/COMET on FLORES/WMT | Neural, cloud, huge parallel |
| **PFLT-Ada (this report)** | Form-gloss sentence surface above | Offline lexicon+morph; M1 form→gloss already 100% on catalog |

## Next climb (M6)

1. Phrase table / multi-word densify from Tatoeba (not just unigram).
2. Word-order / closed-class templates for EU pairs.
3. Optional neural student later — still offline-first under FSOT pin D1D38A.
4. FLORES-200 sample when licensed pack available on D:.
