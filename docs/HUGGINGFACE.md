# Hugging Face packaging

**Account:** `dappalumbo91`  
**GitHub:** https://github.com/dappalumbo91/protofluid-language-translator  
**Version:** `0.2.1` — **full verification source** on Hub + Kaggle (not metrics-only)

## Live on Hub

| Resource | URL | Notes |
|----------|-----|--------|
| **Model (full source)** | https://huggingface.co/dappalumbo91/pflt-fsot | **~395 files**: Ada `src/`, all Python factory/M6 scripts, docs, formal, reports |
| **Dataset (full source)** | https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample | Same verification tree + metrics |
| **Kaggle (full source)** | https://www.kaggle.com/datasets/damianpalumbo/pflt-fsot-benchmarks | Full pack (`pflt-Ada.zip` + root `.py` + docs/formal zips) |
| **GitHub (canonical)** | https://github.com/dappalumbo91/protofluid-language-translator | Git history; tag `v0.2.0` / `main` |
| **Cross-verify guide** | [`docs/VERIFICATION.md`](VERIFICATION.md) | How peers reproduce claims |
| **Release notes** | [`docs/RELEASE_v0.2.0.md`](RELEASE_v0.2.0.md) | Benchmark snapshot |

### What is intentionally *not* uploaded

Multi-GB densify/gold TSVs, neural weight caches, full Tatoeba/Kaikki dumps (third-party size/license). Rebuild paths are in-repo scripts.

### Gradio Space note

Creating a **hosted Gradio Space on free `cpu-basic`** currently requires a **Hugging Face PRO** subscription (API returned HTTP 402).  

The Space-ready files live in-repo under `huggingface_pflt/` (`app.py`, `requirements.txt`, model card). Options:

1. Subscribe PRO and create Space from `huggingface_pflt/`  
2. Run Gradio **locally**: `cd huggingface_pflt && pip install -r requirements.txt && python app.py`  
3. Keep model+dataset public (already done) for discovery  

**Never commit API tokens.** Use `HF_TOKEN` env from the desktop key file only for CLI upload.

## Full product still local

- Ada binary + multi-GB densify/gold: **not** on HF  
- Game drive Kaikki/Tatoeba: **D:** only  
- Law master: `I:\FSOT-Physical-Archive\...\vendor\fsot_compute.py` pin **D1D38A**  
