---
license: apache-2.0
tags:
  - translation
  - multilingual
  - offline
  - fsot
  - linguistics
  - machine-translation
  - evaluation
  - sacrebleu
  - ada
  - classical-languages
language:
  - multilingual
  - en
  - de
  - es
  - fr
  - it
  - pt
  - ru
  - nl
  - pl
  - tr
  - ar
  - he
  - hi
  - ja
  - zh
  - ko
  - la
library_name: custom
pipeline_tag: translation
datasets:
  - wmt/wmt14
  - Helsinki-NLP/opus-mt
metrics:
  - sacrebleu
  - chrf
  - bleu
model-index:
  - name: pflt-fsot
    results:
      - task:
          type: translation
          name: Machine Translation (de→en news)
        dataset:
          name: WMT14 de-en test
          type: wmt/wmt14
          config: de-en
          split: test
        metrics:
          - type: sacrebleu
            value: 36.0
            name: sacreBLEU (product ens opus+NLLB-1.3B gen-score)
          - type: sacrebleu
            value: 35.63
            name: sacreBLEU (NLLB-200-1.3B, beams=5)
          - type: sacrebleu
            value: 33.88
            name: sacreBLEU (opus-mt-de-en student, beams=5)
          - type: sacrebleu
            value: 33.37
            name: sacreBLEU (NLLB-200-distilled-600M, beams=5)
          - type: chrf
            value: 61.06
            name: chrF (NLLB-1.3B)
      - task:
          type: translation
          name: Machine Translation (chat / Tatoeba-style open-set)
        dataset:
          name: Tatoeba-style chat sample (16 langs × ≤200)
          type: other
        metrics:
          - type: sacrebleu
            value: 50.19
            name: Mean best sacreBLEU (opus / mul-en / NLLB)
          - type: sacrebleu
            value: 53.58
            name: Hybrid oracle densify|neural mean sacreBLEU
---

# Protofluid Language Translator (PFLT) — FSOT-native

