# Protofluid-Ada — Translation Language Archive & Competitor Compare

**Built:** 2026-07-21T03:24:21.013713+00:00
**Product:** Protofluid-Ada V6 · pin `D1D38A`

> Metric: **form→gloss** exact/partial (classical/historical/visual).  
> Not WMT/FLORES sentence BLEU — different product track.

## Headline capability

| Metric | Value |
|--------|-------|
| Gold language codes | **20** |
| Gold inventory rows | **1,010,826** |
| Train mass keys (open-set) | ~**3,610,856** |
| Deploy map keys | ~**2,011,650** |
| **Open-set partial** (held-out, n=20000) | **39.3%** |
| Open-set exact | **36.6%** |
| Deploy closed-sample partial (n=7660) | **83.6%** |
| Open-set productive langs (partial≥15%, n≥50) | **1** |
| Open-set usable langs (partial≥40%) | **1** |
| **Deploy strong langs** (closed sample partial≥70%) | **16** |
| **Deploy usable langs** (partial≥40%) | **20** |

### Two tracks (read carefully)

| Track | Meaning | Current |
|-------|---------|---------|
| **DEPLOY** | Form already in quality lexicon | **84%** partial · **16/20** langs A_strong |
| **OPEN-SET** | Held-out form; morph must generalize | **39%** partial · Latin ~66% |

## Per-language open-set (honest held-out)

| Code | Language | n | Exact% | Partial% | Gold rows | Tier |
|------|----------|---|--------|----------|-----------|------|
| la | Latin | 11408 | 61.6 | 65.8 | 696,876 | B_usable |
| grc | Ancient Greek | 2975 | 2.9 | 3.2 | 109,136 | D_thin |
| ang | Old English | 2028 | 8.0 | 9.4 | 48,022 | D_thin |
| ar | Arabic | 648 | 0.0 | 0.0 | 22,145 | D_thin |
| got | Gothic | 446 | 5.6 | 8.5 | 18,553 | D_thin |
| he | Hebrew | 422 | 0.0 | 0.0 | 10,828 | D_thin |
| en | English | 397 | 0.5 | 1.3 | 30,402 | D_thin |
| egy | Egyptian (incl. hieroglyph/Unikemet) | 302 | 0.0 | 0.3 | 23,110 | D_thin |
| fa | Persian (Farsi) | 237 | 0.0 | 0.0 | 14,352 | D_thin |
| non | Old Norse | 217 | 9.7 | 9.7 | 8,383 | D_thin |
| san | Sanskrit | 217 | 0.0 | 0.0 | 9,821 | D_thin |
| cu | Church Slavonic | 205 | 0.0 | 0.0 | 4,282 | D_thin |
| cop | Coptic | 200 | 0.0 | 0.0 | 2,251 | D_thin |
| arc | Aramaic | 168 | 0.0 | 0.0 | 1,744 | D_thin |
| akk | Akkadian | 103 | 0.0 | 0.0 | 1,066 | D_thin |
| sga | Old Irish | 14 | 0.0 | 0.0 | 4,944 | C_sparse |
| sum | Sumerian | 7 | 0.0 | 0.0 | 1,999 | C_sparse |
| syc | Syriac | 5 | 0.0 | 0.0 | 2,452 | C_sparse |
| hit | Hittite | 1 | 0.0 | 0.0 | 307 | C_sparse |

### Tier legend

- **A_strong** partial ≥70% (n≥50)
- **B_usable** partial ≥40%
- **C_emerging** partial ≥15%
- **C_sparse** n<50
- **D_thin** partial <15%

## Deploy closed-sample (coverage when form is in lexicon)

