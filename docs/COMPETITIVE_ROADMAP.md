# Competitive roadmap — accurate status vs competition

**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A** (unchanged; never fitted to BLEU).  
**Measured:** 2026-07-22 stronger student (`m6_stronger_student_report.json` / NLLB-1.3B).

---

## 1. Two competitions (do not mix them)

| Arena | Competitor definition of “win” | PFLT status |
|-------|--------------------------------|-------------|
| **A. Inventory / form→gloss** | Coverage + sense under offline densify | **Winning our catalog** (~99.99% on 113 langs) |
| **B. Sentence MT** | sacreBLEU / chrF / COMET on held-out sentences | **Chat: competitive**; **News: trailing DeepL-class** |

Google/DeepL/NLLB are judged almost entirely on **B**.  
We already win parts of **A** (especially classical / offline / FSOT). Beating them “accurately” means closing **B** without lying about A.

---

## 2. Scoreboard (measured)

### A — Catalog

| Metric | Us | Google-ish | DeepL-ish | NLLB-ish |
|--------|---:|-----------:|----------:|---------:|
| Lang count | **113** | ~249 | ~30–100 | ~200 |
| Form→gloss on our catalog | **~99.99%** | N/A (not their product metric) | N/A | N/A |
| Classical / dead / hieroglyph | **Strong** | Weak | Weak | Weak |
| FSOT law pin | **Yes** | No | No | No |

**Verdict A:** Competitive / leading on **our** product definition. Not “more languages than Google.”

### B1 — Chat / easy parallel (Tatoeba-style open-set)

| System path | sacreBLEU (mean) | Notes |
|-------------|-----------------:|-------|
| Neural best-of (opus/mul/NLLB) | **50.19** | Fair open-set |
| Hybrid oracle densify\|neural | **53.58** | Product upper bound |
| Staged internal bar | 45 | **Passed** |
| Strong open MT chat (rough) | ~45–65+ | We sit mid/high |

**Per-lang neural highs:** it 68 · es/pt 61 · de/ru ~57–58 · hi 55  
**Gaps:** ja 37 · zh 32 · la neural 13 (densify wins classical)

**Verdict B1:** **Competitive** on chat open-set. Not SOTA vs every commercial pair, but past mid bar.

### B2 — News (WMT14 de→en test, n=3003) — the hard public bar

| System | sacreBLEU | Gap to 40 mid | Gap to 48 stretch |
|--------|----------:|--------------:|------------------:|
| Densify-only | ~0.4 | — | — |
| opus-mt-de-en beams=5 | 33.88 | −6.1 | −14.1 |
| NLLB-600M beams=5 | 33.37 | −6.6 | −14.6 |
| **NLLB-1.3B beams=5** | **35.63** | **−4.4** | **−12.4** |
| **Product ens (opus+nllb13 gen-score)** | **36.0** | **−4.0** | **−12.0** |
| Oracle (multi-student) | **40.18** | **clears mid** | −7.8 |
| DeepL-class mid (staged) | ~40 | 0 | — |
| Strong commercial stretch | ~45–55 | — | 0 |

**Verdict B2:** **90% of mid-40** with NLLB-1.3B; oracle already clears mid. Product still needs better picker / quality FT.

---

## 3. Stage ladder (honest)

```text
S0 Dict          ████████████ DONE
S1 Phrase        ████████████ DONE
S2 Chat strong   ████████████ DONE  (neural ~50)
S3 Mid news      █████████░░░ HERE  (~36 / need ~40; oracle clears)
S4 DeepL-class   ████░░░░░░░░       (need ~45–55)
```

---

## 4. What is left to be competitive / beat them (priority order)

| # | Lever | Closes | Effort | Expected gain |
|---|-------|--------|--------|----------------|
| **1** | **Ship hybrid router** (densify short/classical; neural long/news/CJK) | Product accuracy vs single-path | Low | Realizes measured **~53.6** chat hybrid; better UX |
| **2** | **Learned picker on opus+nllb13** (oracle already 40.18) | News −4 gap | Med | Close product 36→~39–40 |
| **3** | **Quality news data + careful FT** (train-holdout; short WMT FT failed) | News single hyp | High | **+1–4** if data quality holds |
| ~~3~~ | ~~Stronger student NLLB-1.3B~~ | **DONE** (+1.75 single, product 36.0) | — | — |
| **4** | **CJK order** always neural SPM path (no EN-dep densify for ja/zh) | ja/zh chat | Low | Lift ja/zh from ~32–37 toward EU band |
| **5** | **FLORES** same-file public bar | Comparable claim vs NLLB papers | Blocked until Hub access | Credibility, not training |
| **6** | **Breadth** more Kaikki langs toward 150–200 | Catalog vs Google count | Med | Count game only |
| **7** | **COMET / human** spot checks | Beyond BLEU honesty | Med | Avoid BLEU-only overclaim |

