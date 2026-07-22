# PFLT v0.2.4 — Stronger student (NLLB-1.3B)

**Date:** 2026-07-22  
**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A** (unchanged)

## What changed

| Item | Result |
|------|--------|
| Downloaded / evaluated **facebook/nllb-200-1.3B** | Fits RTX 5070 fp16; full WMT test sequential |
| NLLB-1.3B WMT14 de-en | **35.63** sacreBLEU (+1.75 vs opus 33.88) |
| Product ens (opus+nllb13 gen-score) | **36.0** (+1.66 vs prior 34.34) |
| Oracle multi-student | **40.18** — **first time mid-40 is cleared as upper bound** |
| Careful FT v4 | No ship (holdout never beat base) |
| Beam tweaks on 600M-only | **Not done** (policy) |

## Distance

- **90% of DeepL mid-bar (40)** at product level  
- Remaining product gap: **4.0** sacre  
- Chat hybrid still **48.74** (competitive)

## Script

`pflt-Ada/m6_stronger_student.py` — download, sequential decode, hyp cache, train-holdout FT protocol.

## Resume next

1. Learned product picker on opus+nllb13 features (oracle already 40.18)  
2. Quality news parallel data + LoRA that tracks holdout without test regression  
3. Optional NLLB-3.3B sequential eval if VRAM/disk allow  
