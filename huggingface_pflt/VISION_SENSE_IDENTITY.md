# Vision lock — Protofluid Language Translator

**Date:** 2026-07-23  
**Authority:** `I:\FSOT-Physical-Archive` · pin **D1D38A** · `vendor/fsot_compute.py`

---

## Product (one sentence)

**PFLT is a universal translator of meaning:** it turns FSOT-derived structure and **stable sense symbols** into language forms. Surface words are labels. A cat is a cat; water is water; a cell is a cell — whatever the spelling.

---

## What FSOT is (archive — not a slogan)

From `02_FSOT-2.1-Lean-Full`:

| Pillar | Content |
|--------|---------|
| Seeds | π, e, φ, γ, G_Catalan only — **no free fit knobs** |
| Engine | \(S = K(T_1+T_2+T_3)\) (mpmath authority; Lean formal) |
| Domains | 400+ routed scientific domains; linguistics is one domain |
| Epistemology | Truth = seed derivation + verification — **not** LLM fluency |
| Observer | May densify knowledge; **must never rewrite law** |

PFLT is the **language surface** of that constitution — not a BLEU contest against DeepL with borrowed NMT.

---

## Correct translation model

```
surface form  →  SENSE_id  →  surface form (target language)
     aqua     →  SENSE_water →  water / Wasser / eau / 水
```

- **Direct meaning** first (form↔sense bindings).  
- Where there is no 1:1 word, there is still a **direct sense** (role, relation, structure).  
- **Structure** (grammar / FSOT domain frame) composes senses; it does not invent referents.  
- Later: physics formulas → same machinery → **narrative** (symbols and relations, not vibes).

---

## What was wrong (2026-07 killshot drift)

| Drift | Cost |
|-------|------|
| Multi-hour NLLB beam + QLoRA “killshot” | **Wrong tool** — probabilistic paraphrase, not sense identity |
| Z-scoring NMT hyps with ad-hoc encoder N/P | **Wrong application** of \(S=K(T_1+T_2+T_3)\) |
| Optimizing WMT sacreBLEU as the product | Optimizes **fluency competitors**, not meaning fidelity |

That path is **off-mission**. It is not how FSOT math is meant to solve translation.

---

## Correct use of the math

| Layer | FSOT role |
|-------|-----------|
| Sense graph | Meaning atoms (data under law — densify, never rewrite \(K,T_i\)) |
| Domain route | Atlas \(D_{\mathrm{eff}}\), observed, phases from seed domain table |
| Each translate/converse act | **Certify** with pinned panel \(S,T_1,T_2,T_3\) (read-only) |
| Linguistics anchors | Zipf/entropy/… from `vendor/linguistics` — empirical bridges, not BLEU knobs |
| Gap densify | Observer-style: bind more form↔sense pairs offline |

**Not:** train a student model for six hours to move BLEU 0.1.  
**Yes:** bind `aqua`≡`water` once; resolve instantly forever under law pin.

---

## Fast path (must stay seconds)

```powershell
cd C:\Users\damia\Desktop\pflt
python pflt_sense_translate.py --smoke
python pflt_sense_translate.py "aqua manus lingua" --src la --tgt en
python pflt_sense_translate.py "water" --src en --tgt de
```

Module: `sense_interlingua.py` · CLI: `pflt_sense_translate.py`  
`map_token` in `PFLT_FSOT_2_1_aligned.py` prefers sense interlingua before fuzzy gapfill.

---

## Competitive bar (honest)

Competitors win on **fluent paraphrase**.  
PFLT must win on **absolute sense fidelity** across covered languages — and eventually on **physics → narrative** under the same sense/structure spine.

BLEU may be a secondary surface check. It is **not** the definition of success.

---

## Do / Don't

| Do | Don't |
|----|--------|
| Expand sense graph with explicit form↔sense | Free LLM invent glosses |
| Pin every numeric claim to D1D38A | Ad-hoc damping / free \(K\) |
| Densify catalog offline (chew_climb, observer) | Multi-hour NMT as product spine |
| Report unresolved honestly | Soft shells (`narrative_flow`) |

---

## Related

- Archive realignment: [`FSOT_ARCHIVE_REALIGNMENT.md`](FSOT_ARCHIVE_REALIGNMENT.md)  
- Law audit: [`FSOT_LAW_AUDIT.md`](FSOT_LAW_AUDIT.md)  
- Founding materials: `I:\FSOT-Physical-Archive\06_Founding-Archives\` · PFLT PDFs  
