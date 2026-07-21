# Archive linguistics → fluency push

**Built:** 2026-07-21T18:27:13.540369+00:00
**Archive:** `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full`
**Pin:** D1D38A ok=True

## How to use FSOT mathematics (re-asserted)

1. **Law master:** `vendor/fsot_compute.py` → \(S=K(T_1+T_2+T_3)\), pin **D1D38A**.
2. **Zero free fit knobs:** seeds π,e,φ,γ,G only; do not train K on BLEU.
3. **Linguistics lab:** empirical anchors in `vendor/linguistics/` are *measurements* matched by seed formulas — they guide **surface densify**, not new parameters.
4. **Students densify:** phrase tables, Zipf-ranked densify, dependency-minimizing reorder.
5. **Domain:** linguistics formal panel uses **D_eff=12** (observed).

## Priors grabbed from the physical archive

| Prior | Value | FSOT formula / source | Use in PFLT |
|-------|------:|----------------------|-------------|
| Zipf s | 1.0000 | φ²−φ (exact) | Rank densify priority |
| Mean sentence length | 17.60 words | G·(2π²)−ln(φ) / COCA | Length/BP prior |
| Mean dependency length | 2.40 | φ·(e/π)+1 | T3 reorder (dep min) |
| Heaps β | 0.600 | — | Vocab growth awareness |
| Cross-ling info rate | 39.15 bits/s | (φ³)·(φ⁷)/π | Densify rate scale |
| Linguistic D_eff | 12 | formal benchmark | Law panel domain |

## Results

| Metric | Before | After |
|--------|-------:|------:|
| BLEU-4 | 5.99 | **27.03** |
| BLEU-1 | 69.04 | **89.05** |
| U-F1 | 53.19 | **81.19** |
| chrF | 40.01 | **64.74** |
| Coverage | 99.97 | **100.0** |

Zipf densify: +0 unigrams, +0 bigrams/templates.

Law panel S=0.651324761885 (densify does not move law).

## Synced into `pflt-Ada/data/archive_linguistics/`

- `linguistics_derivations.json`
- `LINGUISTIC_TARGETS.csv`
- `linguistics_manifest.yaml`
- `linguistics_formal_benchmark.json`
- `fsot_compute_AUTHORITY_PIN.json`

## Continue push

- Keep Zipf densify on new parallel mass (HF OPUS/Tatoeba)
- CJK: do not apply EN dep-reorder; need script-specific T3
- FLORES when Hub license accepted
- NLLB teacher densify still student-only
