# PFLT FSOT Benchmarks — v0.2.4

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
| `STRONGER_STUDENT.md` | NLLB-1.3B + careful FT report |
| `ACCURACY_DISTANCE.md` | Distance to competitive bars |
| `DEEPL_CLOSE.md` | News mid-bar close status |
| `M6_SOTA_PUSH.md` | Earlier SOTA push report |
| `COMPETITIVE_POSITION.md` | Honest competitive framing vs Google/DeepL/NLLB |
| `RELEASE_v0.2.0.md` | Release notes + resume checklist |
| `sample_densify.tsv` | Tiny form→gloss sample (demo only) |

## Headline results (2026-07-22, v0.2.4)

| Track | Metric | Value |
|-------|--------|------:|
| Catalog | 113 langs form→gloss product | ~99.99% |
| Chat open-set neural | mean best sacreBLEU (16 langs) | **50.19** |
| Hybrid densify\|neural | mean sacreBLEU | **53.58** |
| Hybrid product neural-first | sacreBLEU | **48.74** |
| WMT14 de→en | **NLLB-1.3B** sacreBLEU | **35.63** |
| WMT14 de→en | **product ens opus+nllb13** | **36.0** |
| WMT14 de→en | oracle multi-student | **40.18** (clears mid) |
| WMT14 de→en | opus-mt-de-en | 33.88 |
| WMT14 de→en | NLLB-600M | 33.37 |
| Gap to staged DeepL mid (40) | product sacre points | **4.0** |
| % of mid-40 | product | **90%** |

## Protocol (HF-aligned)

- **WMT14** `wmt/wmt14` de-en test, n=3003, sacreBLEU, beams=5  
- **Chat:** Tatoeba-style held sample, best of local OPUS-MT / mul-en / NLLB  
- Students densify/decode only; law pin fixed  
- GPU-safe: one model on GPU at a time; hyp cache on disk  

## Honesty

- Commercial DeepL/Google **news** SOTA is **not claimed**.  
- Product densify BLEU can include residual TM templates (product ceiling).  
- Fair open-set chat = neural numbers above.  
- Short WMT FT (v2–v4) did **not** beat base opus on test/holdout — not shipped.  
- FLORES not included (Hub data gated).  

## License

Apache-2.0 for packaging and reports. Third-party corpora and model weights remain under their original licenses and are not redistributed in this dataset.
