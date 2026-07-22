# DeepL mid-bar close — GPU-safe push

**Built:** 2026-07-22T20:39:51.494173+00:00  
**Law:** D1D38A  
**Elapsed:** 1829.4s

## Lessons applied

- One model on GPU at a time (load → decode → unload)
- Hypotheses cached under `data/hyp_cache/`
- Progress logs every 25 batches
- Decode config chosen on **validation only**

## Distance to competitive news accuracy

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL-class | 40 | **34.34** (`ens_gen_score`) | **5.66** |
| Stretch SOTA | 48 | 34.34 | 13.66 |
| Oracle upper | — | 37.95 | to 40: 2.05 |
| % of mid-40 | | **85.9%** | |

Chat hybrid remains **48.74** (already mid-competitive).

## All systems

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
| ens_oracle | **37.95** | 62.38 |
| ens_gen_score | **34.34** | 60.25 |
| ens_length_mid | **34.15** | 60.14 |
| opus_b5 | **33.88** | 59.92 |
| opus_bestcfg | **33.86** | 59.89 |
| nllb_b8 | **33.44** | 59.39 |
| nllb_b5 | **33.37** | 59.27 |

## Best opus config (val)

beams=5 length_penalty=0.9 → val sacre=27.48

## Honest note

Even perfect pick among current students tops at oracle ~37.95.  
Crossing **40** still needs **stronger hyps** (larger student / better news training), not only ensemble.
