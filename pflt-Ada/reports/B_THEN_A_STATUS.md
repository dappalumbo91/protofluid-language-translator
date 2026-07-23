# B then A status — **COMPLETE**

**Order:** multi-hyp diversity (B) first · wrong-sense mining (A) second  
**Date:** 2026-07-23 · re-eval 18:29 UTC

---

## B — Multi-hyp diversity (**done**)

### Before expand (baseline)

| Metric | Value |
|--------|------:|
| Product gen | 36.50 sacre |
| Oracle | 44.41 sacre |
| Mean unique hyps / sent | 7.3 |
| Selection-gap sentences | 1576 (52.5%) |
| Pool-weak (oracle SB &lt; 0.15) | 77 |

### After expand + family-safe re-eval

| Metric | Value |
|--------|------:|
| **Best product** | **36.79** (`gen_score_nllb33`) |
| `fsot_family_then_gen` | 36.78 |
| Naive cross-family gen | 36.51 (poisoned — worse) |
| **Oracle** | **46.12** (+1.71 vs pre-expand) |
| Mean unique hyps / sent | **14.02** (was 7.3) |
| Gap to mid-40 | **3.21** |
| Selection-gap sentences | **1867 (62.2%)** |
| Pool-weak | **62** (was 77) |
| Pin D1D38A | OK |

### Expand jobs landed

| Cache key | Role |
|-----------|------|
| nllb33 b8 ret5 | more candidates |
| nllb13 b8 ret3/5, lp 0.9/1.1 | beam / length diversify |
| nllb600 b8 ret3 | alt family |
| opus b8 ret3 | architecture diversity |

### Read

- **Pool improved:** oracle 44.41 → 46.12; mean pool ~7 → 14; fewer pool-weak sentences.
- **Product barely moved** (36.5 → 36.8): headroom is almost all **selection**, not missing hyps.
- Cross-family raw gen max **hurts** — stay within nllb33 or use family-then-gen.

Report: `pflt-Ada/reports/NEWS_DEEN_CACHED.{json,md}`

---

## A — Wrong-sense mining (**done**, before B re-eval)

### Outputs

- `data/wrong_sense_mined.json` — 71 unique forms where densify ≠ gold  
- `pflt-Ada/data/sense_prefer.tsv` — **177** form→gloss force rows  
- `data/lang_tables/la.json` — expanded prefer  
- Ada `PFLT_Store.Load_Default_Packs` loads **sense_prefer.tsv last** (force overwrite)  
- Ada `PFLT_Lexicon` hard seeds expanded (sol/mater/mors/homo/corpus/…)  

### Top mined drifts

via, pes, homo, corpus, filia, anima, terra, magister, gramma, ψυχή, …

### Verified converse

```text
sol luna terra vita mors pater mater
→ sun moon earth life death father mother
```

---

## Next lever (on-vision)

**Close selection gap** — do **not** mix uncalibrated cross-family gen scores.

1. Mine sentences where oracle ≠ product (`news_hard_sel_indices.json` written).  
2. Within-nllb33 FSOT-cal over full ret5 pool (features / length / domain).  
3. Optional: domain-gated sense prefer for residual polysemy (classical track).  
4. Domain LoRA only if holdout ships — student, not law.

---

## Reproduce

```powershell
cd C:\Users\damia\Desktop\pflt
python -u eval_news_deen_cached.py
python -u scripts\analyze_news_oracle_gap.py

cd pflt-Ada
alr build
.\bin\pflt_main.exe converse "homo corpus filia anima vis"
```
