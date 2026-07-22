# How far until competitive accuracy?

**Updated:** 2026-07-22T21:09:17+00:00 · Law **D1D38A**

## Straight answer

| Game | Competitive? | Distance |
|------|--------------|----------|
| Catalog form-gloss | **Yes** | Ceiling on 113 langs |
| Chat sentence MT | **Yes (mid)** | Hybrid **48.74** >= mid bar 45 |
| **News / DeepL bar** | **Not yet** | Best product **36.0** · gap **4.0** to mid-40 · **12.0** to stretch 48 |
| FSOT / classical | **Unique** | — |

### One line

**Chat + catalog: competitive.**  
**News: ~90% of DeepL mid-bar** — about **+4.0 sacre** short of mid-parity (was +5.66 before NLLB-1.3B).

## News WMT14 de-en (stronger student v0.2.4)

| System | sacreBLEU | Gap to 40 |
|--------|----------:|----------:|
| Best product (ens2_gen_score: opus+nllb13) | **36.0** | **4.0** |
| NLLB-1.3B alone | **35.63** | 4.37 |
| Oracle multi-system | **40.18** | **−0.18 (clears mid)** |
| opus beams=5 | 33.88 | 6.12 |
| NLLB-600M | 33.37 | 6.63 |

Prior product best was **34.34** (600M pair). NLLB-1.3B alone is **+1.75** over opus; product **+1.66** over prior ensemble.

## FT status (honest)

| FT | Protocol | Result |
|----|----------|--------|
| v2 short freeze | test direct | flat 33.86 |
| v3 WMT-val early-stop | val 35.76 | **test 33.41** (no ship) |
| v4 train-holdout early-stop | never beat base holdout | **no ship** |

Conclusion: short/careless WMT FT on opus does not help. Need **quality data + longer careful FT** (or larger student training), not more beam tweaks.

## Timing lesson (applied)

| Before | After |
|--------|--------|
| Both models on GPU | One model at a time |
| ~2.4 h dual full test | sequential + hyp cache |
| Silent stages | Batch ETA + hyp cache |

## Ceiling of current students

Oracle among opus / NLLB-600M / **NLLB-1.3B** is **40.18** — **mid-40 is reachable with a perfect picker**.  
Product gen-score is still **36.0** → remaining gap is **picker quality** (+ better single hyps still help).
