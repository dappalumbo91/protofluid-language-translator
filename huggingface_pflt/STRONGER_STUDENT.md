# Stronger student + careful FT

**Built:** 2026-07-22T21:09:17.323940+00:00  
**Law:** D1D38A  
**Elapsed:** 1428.0s  
**Policy:** No more beam tweaks on 600M-only pair.

## Phase 1 — NLLB-1.3B (or fallback)

| Field | Value |
|-------|-------|
| Tried | ['facebook/nllb-200-1.3B'] |
| Used | **facebook/nllb-200-1.3B** |
| VRAM OK | True |

## Phase 2 — careful FT v4

| Field | Value |
|-------|------:|
| Base holdout | 34.27 |
| Best holdout | 34.27 |
| Shipped | **False** |
| TEST sacre | n/a (not shipped) |
| Protocol | train-holdout early-stop (not WMT val) |

v3 lesson: WMT val looked strong (35.76) but test regressed (33.41).

## Distance to DeepL mid-bar (~40)

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid | 40 | **36.0** (`ens2_gen_score`) | **4.0** |
| Stretch | 48 | 36.0 | 12.0 |
| Oracle | — | 40.18 | to 40: -0.18 |
| % of mid-40 | | **90.0%** | |

Prior best product was **34.34**. Chat hybrid remains **48.74**.

## All systems

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
| ens_oracle | **40.18** | 63.91 |
| ens2_oracle | **39.03** | 63.29 |
| ens2_gen_score | **36.0** | 61.47 |
| nllb13 | **35.63** | 61.06 |
| ens_gen_score | **35.61** | 61.19 |
| ens_length_mid | **34.44** | 60.4 |
| opus_b5 | **33.88** | 59.92 |
| opus_bestcfg | **33.86** | 59.89 |
| nllb600 | **33.37** | 59.27 |

## Next if still < 40

1. Stronger teacher hyps (3.3B if VRAM/disk, or better news-domain data)
2. Quality parallel data (news-commentary + Europarl filtered), longer LoRA FT
3. Not more beam search on the same 600M pair
