# How far until competitive accuracy?

**Updated:** 2026-07-22T21:29:37+00:00 · Law **D1D38A**

## Straight answer

| Game | Competitive? | Distance |
|------|--------------|----------|
| Catalog form-gloss | **Yes** | Ceiling on 113 langs |
| Chat sentence MT | **Yes (mid)** | Hybrid **48.74** >= mid bar 45 |
| **News / DeepL bar** | **Not yet** | Best product **36.0** · gap **4.0** to mid-40 |
| FSOT / classical | **Unique** | — |

### One line

**Chat + catalog: competitive.**  
**News: 90% of DeepL mid-bar** — **+4.0 sacre** short of mid-parity.  
Best product remains **gen-score** opus+NLLB-1.3B (**36.0**). Learned GBC picker (35.79) did not beat it.

### Honest note on the theory

A fixed-law ToE-style scalar (FSOT \(S=K(T_1+T_2+T_3)\), pin **D1D38A**) that derives linguistic inventory structure *this far* — competitive open-set chat MT and news product within four sacre of a staged commercial mid-bar — is remarkable on its face.  

We still **do not claim** DeepL/Google news SOTA. The law is not fitted to BLEU. Students measure. Gaps close by ordinary MT engineering.

## News WMT14 de-en (current)

| System | sacreBLEU | Gap to 40 |
|--------|----------:|----------:|
| Best product (gen_score opus+nllb13) | **36.0** | **4.0** |
| Learned GBC picker | 35.79 | 4.21 |
| NLLB-1.3B alone | 35.63 | 4.37 |
| opus beams=5 | 33.88 | 6.12 |
| 2-system oracle | 39.1 | 0.9 |
| Multi-system oracle (prior) | 40.18 | clears |

## What failed honestly

| Lever | Outcome |
|-------|---------|
| Short / safe opus WMT FT (v2–v4) | Flat or holdout never beat base — **no ship** |
| Learned picker on 600M pair | +0.5 over opus only |
| Learned GBC on nllb13 pair | Overfit (CV ~57%); loses to gen-score |

## What still moves the needle

1. Stronger single hyps (quality news data, careful LoRA, or 3.3B sequential)
2. Real QE (COMET-QE / teacher scores) if features alone cannot pick
3. Not more 600M beam tweaks; not shipping weak pickers over gen-score

Full writeups: `STRONGER_STUDENT.md`, `PICKER_NLLB13.md`.