**Version:** `0.2.4` · **Snapshot:** 2026-07-22  
**Author:** dappalumbo91  
**Code:** [github.com/dappalumbo91/protofluid-language-translator](https://github.com/dappalumbo91/protofluid-language-translator)  
**Dataset mirror:** [dappalumbo91/pflt-fsot-sample](https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample)

---

## What this is

**PFLT** is an **offline-first translator intelligence** surface grounded in the FSOT free-parameter law:

\[
S = K(T_1 + T_2 + T_3)
\]

**Authority pin:** `D1D38A` (SHA-256 prefix of archive-canonical `fsot_compute.py`).

It is **not** “another LLM wrapper.” It is:

1. **Form→gloss catalog densify** under fixed law (113 languages, near-ceiling product/open inventory)  
2. **Neural students** (local Helsinki OPUS-MT, opus-mt-mul-en, NLLB-600M / **NLLB-1.3B**) for full-sentence fluency  
3. **Hybrid path** — densify for classical/short chat; neural for long/news/CJK  
4. **Ada/SPARK product binary** in the GitHub repo (Python = data factory)

### Honest claims (read first)

| Claim | Status |
|-------|--------|
| Google / DeepL commercial **news** SOTA | **Not claimed** |
| Chat-domain open-set MT (Tatoeba-style) | **Competitive mid/high open MT** (~50 mean sacreBLEU) |
| WMT14 de→en news | **90% of mid-40** (product **36.0** with NLLB-1.3B; oracle **40.18** clears mid) |
| Form→gloss multi-lang catalog | **Strong / near-ceiling** (~99.99% on 113 langs) |
| FSOT law uniqueness | **Category of one** |

Product densify BLEU can look extremely high when residual translation-memory templates are installed for known chat — that is a **product ceiling**, not open-set generalization. Fair open-set bars are the **neural student** numbers below.

---

## Benchmarks (v0.2.4)

Protocol details and JSON: `metrics_snapshot.json` in this repo.

### A — Catalog (form→gloss)

| Metric | Value |
|--------|------:|
| Language codes | **113** |
| OPEN form→gloss | **~99.99%** |
| PRODUCT form→gloss | **~99.99%** |
| Thin langs (n&lt;50) | **0** |

### B1 — Chat / Tatoeba-style (open-set neural)

Best of local students per language, ≤200 sentences/lang, **beams=5**, sacreBLEU:

| Aggregate | sacreBLEU |
|-----------|----------:|
| Mean best (16 langs) | **50.19** |
| Hybrid oracle densify\|neural | **53.58** |
| Staged bar (internal) | 45.0 |

| Lang | Best system | sacreBLEU |
|------|-------------|----------:|
| it | nllb-600M | 67.83 |
| es | opus-mt | 61.34 |
| pt | nllb-600M | 61.29 |
| ru | nllb-600M | 57.75 |
| de | opus-mt | 57.10 |
| nl | nllb-600M | 56.79 |
| fr | nllb-600M | 56.54 |
| hi | nllb-600M | 54.73 |
| tr | nllb-600M | 54.28 |
| ar | opus-mt | 53.27 |
| pl | nllb-600M | 52.66 |
| he | nllb-600M | 47.88 |
| ko | nllb-600M | 39.81 |
| ja | opus-mt | 36.55 |
| zh | nllb-600M | 32.20 |
| la | opus-mt-mul-en | 12.95 |

*Latin / some classical pairs still prefer densify product path in hybrid routing.*

### B2 — News (WMT14 German→English test, n=3003)

| System | sacreBLEU | BLEU-4 | chrF |
|--------|----------:|-------:|-----:|
| **Helsinki-NLP/opus-mt-de-en** (student, beams=5) | **33.88** | 33.38 | 59.92 |
| facebook/nllb-200-distilled-600M (beams=5) | 33.37 | 33.81 | 59.27 |
| Staged DeepL-class mid bar | 40.0 | — | — |
| Stretch SOTA bar | 48.0 | — | — |
| **Gap to 40 / 48** | **6.12 / 14.12** | — | — |

### Stage ladder

| Stage | Meaning | Status |
|-------|---------|--------|
| S0–S1 | Dict / phrase densify | Passed |
| S2 | Strong chat content | **Passed** (neural chat ~50) |
| S3 | Mid neural news (~35–45 sacre) | **~34 — HERE** |
| S4 | DeepL-class stretch (~45–55+) | Gap ~14 sacre on WMT |

---

## Architecture (FSOT)

```text
Law (fixed)  S = K(T1+T2+T3)  pin D1D38A
     │
     ├─ Densify surface   form→gloss, phrases, classical
     ├─ Neural students   OPUS-MT / mul-en / NLLB (decode only)
     └─ Hybrid router     domain/length gate (oracle measured)
```

Students **never rewrite** the law scalar. Densify grows the surface only.

---

## What ships on the Hub

| File | Description |
|------|-------------|
| `README.md` | This model card |
| `metrics_snapshot.json` | Machine-readable benchmarks v0.2.0 |
| `sample_densify.tsv` | Small densify sample (demo) |
| `app.py` | Gradio form→gloss + FSOT panel demo |
| `requirements.txt` | Demo deps |

**Not** on the Hub (by design): multi-GB densify/gold packs, Ada binary, full Kaikki/Tatoeba dumps (stay on local D:).

---

## Quickstart

### Local Gradio demo

```bash
git clone https://github.com/dappalumbo91/protofluid-language-translator.git
cd protofluid-language-translator/huggingface_pflt
pip install -r requirements.txt
python app.py
```

### Full product (Ada)

```powershell
cd pflt-Ada
alr build
.\bin\pflt_main.exe eval-product
.\bin\pflt_main.exe archive   # live D1D38A pin
```

### Reproduce sentence benchmarks (local models required)

```powershell
cd pflt-Ada
python -u m6_sota_push.py
# writes reports/M6_SOTA_PUSH.md + m6_sota_push_report.json
```

Models expected under a local cache (example):

- `Helsinki-NLP/opus-mt-{es,de,fr,ru,zh,ja,ar}-en`
- `Helsinki-NLP/opus-mt-mul-en`
- `facebook/nllb-200-distilled-600M`

---

## Remaining path to SOTA (parked for later)

1. Ship hybrid router in Ada product decode  
2. Optional WMT student finetune (still densify under law)  
3. FLORES when Hub data access unlocks  
4. Optional NLLB 1.3B / larger beams for news  
5. CJK: keep neural path (SPM), densify for inventory only  

---

## Citation / links

```bibtex
@software{pflt_fsot_2026,
  title  = {Protofluid Language Translator (PFLT) under FSOT},
  author = {Palumbo, Damian},
  year   = {2026},
  url    = {https://github.com/dappalumbo91/protofluid-language-translator},
  note   = {Law pin D1D38A; version 0.2.0 benchmarks}
}
```

- GitHub: https://github.com/dappalumbo91/protofluid-language-translator  
- Competitive position: `docs/COMPETITIVE_POSITION.md`  
- SOTA report: `docs/M6_SOTA_PUSH.md`  
- Kaggle benchmarks pack: search `pflt-fsot-benchmarks` under user `damianpalumbo`

## License

Apache-2.0 for code. Sample densify rows derived from Wiktionary-class sources — respect upstream CC-BY-SA/GFDL as applicable. Large third-party corpora (Tatoeba, WMT, OPUS, NLLB weights) remain under their original licenses and are **not** redistributed here.
