# PFLT v0.2.0 — Release notes & public storefront

**Date:** 2026-07-21  
**Git:** `aac7089` (SOTA gap-fill) + packaging commit  
**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A**

---

## Executive summary (where we are)

| Track | Result | vs staged bar |
|-------|--------|----------------|
| Form→gloss catalog (113 langs) | ~99.99% product/open | Near-ceiling |
| Chat neural open-set (mean sacreBLEU) | **50.19** | Past internal bar 45 |
| Hybrid densify\|neural chat | **53.58** | Past bar |
| WMT14 de→en neural student | **33.88** sacreBLEU | **−6.1** to mid-40 DeepL-class; **−14.1** to stretch 48 |
| Commercial DeepL / Google news SOTA | — | **Not claimed** |

**Stage:** **S3 mid-neural news climb** (chat already past S2).  
**Next (when rate limits allow):** hybrid router in Ada, WMT student finetune, FLORES unlock, optional larger NLLB.

---

## Public locations (versioned storefront)

| Store | URL / ID | What is stored |
|-------|----------|----------------|
| **GitHub** | https://github.com/dappalumbo91/protofluid-language-translator | Full code, docs, Ada product, scripts |
| **Hugging Face model** | https://huggingface.co/dappalumbo91/pflt-fsot | Model card, Gradio app, metrics JSON, sample densify |
| **Hugging Face dataset** | https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample | Sample densify + metrics snapshot |
| **Kaggle dataset** | `damianpalumbo/pflt-fsot-benchmarks` | Benchmark JSON + professional description markdown |

Large dumps (Kaikki, full densify, model weights) stay on local **D:** — not uploaded.

---

## Benchmark protocol (Hugging Face–compatible)

1. **WMT14 de-en test** via `datasets` (`wmt/wmt14`, `de-en`, split `test`, n=3003)  
2. Decode with local `transformers` seq2seq students, `num_beams=5`  
3. Score with **sacreBLEU** + chrF  
4. Chat: Tatoeba-style held sample, multi-system best-of per language  

Machine-readable: `huggingface_pflt/metrics_snapshot.json` and `release/metrics_snapshot.json`.

---

## Honesty notes for reviewers

- Product densify BLEU-4 ~83 on chat pack includes residual full-sentence templates (**TM product ceiling**).  
- Fair open-set chat = **neural** mean ~50 sacreBLEU.  
- News densify-only remains weak; news path is **neural student**.  
- FLORES not yet comparable (403 on parquet).  

---

## Files in this packaging pass

```text
docs/RELEASE_v0.2.0.md
docs/M6_SOTA_PUSH.md
docs/COMPETITIVE_POSITION.md
docs/HUGGINGFACE.md
huggingface_pflt/README.md          # HF model card (YAML + prose)
huggingface_pflt/DATASET_README.md
huggingface_pflt/metrics_snapshot.json
release/metrics_snapshot.json
kaggle_pflt/                        # Kaggle dataset package
```

---

## Resume checklist (later)

- [ ] Ship Ada hybrid router from oracle table  
- [ ] WMT finetune student (densify under law)  
- [ ] FLORES when access granted  
- [ ] Optional NLLB-1.3B  
- [ ] Refresh HF/Kaggle metrics after next climb  
