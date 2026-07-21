# Protofluid Language Translator — North Star Metrics

**One goal:** On every metric that defines a leading translator intelligence, **climb until we are first** (or clearly better than the prior best on that metric). The competitor name does not matter — only the bar does.

This is not “win BLEU only.” PFLT is a **universal translator intelligence** under FSOT law. Metrics are multi-track.

---

## Product identity (does not change)

> Map fluid language into meaning, ground claims in FSOT seed law \(S=K(T_1+T_2+T_3)\), densify knowledge without rewriting law, converse and relay — morph/lexicon is the surface; FSOT is the constitution.

---

## Metric board — beat the bar on each track

| # | Track | What “winning” means | External bar (order of magnitude) | PFLT current (approx.) | Next climb target |
|---|--------|----------------------|-----------------------------------|-------------------------|-------------------|
| **M1** | **Core open-set morph** (held-out form→gloss partial) | Honest morph stress (train_mass only) | No public GT | **Ada ~87%** open-set partial (fast climb); Latin **~94%** | Hold **≥85%**; push **≥90%** overall |
| **M1b** | **PRODUCT form→gloss** (full gold+densify) | Shipping inventory accuracy | Dict/MT train on full data | **Ada ~99.5% partial** across 20 langs | Hold **≥99%**; never regress |
| **M2** | **Exact map rate** | Exact gloss hits | — | Product **~99.5%** exact; open-set **~85%** exact | Hold product; open-set exact ≥85% |
| **M3** | **Name / entity track** | Places & proper names | Gazetteer-heavy systems | Name deploy historically **~79%** | Hold **≥80%**, push **≥90%** with Pleiades + densify |
| **M4** | **Language catalog** | Distinct language/script surfaces productively handled | Google Translate **~249** langs; NLLB **200**; DeepL **~30–100** | **20** gold codes · **~1.02M** quality rows · deploy A_strong **~15–16** langs | Grow toward **100 → 200 → 249+** *meaningful* surfaces |
| **M5** | **Classical / dead / visual** | la, grc, ang, akk, sum, **hieroglyphs**, etc. | Weak or absent in consumer MT | Deploy sample **~84%** partial when known; Latin open-set **~50%** | Own this band: **best offline classical+visual translator** |
| **M6** | **Modern sentence quality** | Tatoeba BLEU-style bars (src→en); path to FLORES/COMET | WMT leaders: frontier LLMs; EU pairs often DeepL-strong | **v1 live:** overall BLEU~1.9 · U-F1~24 · cov~87% (word+phrase table, offline) | Climb phrase table + word order; then FLORES sample |
| **M7** | **FSOT law pin** | Authority hash + scalar panel every act | N/A (unique) | **D1D38A** pin, `authority_ok` | Keep **100%** law-backed turns |
| **M8** | **Knowledge + converse** | Multi-turn relay, ledger growth, archive cite, teach panel | Consumer MT has little/no persistent grounded ledger | Converse + ledger + teach + densify + cert math | Product metrics: multi-turn coherence, non-contradiction with law |
| **M9** | **Offline / local** | No paid API required to climb or translate | Cloud MT depends on vendors | Full local chew + archive | Stay **offline-first** |
| **M10** | **Certified numeric claims** | No vibes math as law | LLMs invent numbers | `certified_math` gate | Expand Lean bridge when ready |

---

## Immediate campaign (now) — **Ada-primary**

1. **Ada open-set climb** → **M1 ≥ 70%** partial on held-out `eval_sample.tsv`  
   (`pflt_main.exe eval` with `train_mass.tsv` only).  
2. Fuel: `export_data_for_ada.py` → densify + gold_core + train_mass + paradigm expand  
   (sources: expanded_gold ~1.3M, classical lexica, hieroglyphs, Dictionary mine).  
3. Ada self-climb: `pflt_main.exe inject FORM GLOSS` grows densify offline.  
4. Do **not** claim open-set if eval forms sit in train_keys.  
5. After 70%: freeze report → **M2 exact**, **M5 classical/visual**, **M4 catalog**, then **M6 modern**.  
6. Python is **data factory only** — not the product binary.

Commands:

```powershell
cd pflt-Ada
python export_data_for_ada.py
alr build
.\bin\pflt_main.exe eval
.\bin\pflt_main.exe converse "aqua lingua manus"
```

---

## Rules of the climb

- **Honest splits** — no silent test leakage into train for claimed open-set numbers (`supervised` densify is labeled; `oracle` is debug only).  
- **Law never rewritten** by dialogue or densify.  
- **Multi-metric** — winning M1 does not skip M7–M9.  
- **Competitor is the bar**, not the brand: if a new system sets a higher bar on any Mi, that becomes the new target.

---

## One-line north star

> **Climb every translator-intelligence metric until we hold the bar — breadth, classical/visual depth, open-set accuracy, grounded knowledge, and FSOT law — offline-first, no excuses.**
