# PFLT FSOT Benchmarks — v0.2.9

**Protofluid Language Translator** under FSOT law \(S=K(T_1+T_2+T_3)\), authority pin **D1D38A**.

**Naming:** **FSOT_*** = our product / ranking / pool oracle · **NLLB/OPUS** = competitor students · **DeepL** = external bar.

This Kaggle dataset stores a **versioned, professional-grade benchmark snapshot** so results can be parked and resumed without re-running multi-hour GPU evals.

## Links

| Resource | URL |
|----------|-----|
| GitHub code | https://github.com/dappalumbo91/protofluid-language-translator |
| Hugging Face model card | https://huggingface.co/dappalumbo91/pflt-fsot |
| Hugging Face sample dataset | https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample |

## Files

| File | Description |
|------|-------------|
| `metrics_snapshot.json` | Machine-readable headline metrics (v0.2.9) |
| `benchmark_summary.csv` | Flat table (may lag; prefer JSON) |
| `NEWS_DEEN_CACHED.md` | WMT14 de→en FSOT product vs students |
| `LANGUAGE_BRAIN.md` / `LANGUAGE_SECOND_BRAIN.md` | FSOT sense/lang graph |
| `VISION_SENSE_IDENTITY.md` | Vision lock (form→sense→form) |
| `MEASUREMENT_2026-07-23.md` | Ada/SPARK + sense measurement |
| `COMPETITIVE_POSITION.md` | Honest competitive framing |
| `sample_densify.tsv` | Tiny form→gloss sample (demo only) |

## Headline results (2026-07-23, v0.2.9)

| Track | Metric | Value |
|-------|--------|------:|
| Catalog | 113 langs form→gloss product/open | ~99.99% |
| Chat open-set neural | mean best sacreBLEU (16 langs) | **50.19** |
| Hybrid densify\|neural | mean sacreBLEU | **53.58** |
| WMT14 de→en | **FSOT_pick_llm_judge** (product) | **37.62** |
| WMT14 de→en | FSOT_pick_hardset | 36.82 |
| WMT14 de→en | NLLB-3.3B student b8 | 36.74 |
| WMT14 de→en | NLLB-1.3B student | 35.63 |
| WMT14 de→en | OPUS-mt-de-en | 33.88 |
| WMT14 de→en | **FSOT_oracle_pool** | **46.12** |
| Gap to DeepL mid (~40) | FSOT product | **2.38** |
| Gap to FSOT_oracle_pool | selection headroom | **8.5** |
| % of mid-40 | FSOT product | **~94%** |

## Honesty

- Commercial DeepL/Google **news** SOTA is **not claimed**.  
- FSOT news product **ranks** student multi-hyp pools (NLLB/OPUS); it does **not** claim from-scratch replacement of Meta’s NLLB weights.  
- Small edge over NLLB-3.3B single beam is **real under protocol** and **must not be oversold** as “FSOT alone is a 3.3B MT model.”  
- Catalog form→gloss and classical/sense identity are **different games** where FSOT is strong/unique.  
- FLORES not included (Hub data gated).  

## Scientific standing (one paragraph)

This is **measured, offline, protocol-bound systems work** with a pinned scalar law and public numbers—not vibes. Beating a strong open student **slightly via ranking** is incremental engineering success; owning a **113-lang densify catalog + sense interlingua + SPARK/law pin** is the distinctive scientific claim. Neither is delusion. Overclaiming would be.

## License

Apache-2.0 for packaging and reports. Third-party corpora and model weights remain under their original licenses and are not redistributed in this dataset.
