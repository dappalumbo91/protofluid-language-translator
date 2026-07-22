# How far until competitive accuracy?

**Measured 2026-07-22 (post-crash resume) · Law D1D38A**

## Straight answer

| Game | Competitive? | How far |
|------|--------------|---------|
| **A. Form→gloss catalog** | **Yes — already** | Near ceiling (~99.99% / 113 langs) |
| **B1. Chat sentence MT** | **Yes — mid open-MT** | Hybrid **48.74** ≥ mid bar 45; ~+6 to strong (~55) |
| **B2. News sentence MT** (DeepL-style) | **Not yet** | Best product **34.39** · gap **+5.61** to mid-40 · **+13.6** to stretch 48 |
| **FSOT / classical offline** | **Yes — unique** | No commercial equivalent |

### One line

**Chat + catalog: competitive now.**  
**News accuracy: ~86% of mid DeepL-class bar** — about **+6 sacreBLEU** short of mid-parity, **+14** short of top stretch.

\Catalog     ############ DONE
Chat mid    ############ DONE (48.7 >= 45)
Chat strong ##########.. +6 to ~55
News mid40  ########.... +5.6 from product 34.4
News 48     #####....... +13.6
\
## News WMT14 de→en (latest)

| System | sacreBLEU | Gap to 40 |
|--------|----------:|----------:|
| opus-mt-de-en | 33.88 | 6.12 |
| NLLB-600M | 33.37 | 6.63 |
| Gen-score ensemble | 34.37 | 5.63 |
| **Learned ensemble** | **34.39** | **5.61** |
| Oracle upper | 37.71 | 2.29 |

Picker train acc was only **54.5%** (barely above chance) → learned pick barely beats gen-score; ~**3.3 pts** still sit in oracle headroom.

## Why the last run took ~2.4 hours

Full WMT test (3003) × dual models × beams=5, **both models on one 12GB GPU** (~11.8GB used) → slow beam decode, not a hang.

## Next to close the remaining ~6 news points

1. Better quality estimator / larger student (not more thin FT)
2. Model unload between decodes for faster iteration
3. FLORES multi-pair when unlocked