### What will **not** beat DeepL alone

- More form→gloss densify on chat templates (product ceiling ≠ news SOTA)  
- Refitting the FSOT law scalar to BLEU (forbidden / false)  
- Claiming product densify BLEU-4 ~83 as open-set MT

---

## 5. Definition of “we beat the competition” (accurate)

Pick a claim level:

| Claim level | Criteria | Distance now |
|-------------|----------|--------------|
| **L1 Product unique** | Offline FSOT + classical + catalog depth | **Met** |
| **L2 Chat competitive** | Mean chat sacre ≥45 open-set multi-lang | **Met** (~50) |
| **L3 News mid-parity** | WMT14 de-en sacre ≥40 | **~6 pts short** |
| **L4 News strong** | WMT14 de-en sacre ≥45–48 | **~11–14 pts short** |
| **L5 Broad DeepL-class** | Many pairs FLORES/WMT mid-40s+ | **Not started** (FLORES gated; multi-pair news unrun) |

**Accurate one-liner:**  
We **beat / own** unique offline+classical+law. We **match mid open-MT on chat**. We **do not yet beat** commercial systems on **news full-sentence fluency** — need roughly **+6 sacre** for mid-parity and **+14** for stretch SOTA on de→en.

---

## 6. Immediate execution plan (this push)

1. Implement **product hybrid router** + measure non-oracle (feature rules, not ref peeking)  
2. **WMT decode push**: higher beams, dual-system sentence-level ensemble upper bound  
3. Write measured gaps into `reports/COMPETITIVE_PUSH.md`  
4. Keep law pin D1D38A fixed  

Optional next session: WMT finetune loop under densify law wrap.

---

## 7. Measured this push (2026-07-22 competitive run)

| Track | Result | Notes |
|-------|-------:|-------|
| Product hybrid chat sacreBLEU | **40.64** | No ref peeking; densify-heavy (2800) + neural CJK (400) |
| WMT opus-mt beams=8 | **33.79** | Slightly under prior beams=5 33.88 |
| WMT NLLB-600M beams=8 | **33.49** | |
| **WMT oracle dual ensemble** | **37.61** | Best of opus/nllb per sentence (upper bound) |
| Gap ensemble → mid 40 | **2.39** | Was ~6.1 for single student |
| Gap ensemble → stretch 48 | **10.39** | Still needs finetune / larger model |

**Insight:** Beams alone do not close news. **Dual-student ensemble** recovers ~+3.7 sacre toward bar 40 without finetune. Remaining ~2.4 points need quality model upgrade or WMT finetune.

---

## 8. Beat levers run (2026-07-22)

| Lever | Result | Clears bar? |
|-------|-------:|:------------|
| L2 Neural-first hybrid chat | **48.74** sacre | **Yes** (≥45) |
| L1 Product NLL ensemble WMT | **34.54** | No (gap 5.46 to 40) |
| L1 Oracle ensemble upper | **37.13** | No (gap 2.87) |
| L3 Aggressive FT | 32.2 | No (regressed) |
| L3b Safe FT freeze-enc | 33.86 | No (flat) |
| Base opus-mt-de-en | 33.88 | No |

**Still required to beat news mid-parity (40):** better ensemble selection (~2.6 pts headroom to oracle), multi-epoch WMT FT with validation early-stop, or larger NLLB.

---

## 9. News push v3 (2026-07-22)

| System | sacreBLEU |
|--------|----------:|
| Product cross-NLL ensemble | **34.11** |
| Base opus | 33.88 |
| FT v3 test / best val | 33.41 / 35.76 |
| Oracle upper | 37.13 |
| Gap product → 40 | **5.89** |

Chat neural-first hybrid remains **48.74** (mid bar met).

