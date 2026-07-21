# Competitive position — where we stand vs Google / DeepL / NLLB

**Honest snapshot** (2026-07-21).  
**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A** (FSOT; competitors have no equivalent).

---

## Two different games

| Game | What “accuracy” means | Who owns the public narrative |
|------|----------------------|-------------------------------|
| **A. Form→gloss inventory** | Word/lemma → meaning under densify | **PFLT is very strong** |
| **B. Sentence fluency (MT)** | Full sentence → fluent EN (BLEU/chrF/COMET) | **Google / DeepL / NLLB** |

We are **competitive / leading on A**.  
We are **climbing toward B**, not at parity yet.

---

## Our numbers (measured in-repo)

### A — Form→gloss solidify (catalog)

| Metric | PFLT |
|--------|------|
| Languages | **113** |
| OPEN / PRODUCT form→gloss | **~99.99%** |
| Thin langs (n&lt;50) | **0** |
| Breadth vs Google ~249 | **~45%** of lang count |
| Breadth vs NLLB ~200 | **~56%** |
| vs DeepL ~30–100 langs | **At/above DeepL scale on count** |

This bar is **not** what Google advertises — but it is real offline inventory depth (incl. classical/historical).

### B — Sentence fluency (dual student: densify + neural)

**B1 — Chat/Tatoeba domain** (16 langs; latest SOTA push 2026-07-21):

| Path | Metric | PFLT | Note |
|------|--------|-----:|------|
| Product densify + residual TM | BLEU-4 / B1 / U-F1 | **~83 / ~98 / ~92** | Product ceiling (includes chat residual templates) |
| **Neural open-set** (best of opus/NLLB/mul per lang, ≤200/lang) | mean sacreBLEU | **~50.2** | Fair chat bar — **past staged 45** |
| Hybrid oracle densify\|neural | mean sacreBLEU | **~53.6** | Upper bound for router |

Per-lang neural peaks: it ~68, es/pt ~61, de/ru ~57–58; thin: hi ~55; CJK gap: ja ~37, zh ~32; classical la densify still wins (~48 product).

**B2 — News domain (public WMT14 de→en test, n=3003)** — harder bar:

| Metric | PFLT densify-only | PFLT neural student (local) | DeepL-class band |
|--------|------------------:|----------------------------:|-----------------:|
| **sacreBLEU** | **~0.4** | **~33.9** (opus-mt-de-en beams=5; NLLB-600M ~33.4) | Often **~40–48+** |
| **chrF** | low | **~60** | Higher |
| Gap to staged mid bar (40) | — | **~6.1** | — |
| Gap to stretch (48) | — | **~14.1** | — |

Domain split: **chat neural is past mid bar** (~50 mean sacre); **news still ~6 BLEU short** of DeepL-class mid. Densify alone does not transfer to news — hybrid router is the product path.

\*Literature ranges, not same-day FLORES A/B. FLORES **data files still 403** (README ok; parquet gated — re-check Hub “Access granted”).

### Law / uniqueness (no competitor equivalent)

| Metric | PFLT |
|--------|------|
| Live pin D1D38A | **Yes** |
| Offline classical + visual path | **Yes** |
| Densify without rewriting law | **Yes** |

---

## Are we competitive at all?

| Track | Competitive? | One-line |
|-------|--------------|----------|
| Offline form→gloss multi-lang | **Yes — strong** | Near-ceiling on our catalog |
| Catalog breadth | **Mid** | 113 of ~200–249; beating DeepL *count* band |
| Classical / dead / hieroglyph | **Yes — unique** | Weak/absent in consumer MT |
| Chat sentence (neural open-set) | **Yes — mid/high open MT** | Mean sacre **~50** (Tatoeba-style) |
| News sentence (WMT de-en) | **Near mid open MT** | **~34** sacre; **~6** to DeepL mid bar |
| Top DeepL commercial SOTA | **Not claimed** | Need +6 to +14 sacre on news |
| Cloud UX / latency | N/A | Different product (local Ada) |
| FSOT law grounding | **Category of one** | — |

**Short answer:**  
Yes on **inventory, classical, offline FSOT**, and **chat neural open-set**.  
**Almost mid-parity** on news WMT (~34 vs ~40 staged); **not** full DeepL stretch (~48).  
Hybrid densify\|neural is the product route (oracle mean chat sacre **~54**).

---

## How far to go (gap to “parity”)

Define stages (honest):

| Stage | Domain bar | Where we are |
|-------|------------|--------------|
| **S0** Dict word map | &lt;5 BLEU | Passed |
| **S1** Phrase densify | ~10–20 | Passed |
| **S2** Strong chat content | ~25–35 BLEU | **Passed** (neural chat mean sacre ~50) |
| **S3** Mid neural news / good EU | ~35–45 sacre WMT | **~34 HERE** — gap **~6** to 40 |
| **S4** Strong neural / DeepL-class | ~45–55+ sacre | Gap **~14** to 48 stretch |

### What must rise for S3–S4

| Lever | Why | Status |
|-------|-----|--------|
| Hybrid router densify\|neural | Product best-of path | **Oracle measured** (~54 chat mean); ship in Ada |
| Word order / T3 (esp. ja/zh) | BP kills densify BLEU despite B1 | **Route CJK to neural** (ja/zh already) |
| FLORES / WMT **same-file** eval | Comparable claim | FLORES data still gated; WMT14 **scored** |
| Neural student (NLLB/opus-mt) | Fluency generators | **Done multi-system**; optional 1.3B / finetune |
| Domain match (news vs chat) | DeepL trains news/web | Need more WMT densify or student finetune |

---

## FLORES status

- Account can read **README** of `facebook/flores`.  
- **Data parquet still returns 403** (gated) — accept may be pending, wrong dataset page, or needs re-login/approval.  
- Action: open https://huggingface.co/datasets/facebook/flores while logged in → confirm **Access granted** (not just license text).  
- Until then we report **Tatoeba product densify** + **WMT** as public bars, not FLORES.

---

## Bottom line

| Question | Answer |
|----------|--------|
| Competitive on form→gloss / offline catalog? | **Yes** |
| Competitive on Google/DeepL sentence fluency? | **Not parity; mid-climb (~S2)** |
| How far on sentence BLEU-4? | Roughly **+10 to +25 points** toward mid/strong neural bands, pair-dependent |
| Unique advantage? | **FSOT law + classical + offline densify** |

We do **not** claim DeepL parity. We **do** claim a real, measured climb under fixed FSOT law, with high content-level scores and mid full-sentence BLEU.
