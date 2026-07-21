# Hugging Face packaging

**Account:** `dappalumbo91`  
**GitHub:** https://github.com/dappalumbo91/protofluid-language-translator  

## Live on Hub

| Resource | URL | Notes |
|----------|-----|--------|
| **Model** | https://huggingface.co/dappalumbo91/pflt-fsot | Card, sample densify, metrics, Gradio `app.py` |
| **Dataset** | https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample | Sample densify + metrics snapshot |

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
