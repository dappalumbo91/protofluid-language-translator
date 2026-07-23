# How far until DeepL killshot?

**Updated:** 2026-07-23T04:21:16.726680+00:00 · Law **D1D38A**

| Track | Value |
|-------|------:|
| **Best product** | **36.88** (gen_score nllb33+nllb13) |
| Best single | **36.69** (NLLB-3.3B) |
| Gap to mid-40 | **3.12** |
| Oracle multi-hyp | **43.24** |
| % of mid-40 | **92.2%** |
| Prior v1 | 36.03 |

## v2 delivered

- Encoder-state N + TF-NLL P + SPM T3 features  
- Multi-beam / multi-return + **NLLB-3.3B** (fits RTX 5070 sequential fp16)  
- Lesson: do not mix TF-NLL ranks across model families without calibration  

See FSOT_KILLSHOT_V2.md.
