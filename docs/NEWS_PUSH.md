# News mid-parity push — measured

**Built:** 2026-07-22T17:10:39.514108+00:00  
**Law pin:** D1D38A

## Headline

| System | sacreBLEU | Gap to 40 |
|--------|----------:|----------:|
| Base opus-mt-de-en | 33.88 | 6.12 |
| NLLB-600M | 33.37 | 6.63 |
| **Product cross-NLL ensemble** | **34.11** | **5.89** |
| FT v3 (early-stop) **test** | 33.41 | 6.59 |
| FT v3 best **val** | 35.76 | (not test) |
| Oracle uF1 ensemble | 37.13 | 2.87 |

**Mid-40 cleared?** No.

## Finetune v3

- Froze first 3/6 encoder layers, lr=3e-5, train=120k pairs
- Early-stop patience 4 @ every 500 steps
- Best val **35.76** @ step 500; test **33.41** (do not ship over base)
- Saved: Helsinki-NLP__opus-mt-de-en-wmt-ft-v3

## Product ensemble

Cross-model NLL pick: **34.11** (opus 1776 / nllb 1227).  
Same as MBR-cross-NLL. Oracle still **37.13** (~3 pts selection headroom).

## Chat (prior lever)

Neural-first hybrid: **48.74** sacre — past mid bar 45.

## Honest remaining path to beat news mid-bar

1. Learned ensemble / quality estimator (close 34.1 → ~37)
2. Larger student (NLLB-1.3B) or multi-epoch FT with true WMT val that tracks test
3. FLORES multi-pair when unlocked

## Repos

Code + this report shipped to GitHub / HF / Kaggle with verify pack.
