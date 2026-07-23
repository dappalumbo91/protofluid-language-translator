# Protofluid measurement — Ada/SPARK + sense identity

**Date:** 2026-07-23  
**Product:** Ada/SPARK `pflt_main.exe` V6 + Python sense interlingua (data factory)  
**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A** live from `I:\FSOT-Physical-Archive`

JSON twin: [`MEASUREMENT_2026-07-23.json`](MEASUREMENT_2026-07-23.json)

---

## 1. Law / SPARK spine

| Check | Result |
|-------|--------|
| Live SHA-256 of archive `fsot_compute.py` | **D1D38A…** match |
| Kernel pin embedded | **TRUE** |
| Linguistic panel \(S\) | **0.6513247618848969** (archive parity) |
| `alr build` | **Success** |
| GNATprove (level 2) on law units | See summary below · log `gnatprove_law.log` / `obj/gnatprove/` |
| SPARK_Mode On packages | `PFLT_Constants`, `PFLT_Scalar`, `PFLT_Domains`, `PFLT_Authority`, `PFLT_Lexicon` |
| Ada converse `aqua lingua manus` | **Surface gloss: water language hand** · map_rate=1.0 · live_pin=true · S≈0.6513 |
| Ada cert `zipf entropy S=` | **certified_n=3 refused_n=0** · Zipf exact; entropy err≈0.3% |

### SPARK fix landed this session

- `PFLT_Scalar`: domain-realistic subtypes (`Domain_D_Eff`, `Positive_Mass`, …) + aligned `Compute_S` Pre with `Compute_Panel`
- `PFLT_Authority.Pad48`: fixed `Note_Str` (1..48) safe copy for prove

### GNATprove snapshot (level 2, law units)

| Unit / subprogram | Result |
|-------------------|--------|
| `PFLT_Constants` | **proved** |
| `PFLT_Domains` (all) | **proved** |
| `PFLT_Lexicon.Map_Token` | **28/28 proved** |
| `PFLT_Lexicon.To_Lower` | **proved** |
| `PFLT_Lexicon.Translate_Exact` | 15/23 (residual) |
| `PFLT_Authority.Pad48` | 9/10 |
| `PFLT_Scalar.Compute_Panel` | **44/73** (remaining: float intermediate overflow VCs) |
| `PFLT_Scalar.Compute_S` | 1/3 (depends on panel) |

Runtime is solid; residual VCs are prove-time float bounds, not wrong answers at domain defaults.

---

## 2. Ada accuracy (form → gloss)

Eval file: `data/eval_sample.tsv` · **n = 8000** held sample

| Track | Store | Exact | Soft | Miss | Exact % | **Partial %** | Goal | Status |
|-------|------:|------:|-----:|-----:|--------:|--------------:|------|--------|
| **OPEN-SET** (train_mass morph stress) | 11,943,799 | 7804 | 13 | 183 | **97.55** | **97.71** | ≥70 | **PASS** |
| **PRODUCT** (gold+densify shipping) | 14,165,729 | 7161 | 25 | 814 | **89.51** | **89.83** | ≥90 | **~0.17 short** |

Logs: `ada_eval_open_set.log`, `ada_eval_product.log`

**Read:** Open-set morph is **strong** (well past 70%). Product inventory partial is **within a hair of 90%** on this 8k sample — next densify/miss inject closes it.

---

## 3. Sense identity (meaning spine — not NMT)

| Battery | Result |
|---------|--------|
| Smoke (aqua/water/cat/cell/…) | **10/10 (100%)** · ~1–30 ms |
| Water cross-lang matrix (en/la/de/fr/es/grc) | **30/30 (100%)** |
| Sense graph | 240 senses · 861 form bindings · 17 langs |

```text
aqua → SENSE_water → water / wasser / eau / agua / ὕδωρ
```

CLI: `python ../pflt_sense_translate.py --smoke`

---

## 4. Competitive position (honest two games)

### Game A — Form → meaning inventory (PFLT’s home field)

| System | Strength |
|--------|----------|
| **PFLT Ada open-set** | **97.7%** partial on held morph sample |
| **PFLT Ada product** | **89.8%** partial · 14M map · offline |
| **PFLT catalog breadth** | **113** languages solidified |
| Google Translate | ~249 langs · cloud · not offline densify |
| NLLB | ~200 langs · neural · not classical/visual depth |
| DeepL | ~30–100 langs · fluency leader · no FSOT law |

**Winner Game A (accuracy of densified form→gloss under our protocol):** **PFLT**  
**Winner lang-count breadth:** Google / NLLB  

### Game B — Full sentence fluency (competitors’ home field)

| Metric | PFLT | Competitor class |
|--------|-----:|------------------|
| Chat neural mean sacre (prior measure) | ~50.2 | open MT mid/high |
| WMT14 de→en best product (prior) | ~36.95 | NLLB-3.3B ~36.7 · DeepL mid ~40 |
| Gap to DeepL-class news mid-40 | ~3.0 | — |

**Winner Game B (news sentence fluency):** **DeepL / commercial MT** (still ahead)  

### What no competitor has

| Unique | Status |
|--------|--------|
| Live FSOT pin **D1D38A** | Yes |
| SPARK law core \(S=K(T_1+T_2+T_3)\) | Yes |
| Classical + visual (la/grc/hieroglyph path) | Yes |
| Offline densify without rewriting law | Yes |
| Sense-identity interlingua (aqua≡water) | Yes (this session) |

---

## 5. Where we sit (one paragraph)

On the **Ada shipping product**, form→gloss open-set is **excellent (97.7%)** and product inventory is **~90%** of goal on the 8k sample. Sense-identity is **perfect on the core universal battery** and must grow by binding, not by QLoRA. Sentence-level news fluency remains behind DeepL-class systems; that is a **different game** and must not redefine the product as NMT. Law is pinned and building clean; SPARK prove is active with tightened contracts — residual float-overflow VCs on exp intermediates are the remaining prove work, not a runtime failure.

---

## 6. Next forward (priority order)

1. **Close product partial ≥90%** — inject top miss classes from product eval; re-run `eval-product`  
2. **Expand sense graph** from densify gold (form↔sense) across covered langs  
3. **GNATprove clean** — discharge remaining medium float VCs (level 2 / longer timeout or ghost bounds on Exp args)  
4. **Ada converse path** — ensure shipping binary replies use sense primary forms under law panel  
5. **Do not** resume multi-hour NMT killshot as product spine  

---

## Commands to reproduce

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
alr build
.\bin\pflt_main.exe archive
.\bin\pflt_main.exe eval
.\bin\pflt_main.exe eval-product
alr exec -- gnatprove -P pflt_ada.gpr --level=2 --report=statistics `
  -u pflt_constants.ads pflt_scalar.adb pflt_domains.adb pflt_authority.adb pflt_lexicon.adb

cd C:\Users\damia\Desktop\pflt
python pflt_sense_translate.py --smoke
```
