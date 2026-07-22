# Accuracy distance + learned ensemble

**Built:** 2026-07-22T19:58:21.343746+00:00  
**Law:** D1D38A

## How far (accuracy)

| Game | Us | Bar | Gap | Status |
|------|---:|----:|----:|--------|
| Catalog form→gloss | ~99.99% | product | — | **Competitive** |
| Chat hybrid | 48.74 | 45 mid | done | **Competitive** |
| News best product | **34.39** | 40 mid | **5.61** | Climbing |
| News oracle | 37.71 | 40 | 2.29 | Headroom |
| News stretch | 34.39 | 48 | 13.61 | Farther |

**~86.0% of mid DeepL-class news bar.**

## Learned ensemble (this run)

| System | sacreBLEU |
|--------|----------:|
| opus-mt-de-en | 33.88 |
| NLLB-600M | 33.37 |
| Gen-score ensemble | 34.37 |
| **Learned ensemble** | **34.39** |
| Oracle | 37.71 |

Picker train acc: 0.545 · picks: {'opus': 1545, 'nllb': 1458} · Δ vs opus: 0.51

elapsed 8748s
