---
license: apache-2.0
pretty_name: PFLT FSOT Sample + Benchmark Snapshot
tags:
  - translation
  - multilingual
  - evaluation
  - fsot
  - sacrebleu
  - offline
task_categories:
  - translation
language:
  - multilingual
size_categories:
  - n<1K
---

# PFLT FSOT — sample densify + benchmark snapshot

**Version:** `0.2.0` (2026-07-21)  
**Companion model card:** [dappalumbo91/pflt-fsot](https://huggingface.co/dappalumbo91/pflt-fsot)  
**Code:** [protofluid-language-translator](https://github.com/dappalumbo91/protofluid-language-translator)

## Contents

| File | Role |
|------|------|
| `sample_densify.tsv` | Small form→gloss densify sample for demos |
| `metrics_snapshot.json` | Public catalog + MT benchmarks (sacreBLEU / chrF) |
| `DATASET_README.md` | This card |

## What this is **not**

- Not the full multi-GB densify/gold lexicon (local product only)  
- Not FLORES scores (Hub parquet still gated)  
- Not a claim of commercial DeepL news SOTA  

## Headline numbers (v0.2.0)

| Track | Metric | Value |
|-------|--------|------:|
| Catalog | langs / form→gloss product | 113 / ~99.99% |
| Chat neural open-set | mean best sacreBLEU (16 langs) | **50.19** |
| Hybrid oracle | mean sacreBLEU | **53.58** |
| WMT14 de→en | opus-mt-de-en sacreBLEU | **33.88** |
| WMT14 de→en | NLLB-600M sacreBLEU | **33.37** |

Full tables and honesty notes: model card + `metrics_snapshot.json`.

## License

Apache-2.0 for packaging. Sample rows may derive from Wiktionary-class data — respect upstream licenses.
