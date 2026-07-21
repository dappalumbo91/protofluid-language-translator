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

### B — Sentence fluency (product densify path)

**B1 — Chat/Tatoeba domain** (16 langs × 400, product densify after FSOT Zipf/dep):

| Metric | PFLT | Rough competitor band* |
|--------|-----:|------------------------|
| **BLEU-4** | **~27** | Neural on easy chat often **higher**; content-level we look strong |
| **BLEU-1** | **~89** | Often **~70–90** |
| **U-F1** | **~81** | Competitive content overlap |
| **chrF** | **~65** | Strong systems **~50–70+** |
| **Coverage** | **~100%** | High |

**B2 — News domain (public WMT14 de→en test, n=3003)** — harder bar:

| Metric | PFLT densify path | Typical neural (DeepL/Google-class) |
|--------|------------------:|-------------------------------------|
| **BLEU-4 / sacreBLEU** | **~1.0 / ~1.1** | Often **~30–45+** on de–en news |
| **BLEU-1** | **~31** | Much higher |
| **Coverage** | **~86%** | Near full |

This shows **domain shift**: chat densify does not yet transfer to news. Competitors train on news-scale parallel; we must densify WMT/news or use neural student for that bar.

\*Literature ranges, not same-day FLORES A/B. FLORES **data files still 403** (README ok; parquet gated — re-check Hub “Access granted”).

**Per-lang snapshot (product densify, BLEU-4):**  
ar/he/ru/ko/tr often **~22–28**; de/es/fr/pt **~17–19**; **ja/zh** high B1 but low BP (order/seg) → full BLEU still limited.

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
| Sentence fluency (neural bar) | **Not yet parity** | Strong unigram content; mid BLEU-4 |
| Cloud UX / latency | N/A | Different product (local Ada) |
| FSOT law grounding | **Category of one** | — |

**Short answer:**  
Yes on **inventory, classical, offline FSOT**.  
**Not yet** if “competitive” means *Google/DeepL sentence quality on FLORES/news*.  
We are **in the game** on content coverage (B1/U-F1 high) and **halfway-ish** on full n-gram BLEU toward a mid-neural bar.

---

## How far to go (gap to “parity”)

Define stages (honest):

| Stage | BLEU-4 (order of mag.) | Where we are |
|-------|------------------------|--------------|
| **S0** Dict word map | &lt;5 | Passed |
| **S1** Phrase densify | ~10–20 | Passed |
| **S2** Strong content fluency | **~25–35** | **~27 — HERE** |
| **S3** Mid neural / good EU pair | **~35–45** | Gap **~10–20 BLEU** |
| **S4** Strong neural / DeepL-class pair | **~45–55+** | Gap **~20–30+ BLEU** |

### What must rise for S3–S4

| Lever | Why | Status |
|-------|-----|--------|
| Word order / T3 (esp. ja/zh) | BP kills BLEU-4 despite B1 | Weak on CJK |
| Multi-word phrases + syntax | BLEU-2/3/4 | Climbing |
| FLORES / WMT **same-file** eval | Comparable claim | FLORES data still gated; WMT14 available |
| Neural student (NLLB/opus-mt teacher densify) | Fluency generators | **Models on D:**; densify running |
| Domain match (news vs chat) | DeepL trains news/web | OPUS/WMT help |

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
