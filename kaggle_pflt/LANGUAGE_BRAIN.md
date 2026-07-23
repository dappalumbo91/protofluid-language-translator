# FSOT Language Second Brain

**Built:** 2026-07-23T19:00:13.393159+00:00
**Nodes:** 7906 · **Edges:** 23193
**By kind:** `{'sense': 296, 'form': 7378, 'language': 126, 'note': 80, 'claim': 26}`
**Law:** S=K(T1+T2+T3) pin D1D38A · S_ling=0.6513247618848969

## Mission

**FSOT** connective graph of form↔sense↔language↔lineage for the universal translator.
Obsidian vault (optional browse): `data/language_brain/vault/`.
Naming: **FSOT_*** = ours · NLLB/DeepL/OPUS = competitor students/bars.

## Hole map (core senses × target langs)

- Senses scored: **61**
- Under min_langs: **0**
- Mean langs bound: **46.0**

| Gloss | Langs bound | Missing (sample) |
|-------|------------:|------------------|
| cell | 25 | `ang`, `egy`, `akk`, `san`, `got`, `non` |
| big | 36 | `ang`, `egy`, `akk`, `san`, `got` |
| path | 34 | `egy`, `akk`, `san`, `got`, `non` |
| hot | 38 | `egy`, `akk`, `san`, `got` |
| language | 36 | `egy`, `akk`, `san`, `got` |
| friend | 49 | `he`, `egy`, `akk` |
| meat | 35 | `he`, `egy`, `akk` |
| people | 39 | `egy`, `akk`, `non` |
| sky | 42 | `egy`, `got`, `non` |
| soul | 37 | `egy`, `akk`, `san` |
| year | 44 | `he`, `san`, `non` |
| bad | 42 | `egy`, `akk` |
| cat | 41 | `he`, `got` |
| child | 42 | `he`, `akk` |
| cold | 43 | `egy`, `akk` |
| dark | 38 | `egy`, `akk` |
| enemy | 45 | `akk`, `san` |
| foot | 47 | `ar`, `non` |
| mind | 37 | `egy`, `akk` |
| moon | 46 | `egy`, `got` |

## CLI

```powershell
python language_brain.py build
python language_brain.py holes
python language_brain.py query water
python language_brain.py climb
python language_brain.py export-obsidian
```

## Breadth (do not undercount)

- **Solidify catalog:** **113** codes (all ≥95 open: True, overall 99.99)
- Gold-core historical slice: **20** codes (different track)
- FSOT law S (linguistic): **0.6513247618848969** · pin D1D38A
- FSOT lang pathways: **126**

## Competitive frame (news de→en, honest)

| Layer | sacre | Meaning |
|-------|------:|---------|
| Product = gen_score_nllb33 | **36.79** | What we ship (≈ NLLB-3.3B class) |
| DeepL-class mid bar | ~40 | External fluency competitor (~3.2 gap) |
| **Oracle (pool upper bound)** | **46.12** | Best hyp *already in our pool* — not DeepL |

Oracle is **not** an external product. It is the ceiling of candidates we already generated.
Gap product→oracle ≈ **9.3** sacre is almost all **selection**. Gap product→mid-40 ≈ **3.2**.

## Next levers

1. **Selection toward oracle** (hard indices) — largest fluency residual
2. Grow sense graph *across the 113 catalog* (not just core 61)
3. Classical/visual depth (unique band)
4. Hold solidify 113 ≥95; expand toward 200 when ready
