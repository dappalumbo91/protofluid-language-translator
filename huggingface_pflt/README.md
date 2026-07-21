---
license: other
tags:
  - translation
  - linguistics
  - offline
  - fsot
  - multilingual
  - ada
language:
  - multilingual
library_name: custom
pipeline_tag: translation
---

# Protofluid Language Translator (PFLT) — FSOT-native

**Offline-first translator intelligence** grounded in the FSOT free-parameter law:

\[
S = K(T_1 + T_2 + T_3)
\]

**Authority pin:** `D1D38A` (SHA-256 of archive `fsot_compute.py`).

> This is **not** a claim of Google/DeepL neural sentence BLEU parity.  
> It **is** a densify + morph surface under FSOT law, with classical/visual depth and multi-language form→gloss solidification.

## What ships in this Hub pack

| Asset | Description |
|-------|-------------|
| `app.py` | Gradio demo (local or HF PRO Space): form→gloss + FSOT panel |
| `sample_densify.tsv` | Small densify sample (full multi-GB packs stay local) |
| `metrics_snapshot.json` | Catalog open/product + M6 snapshot |
| Law | Seeds frozen; students densify **without rewriting law** |

Full product binary: **Ada/SPARK** on GitHub  
https://github.com/dappalumbo91/protofluid-language-translator

**Dataset mirror:** https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample

## Coverage (full local packs)

| Metric | Value |
|--------|------:|
| Language codes | **113** |
| Form→gloss OPEN | **~99.99%** |
| Form→gloss PRODUCT | **~99.99%** |
| Thin langs (n&lt;50) | **0** |
| M6 sentence BLEU-4 (offline climb) | **~2.4** |
| M6 BLEU-1 / U-F1 | **~44 / ~34** |

## FSOT law (no ad-hoc scalar)

Archive: `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py`  
Audit: repo `docs/FSOT_LAW_AUDIT.md` — archive \(S\) matches PFLT Python to **0** absdiff on domain fixtures.

## Hosted Gradio Space

Free Gradio Spaces currently require **HF PRO** (HTTP 402 on create). Run locally:

```bash
cd huggingface_pflt
pip install -r requirements.txt
python app.py
```

## License / data

- Code: GitHub LICENSE  
- Sample densify: derived from Wiktionary-class sources — respect CC-BY-SA/GFDL as applicable  
- Large dumps not hosted here  
