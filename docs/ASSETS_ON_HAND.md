# Assets on hand for sentence-fluency push

**Updated:** 2026-07-21  
**Law:** \(S=K(T_1+T_2+T_3)\) pin **D1D38A** — teachers densify only.

## Downloaded (game drive D:)

Root: `D:\training data\pflt_linguistics\13_huggingface\models\`

| Model | Size (approx) | Role |
|-------|---------------|------|
| `facebook/nllb-200-distilled-600M` | **~2.5 GB** | Broad multilingual teacher + SPM for CJK |
| `Helsinki-NLP/opus-mt-es-en` | ~0.6 GB | ES→EN teacher |
| `Helsinki-NLP/opus-mt-de-en` | ~1.1 GB | DE→EN |
| `Helsinki-NLP/opus-mt-fr-en` | ~1.2 GB | FR→EN |
| `Helsinki-NLP/opus-mt-ru-en` | ~1.2 GB | RU→EN |
| `Helsinki-NLP/opus-mt-zh-en` | ~1.2 GB | ZH→EN |
| `Helsinki-NLP/opus-mt-ja-en` | ~0.6 GB | JA→EN |
| `Helsinki-NLP/opus-mt-ar-en` | ~1.2 GB | AR→EN |
| `Helsinki-NLP/opus-mt-mul-en` | ~0.6 GB | Multi→EN fallback |

Also: OPUS Books + WMT14 via HF datasets cache under `13_huggingface\`.  
Tatoeba parallel: `D:\...\03_parallel_corpora\tatoeba\`.  
Archive linguistics priors: `pflt-Ada/data/archive_linguistics\`.

## Still blocked (you must act once)

| Asset | Status | Action |
|-------|--------|--------|
| **FLORES-200** (`facebook/flores`) | **Gated 403** | Log in as `dappalumbo91` → https://huggingface.co/datasets/facebook/flores → **Accept** |

## Pipeline commands

```powershell
# Teacher densify (uses local models on D:)
cd pflt-Ada
python m6_teacher_densify.py

# Archive Zipf + dependency priors
python fsot_archive_fluency_push.py

# FSOT surface gap solve
python fsot_solve_fluency_gap.py
```

## Latest fluency (product densify path)

| Stage | BLEU-4 | BLEU-1 | U-F1 | chrF |
|-------|-------:|-------:|-----:|-----:|
| Pre-FSOT gap | ~2.2 | ~46 | ~35 | ~25 |
| FSOT gap solve | ~6 | ~69 | ~53 | ~40 |
| Archive Zipf+dep | **~27** | **~89** | **~81** | **~65** |
| + teacher (mixed) | ~19–27 | ~87–89 | ~78–81 | ~61–65 |

Law panel S remains **0.651324761885** throughout.

## Not on GitHub

Model weights and multi-GB densify packs stay on **D:** / local only.
