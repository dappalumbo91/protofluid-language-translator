# DeepL mid-bar close — stronger student (NLLB-1.3B)

**Built:** 2026-07-22T21:09:17+00:00  
**Law:** D1D38A  
**Policy:** No more beam tweaks on 600M-only pair.

## Latest measured (WMT14 de-en test n=3003)

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
| ens_oracle (all) | **40.18** | 63.91 |
| ens2_oracle (opus+nllb13) | **39.03** | 63.29 |
| **ens2_gen_score (product)** | **36.0** | 61.47 |
| **nllb13 (NLLB-1.3B)** | **35.63** | 61.06 |
| ens_gen_score (4-sys) | 35.61 | 61.19 |
| opus_b5 | 33.88 | 59.92 |
| nllb600 | 33.37 | 59.27 |

## Distance

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL-class | 40 | **36.0** | **4.0** |
| Stretch SOTA | 48 | 36.0 | 12.0 |
| Oracle | — | **40.18** | **clears mid** |
| % of mid-40 | | **90%** | |

## What worked

1. **NLLB-1.3B** fits RTX 5070 (~12 GB) in fp16; sequential decode ~12 min for full test.
2. Offline gen-score ensemble of **opus + nllb13** → **36.0** (+1.66 vs prior 34.34).
3. Oracle with 1.3B **crosses 40** for the first time.

## What did not work

- Careful FT v4 (lr=1e-5, freeze 2/3 encoder, train-holdout early-stop): holdout never beat base; **no ship**.
- Prior short FTs (v2/v3) were flat or test-regressing.

## Scripts

- `pflt-Ada/m6_stronger_student.py` — download 1.3B, sequential eval, careful FT protocol
- Hyp cache: `pflt-Ada/data/hyp_cache/test_nllb13_b5_lp1.0.json`

## Next levers (still not beam tweaks)

1. Better product picker (learned, with 1.3B features) to close 36 → 40
2. Quality news parallel data + LoRA/FT that tracks holdout **and** does not regress test
3. Optional 3.3B if disk/VRAM allow (inference-only sequential)
