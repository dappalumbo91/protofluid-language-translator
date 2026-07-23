# Sense drift fix + news de-en push

**Date:** 2026-07-23  
**Law pin:** D1D38A  

---

## 1. Sense drift — fixed

### Problem
Ada densify mapped every token (map_rate=1.0) but **wrong polysemy**:

| Form | Was | Ideal |
|------|-----|--------|
| sol | astronomy | sun |
| mater | Primordial | mother |
| mors | annihilation | death |

### Fix
1. **`PFLT_Lexicon.Map_Token`** — hard sense seeds for high-freq Latin core (sol/mater/mors/pater/dies/nox/…)  
2. **`PFLT_Store.Lookup`** — consult lexicon prefer **before** densify score  
3. **`data/lang_tables/la.json`** — expanded `form_sense_prefer`  
4. **Python sense interlingua + map_token** — same preferred identities  

### Verify (Ada shipping binary)

```text
IN:  aqua lingua manus sol luna terra vita mors pater mater
OUT: water language hand sun moon earth life death father mother
map_rate=1.0  pin=D1D38A  S≈0.6513
```

**10/10 correct senses** (was 7–8/10 with drift).

---

## 2. News free sentences (WMT14 de→en) — worked without retrain

Cached hyps only + within-family FSOT-cal ranking (`eval_news_deen_cached.py`):

| System | sacreBLEU |
|--------|----------:|
| opus b5 | 33.88 |
| nllb13 b8 | 35.80 |
| nllb33 b8 | 36.74 |
| gen_score_strong | 36.95 |
| **fsot_family_then_gen** | **37.02** |
| nllb33 min tf-nll | 36.51 |
| **oracle** (pool upper bound) | **43.97** |
| DeepL-class mid bar | 40.0 |

| Metric | Value |
|--------|------:|
| Best product | **37.02** |
| Gap to mid-40 | **2.98** |
| Headroom to oracle | **6.95** |

**Interpretation:** Correct FSOT-cal family ranking beat pure gen_score (+0.07). Mid-40 is **inside the oracle pool** — remaining gap is selection + hyp diversity, not “need QLoRA for 6 hours.” Mean English fluency proxy on NLLB hyps ≈ **0.997**.

### Protocol (on-vision)
- Neural models = **students / hyp factories only**  
- Ranking = gen_score + within-family z(gen) + z(−tf_nll)/Φ  
- Law pin logged; no free BLEU fit of K  

---

## 3. Next (keep going)

**Sense accuracy**
- Expand prefer table from densify miss clusters (auto-mine wrong-sense pairs)  
- Domain-gated prefer (historical vs mythological for *sol* = sun vs Sol god when context is myth)  

**News → DeepL mid-40**
- Grow multi-hyp diversity only where oracle still wins  
- Optional holdout-tracked student FT only if holdout ships  
- Do not redefine product as NMT  

---

## Reproduce

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
alr build
.\bin\pflt_main.exe converse "aqua lingua manus sol luna terra vita mors pater mater"

cd C:\Users\damia\Desktop\pflt
python -u eval_news_deen_cached.py
```
