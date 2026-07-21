# Protofluid Language Translator — **Ada / SPARK** (primary product)

**Ada-primary path.** Python tree is a data factory (`export_data_for_ada.py`);  
this binary is the product: law + lexicon + morph + vision + audio + converse.

**Law master:** `I:\FSOT-Physical-Archive` (canonical `fsot_compute.py` pin **D1D38A**).

| Layer | Status (V6) |
|--------|-------------|
| FSOT law `S=K(T1+T2+T3)` | **Golden PASS** (archive-aligned) |
| Authority pin **D1D38A** | **Live SHA256** of I: `fsot_compute.py` |
| Domain atlas | **410** domains (`atlas`) |
| Linguistics anchors + cert | **60** anchors; `cert` gate in converse |
| densify + gold deploy | **~96k densify · ~1.02M gold · ~2.08M map** |
| train_mass (open-set) | **~1.02M** (+ paradigm expand) |
| Reverse morph + edit-sim | **Yes** |
| Vision + U-Net hyp file | **Yes** (`vision unet`) |
| Articulatory audio | **Yes** (`audio`) |
| LTM / mulling (SR-ITE-style) | **Yes** (`ltm recall`) |
| Pathway / teach / converse / ledger | **Yes** |
| Honest open-set eval | **`eval` → ~36% partial** (climbing to 70%+) |
| Self-climb inject | **`inject FORM GLOSS`** |
| GNATprove | law packages (level 2) |

## Commands

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
python export_data_for_ada.py
alr build
.\bin\pflt_main.exe eval
.\bin\pflt_main.exe converse "aqua lingua manus"
.\bin\pflt_main.exe inject aquarum water
.\bin\pflt_main.exe status
```

## Layout

```text
pflt-Ada/
  export_data_for_ada.py   # quality packs from ../data
  data/
    densify.tsv
    gold_core.tsv
    train_mass.tsv         # open-set train
    eval_sample.tsv        # held-out (no train keys)
  src/                     # law + store + morph + product surface
  bin/pflt_main.exe
```

## North star

Beat every translator-intelligence metric offline under FSOT law  
(see `../docs/NORTH_STAR_METRICS.md`, `../docs/ADA_REFINEMENTS.md`).

Priority order for Ada:

1. **M1** open-set form→gloss partial ≥70% then ≥85%  
2. **M5** classical/visual depth (la, grc, egy, hieroglyphs…)  
3. **M4** catalog breadth  
4. **M7–M9** law pin, converse/ledger, offline-first  
5. **M6** modern sentence quality only after M1 holds
