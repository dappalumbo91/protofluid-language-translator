# Using the FSOT Physical Archive for PFLT

**Master:** `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full` (I: definitive; GitHub is sync-from-I)

## Always

```text
Law:     vendor/fsot_compute.py  pin D1D38A
Scalar:  S = K*(T1+T2+T3)  from seeds only
Domain:  linguistic D_eff=12, observed=true for converse
Students: densify/morph/phrase — never rewrite law
```

## Grab for translation fluency

| Archive path | Use |
|--------------|-----|
| `vendor/fsot_compute.py` | Authority pin + compute_scalar |
| `vendor/linguistics/linguistics_derivations.json` | Zipf, dep length, sentence length |
| `vendor/linguistics/data/LINGUISTIC_TARGETS.csv` | Empirical gates |
| `data/linguistics_formal_benchmark.json` | D_eff=12 panel culture |
| `FSOT/Scalar.lean` | Formal T1/T2/T3 structure |
| `docs/PRACTICAL_PIPELINE.md` | Offline validation → application |

## Commands

```powershell
cd pflt-Ada
python fsot_archive_fluency_push.py
python fsot_solve_fluency_gap.py
```
