# Cross-verification guide — PFLT / FSOT

This document tells **independent reviewers** how to obtain the **actual program**, reproduce catalog metrics, and score sentence benchmarks.  
It is intentionally separate from marketing-style cards.

**Version:** 0.2.1  
**Law:** \(S = K(T_1+T_2+T_3)\) authority pin **D1D38A**  
**Git tag:** `v0.2.0` / `main` (see release notes for snapshot scores)

---

## 1. Where the *code* lives (not just metrics)

| Location | What you get |
|----------|----------------|
| **GitHub (canonical)** | Full program: Python data factory + Ada/SPARK product sources + docs + eval scripts |
| **Hugging Face model `dappalumbo91/pflt-fsot`** | Same verification tree (source + docs + reports + sample data) + Gradio demo |
| **Hugging Face dataset `dappalumbo91/pflt-fsot-sample`** | Metrics + sample densify + reports (lighter mirror) |
| **Kaggle `damianpalumbo/pflt-fsot-benchmarks`** | Full verification source pack + benchmark JSON/CSV |

**Not redistributed** (too large / third-party): multi-GB densify/gold packs, full Tatoeba extract, Kaikki dumps, neural weight caches. Scripts document how to rebuild or download those locally.

Canonical code URL:

```text
https://github.com/dappalumbo91/protofluid-language-translator
```

Clone:

```bash
git clone https://github.com/dappalumbo91/protofluid-language-translator.git
cd protofluid-language-translator
git checkout v0.2.0   # or latest main
```

From Hugging Face (full tree upload):

```bash
# requires: pip install huggingface_hub
huggingface-cli download dappalumbo91/pflt-fsot --local-dir ./pflt-fsot --repo-type model
```

From Kaggle:

```bash
kaggle datasets download -d damianpalumbo/pflt-fsot-benchmarks -p ./pflt-kaggle --unzip
```

---

## 2. Repository layout (what matters for verification)

```text
protofluid-language-translator/
  README.md
  docs/                     # competitive position, law audit, release, THIS file
  PFLT_FSOT_2_1_aligned.py  # Python law-aligned surface
  fsot_law_bridge.py        # pin D1D38A bridge
  dual_track_eval.py        # open vs product tracks
  huggingface_pflt/         # Hub card + Gradio demo
  pflt-Ada/                 # **shipping product (Ada/SPARK)**
    src/*.ads *.adb         # full Ada sources
    *.py                    # densify / M6 / solidify / WMT eval factory
    reports/                # measured JSON + markdown
    data/                   # small samples + archive pin artifacts (not multi-GB packs)
  release/metrics_snapshot.json
  kaggle_pflt/              # Kaggle packaging mirror
```

---

## 3. Reproduce without multi-GB packs (smoke)

```bash
python -c "import ast; ast.parse(open('PFLT_FSOT_2_1_aligned.py',encoding='utf-8').read()); print('python parse ok')"
# Ada (if GNAT/Alire installed):
cd pflt-Ada && alr build
```

Law pin artifact (archive SHA culture):

```text
pflt-Ada/data/archive_linguistics/fsot_compute_AUTHORITY_PIN.json
pflt-Ada/data/archive_linguistics/live_pin.json
```

---

## 4. Reproduce form→gloss catalog claims

Requires local densify/gold rebuilt via scripts (or your own packs). Then:

```powershell
cd pflt-Ada
python report_translation_coverage.py
python solidify_covered_95.py   # optional solidify pass
# Ada product eval if built:
.\bin\pflt_main.exe eval-product
```

Published snapshot: ~**113** langs, ~**99.99%** open/product form→gloss (see `reports/gap_fill_verify.json`, `metrics_snapshot.json`).

---

## 5. Reproduce sentence benchmarks (HF-aligned protocol)

### 5a WMT14 German→English (public, no Tatoeba dump)

```powershell
cd pflt-Ada
# Requires: pip install transformers datasets sacrebleu torch
# Local model: Helsinki-NLP/opus-mt-de-en and/or facebook/nllb-200-distilled-600M
python -u eval_wmt14_deen.py
# Full dual-track SOTA script:
python -u m6_sota_push.py
```

**Published v0.2.0 (self-reported):**

| System | sacreBLEU |
|--------|----------:|
| opus-mt-de-en beams=5 | **33.88** |
| NLLB-600M beams=5 | **33.37** |

### 5b Chat / multi-lang neural

`m6_sota_push.py` scores Tatoeba-style samples when local pair cache exists. Without cache, still verify script + report JSON:

```text
pflt-Ada/reports/m6_sota_push_report.json
pflt-Ada/reports/M6_SOTA_PUSH.md
release/metrics_snapshot.json
```

**Published mean best chat sacreBLEU:** **50.19** (16 langs, ≤200/lang, best of opus/mul/NLLB).

---

## 6. What we do *not* claim

- Commercial DeepL / Google **news** SOTA  
- FLORES scores (Hub parquet may still be gated)  
- That product densify BLEU with residual TM templates is open-set generalization  

Honest framing: `docs/COMPETITIVE_POSITION.md`.

---

## 7. Minimal file set for peer review checklist

- [ ] Ada sources under `pflt-Ada/src/` present and buildable or reviewable  
- [ ] Python eval scripts: `m6_sota_push.py`, `eval_wmt14_deen.py`, solidify/coverage  
- [ ] Reports JSON match model-card tables  
- [ ] Law pin / constants not silently refit to BLEU  
- [ ] Large third-party corpora not required to *read* the code  

---

## 8. Contact / issues

Open issues on GitHub:  
https://github.com/dappalumbo91/protofluid-language-translator/issues
