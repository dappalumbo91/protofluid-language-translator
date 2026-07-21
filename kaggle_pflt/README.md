# PFLT FSOT Benchmarks — v0.2.0

**Protofluid Language Translator** under FSOT law \(S=K(T_1+T_2+T_3)\), authority pin **D1D38A**.

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
| `metrics_snapshot.json` | Machine-readable headline metrics + per-lang neural sacreBLEU |
| `benchmark_summary.csv` | Flat table: chat neural + WMT14 de-en |
| `M6_SOTA_PUSH.md` | Full SOTA push report (tables) |
| `COMPETITIVE_POSITION.md` | Honest competitive framing vs Google/DeepL/NLLB |
| `RELEASE_v0.2.0.md` | Release notes + resume checklist |
| `sample_densify.tsv` | Tiny form→gloss sample (demo only) |

## Headline results (2026-07-21)

| Track | Metric | Value |
|-------|--------|------:|
| Catalog | 113 langs form→gloss product | ~99.99% |
| Chat open-set neural | mean best sacreBLEU (16 langs) | **50.19** |
| Hybrid densify\|neural | mean sacreBLEU | **53.58** |
| WMT14 de→en | opus-mt-de-en sacreBLEU | **33.88** |
| WMT14 de→en | NLLB-600M sacreBLEU | **33.37** |
| Gap to staged DeepL mid (40) | sacreBLEU points | **6.12** |
| Gap to stretch (48) | sacreBLEU points | **14.12** |

## Protocol (HF-aligned)

- **WMT14** `wmt/wmt14` de-en test, n=3003, sacreBLEU, beams=5  
- **Chat:** Tatoeba-style held sample, best of local OPUS-MT / mul-en / NLLB-600M  
- Students densify/decode only; law pin fixed  

## Honesty

- Commercial DeepL/Google **news** SOTA is **not claimed**.  
- Product densify BLEU can include residual TM templates (product ceiling).  
- Fair open-set chat = neural numbers above.  
- FLORES not included (Hub data gated).  

## License

Apache-2.0 for packaging and reports. Third-party corpora and model weights remain under their original licenses and are not redistributed in this dataset.
