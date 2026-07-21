# Protofluid-Ada — Solidify Core + Fill Partials

**Product:** Ada V6 · pin **D1D38A**  
**Stance:** DeepL-class density on **20** languages first; expand only after partials hold.

---

## Headline (after partial climb)

| Track | Result |
|-------|--------|
| **Deploy** (form in lexicon) | **~83.6% partial · ~82.3% exact** |
| **Open-set full** (n=20k held-out) | **~39.3% partial · ~36.6% exact** |
| **Ada product eval** (n=8k classical-weighted) | **~42.4% partial · ~39.3% exact** |
| **Latin open-set** | **~65.8% partial · ~61.6% exact** |
| Train mass | **~3.61M** keys (stem densify; eval leaks purged) |
| Gold | **~1.01M** rows · **20** codes |

### Climb progress

| Metric | Pre-solidify | Now |
|--------|--------------|-----|
| Overall open-set partial | ~31% | **~39%** |
| Ada eval partial | ~37% | **~42%** |
| Latin open-set partial | ~51% | **~66%** |

### Core five

| Lang | Open-set partial | Deploy | Note |
|------|------------------|--------|------|
| **la** | **~66%** | ~80% | Primary; next **≥70%** |
| grc | ~3% | ~80%+ | Unicode densify next |
| ang | ~9% | strong | OE peels next |
| egy | ~0% | ~88% | Transliteration densify |
| en | ~1% | ~90%+ | Panel junk removed; hard OOV |

---

## How we fill partials (frozen)

1. **Quality gold** — `solidify_core_langs.py` (no meta / no FSOT panel lemmas)  
2. **Paradigm densify** — train stems only  
3. **Stem climb** — `climb_partials.py` strips suffixes from train forms → maps stems to same gloss  
4. **Ada morph peels** — match climb reattachments (`PFLT_Morph`)  
5. **Purge eval leaks** — never count open-set if form exact-keyed into train  
6. **Measure** — `report_translation_coverage.py` + `pflt_main.exe eval`  

Do **not** inject held-out eval forms into train (that inflates partials dishonestly).

---

## Reproduce

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
python solidify_core_langs.py
python climb_partials.py
alr build
.\bin\pflt_main.exe eval
python report_translation_coverage.py
```

Reports: `pflt-Ada/reports/climb_partials_report.json`, `TRANSLATION_LANGUAGE_ARCHIVE.md`

---

## Still to fill

1. Latin **66% → 70%+** (remaining misses = true OOV lemmas / wrong-stem gloss)  
2. Greek Unicode open-set (largest non-Latin gap)  
3. OE / Egyptian open-set densify  
4. Overall open-set **39% → 55% → 70%**  
5. Hold deploy **≥85%**  
6. Then expand language catalog  

---

## One-line

> Stem densify + morph peels raised **Latin open-set to ~66%** and **overall open-set to ~39% / Ada eval ~42%** — keep climbing the same 20 languages until partials are filled.