| Code | Language | n | Exact% | Partial% | Tier |
|------|----------|---|--------|----------|------|
| akk | Akkadian | 400 | 92.2 | 92.8 | A_strong |
| ang | Old English | 400 | 82.2 | 86.5 | A_strong |
| ar | Arabic | 400 | 100.0 | 100.0 | A_strong |
| arc | Aramaic | 400 | 94.8 | 95.0 | A_strong |
| cop | Coptic | 400 | 99.2 | 99.2 | A_strong |
| cu | Church Slavonic | 400 | 99.8 | 99.8 | A_strong |
| egy | Egyptian (incl. hieroglyph/Unikemet) | 400 | 87.5 | 87.8 | A_strong |
| en | English | 400 | 86.8 | 93.0 | A_strong |
| fa | Persian (Farsi) | 400 | 74.0 | 74.8 | A_strong |
| got | Gothic | 400 | 53.0 | 53.0 | B_usable |
| grc | Ancient Greek | 400 | 76.0 | 81.5 | A_strong |
| he | Hebrew | 400 | 89.0 | 89.2 | A_strong |
| la | Latin | 400 | 76.5 | 79.2 | A_strong |
| non | Old Norse | 400 | 55.2 | 55.8 | B_usable |
| san | Sanskrit | 400 | 99.5 | 99.5 | A_strong |
| sga | Old Irish | 400 | 43.0 | 44.0 | B_usable |
| sum | Sumerian | 400 | 55.8 | 57.8 | B_usable |
| syc | Syriac | 400 | 99.8 | 99.8 | A_strong |
| hit | Hittite | 307 | 95.4 | 97.1 | A_strong |
| phn | Phoenician | 153 | 99.4 | 99.4 | A_strong |

## Competitor comparison (multi-metric, honest)

| System | Language surfaces | Strength | vs PFLT |
|--------|-------------------|----------|---------|
| **Google Translate** | ~249 | Modern sentence MT, breadth, cloud | Classical/dead/visual (la/grc/egy hieroglyphs) thin or absent |
| **Meta NLLB-200** | 200 | Many low-resource modern langs, research MT | Not offline FSOT-law product; classical visual not core |
| **DeepL** | ~30–100 (product varies) | EU modern sentence quality (often SOTA-class) | Narrow classical/historical; cloud |
| **Frontier LLM MT (Gemini/GPT class)** | many via prompting | Fluent modern + some classical with hallucination risk | No D1D38A law pin; not offline densify constitution |
| **Protofluid-Ada (this report)** | 20 gold codes · deploy A_strong=16 · open productive=1 | Offline classical/visual; deploy ~84% when known; Latin open-set ~66%; live D1D38A | Modern sentence BLEU not primary; non-Latin open-set morph thin |

### Breadth count vs quality

- vs Google ~249: **20/249** gold codes (8.0% of *count* only)
- vs NLLB 200: **20/200** (10.0% of count)
- PFLT is **not** claiming to beat Google/DeepL on modern sentence BLEU yet (M6).
- PFLT **does** claim a competitive offline classical/visual form→gloss track with FSOT law pin — a band consumer MT largely leaves empty.

## Where we stand (plain language)

1. **Catalog:** 20 language codes with quality gold (led by Latin 696,876, Greek, OE, Egyptian…).
2. **Open-set translation capability:** ~**39%** partial / ~**37%** exact on held-out forms (target **70%+** partial).
3. **Deploy lexicon hit rate (sampled closed):** ~**84%** when the form is already in the quality map.
4. **Productive surfaces:** **1** langs with open-set partial≥15% and enough eval mass.
5. **vs competitors:** trailing on *modern breadth count* (249/200); leading opportunity on *classical+visual offline + FSOT law*.

## Residuals

### Closed this report cycle
- Per-lang open-set + deploy scoring report (this file)
- Language archive with tiers A/B/C/D
- Competitor multi-metric comparison table

### Still open
- Open-set partial toward 70%+ (morph densify climb)
- Real U-Net image weights (hyp TSV contract ready)
- Modern sentence BLEU/COMET (M6 after M1)
- Lean spawn on every numeric claim

## Next climb
- Paradigm densify + inject for miss-heavy langs (grc Unicode, ar, got)
- Raise open-set partial la first (largest mass)
- Grow gold codes toward 100 meaningful surfaces
