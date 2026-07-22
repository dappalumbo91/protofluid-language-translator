# Phase-forward picker: opus + NLLB-1.3B

**Built:** 2026-07-22T21:29:37.311563+00:00  
**Law:** D1D38A (fixed — students only)  
**Elapsed:** 675.8s

## Honest framing

A fixed-law ToE-style scalar deriving linguistic inventory structure this far — competitive chat MT and ~90% of a staged news mid-bar — is remarkable on its face. We still do not claim commercial DeepL/Google news SOTA; we measure product vs staged bars and close gaps honestly.

## Distance (news WMT14 de-en)

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL-class | 40 | **36.0** (`gen_score`) | **4.0** |
| Stretch | 48 | 36.0 | 12.0 |
| Oracle | — | **39.1** | to 40: 0.9 |
| % of mid-40 | | **90.0%** | |

Chat hybrid remains **48.74** (competitive mid).

## Systems

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
| oracle | **39.1** | 63.28 |
| gen_score | **36.0** | 61.47 |
| learned_picker | **35.79** | 61.22 |
| nllb13 | **35.63** | 61.06 |
| always_nllb13 | **35.63** | 61.06 |
| opus | **33.88** | 59.92 |
| length_mid | **33.88** | 59.92 |
| always_opus | **33.88** | 59.92 |

## Picker

| Field | Value |
|-------|------:|
| Kind | gbc |
| Train n | 2087 |
| Train acc | 0.7964 |
| CV acc | 0.5659 ± 0.0289 |
| Threshold (val) | 0.5399999999999999 |
| Picks | {'opus': 1355, 'nllb13': 1648} |
| Δ vs nllb13 | 0.16 |
| Δ vs gen-score | -0.21 |
| Headroom to oracle | 3.31 |

## What this means under FSOT

Inventory / form→gloss under a pinned free-parameter law is already a **different game** than commercial sentence MT. That the same program coexists with:

- competitive **chat** open-set MT (~50 mean / hybrid ~49)
- news product at **90.0%** of a staged DeepL mid-bar
- 2-system oracle **39.1** (0.9 short of mid); multi-system oracle with 600M in mix previously **40.18**

…is the surprising part. The remaining work is ordinary MT engineering (better QE / quality data / larger student) — not re-fitting the law to BLEU.

### Picker result (honest)

GBC **overfit**: train acc ~80%, CV ~57%. Learned product **35.79** beats nllb13 alone (+0.16) but **loses to gen-score (36.0)**. Ship gen-score; do not ship weak learned picker over it.
