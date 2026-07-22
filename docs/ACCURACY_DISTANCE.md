# How far until competitive accuracy?

**Updated:** 2026-07-22T20:40:29.428556+00:00 · Law **D1D38A**

## Straight answer

| Game | Competitive? | Distance |
|------|--------------|----------|
| Catalog form-gloss | **Yes** | Ceiling on 113 langs |
| Chat sentence MT | **Yes (mid)** | Hybrid **48.74** >= mid bar 45 |
| **News / DeepL bar** | **Not yet** | Best product **34.34** · gap **5.66** to mid-40 · **13.66** to stretch 48 |
| FSOT / classical | **Unique** | — |

### One line

**Chat + catalog: competitive.**
**News: ~85.9% of DeepL mid-bar** — still about **+5.66 sacre** short of mid-parity.

## News WMT14 de-en (GPU-safe v0.2.3)

| System | sacreBLEU | Gap to 40 |
|--------|----------:|----------:|
| Best product (ens_gen_score) | **34.34** | 5.66 |
| Oracle multi-system | 37.95 | 2.05 |
| opus beams=5 | 33.88 | 6.12 |

## Timing lesson (applied)

| Before | After |
|--------|--------|
| Both models on GPU | One model at a time |
| ~2.4 h dual full test | **~30 min** full sweep |
| Silent stages | Batch ETA + hyp cache |

## Ceiling of current students

Oracle among opus/nllb is **37.95** — still **2.05** below mid-40.
Crossing 40 needs stronger hyps (larger student / better news training), not only better picking.
