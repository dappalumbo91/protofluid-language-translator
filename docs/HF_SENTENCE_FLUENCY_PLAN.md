# Hugging Face → sentence fluency (Google/DeepL parity path)

**Goal:** Climb **M6 sentence fluency** toward Google / DeepL / NLLB class bars.  
**Constraint:** FSOT remains **law** (\(S=K(T_1+T_2+T_3)\), pin **D1D38A**). HF assets are **students / data / teachers**, not a replacement constitution.

## What Hugging Face gives us that we need

| HF asset | Role for PFLT | Why it matters for parity |
|----------|---------------|---------------------------|
| **FLORES-200** (eval) | Industry-style many→en test set | Same bar people cite vs NLLB/Google |
| **OPUS / Tatoeba / OpenSubtitles** | Parallel mass for phrase + order models | Fuel for fluency without cloud API |
| **NLLB-200 distilled 600M** | Offline **teacher** (optional) | Generate synthetic parallels / phrase densify; student never rewrites law |
| **Helsinki-NLP opus-mt-*** | Pair-specific teachers (es-en, de-en, …) | Smaller than NLLB; EU fluency climb |
| **M2M100 / mBART** | Multilingual seq2seq students | Later: distill into Ada pathway or local runtime |
| **SentencePiece tokenizers** | CJK / unsegmented scripts | Fixes ja/zh weak spots |
| **`evaluate` / sacrebleu / COMET** | Comparable scores | Honest head-to-head reporting |
| **Our Hub pack** `dappalumbo91/pflt-fsot` | Publish metrics + sample densify | Visibility; not the training mass |

## Architecture (students under law)

```
                    ┌─────────────────────────────┐
                    │  FSOT law pin D1D38A          │
                    │  S = K(T1+T2+T3)              │
                    │  Ada converse / cert / panel │
                    └──────────────▲────────────────┘
                                   │ densify only
         ┌─────────────────────────┴──────────────────────────┐
         │  Surface fluency stack (students)                  │
         │  • densify lexicon + peels                         │
         │  • Tatoeba/OPUS/FLORES phrase + order tables       │
         │  • HF teacher (NLLB/Marian) → synthetic densify    │
         │  • optional neural decode student (later)          │
         └────────────────────────────────────────────────────┘
                                   ▲
                    Hugging Face Hub: data + models
```

**Hard rule:** Teacher MT may **propose** glosses/phrase rows. Product densify may accept them. **K, T1–T3, pin** never trained on BLEU.

## Climb stages

| Stage | Action | Success signal |
|-------|--------|----------------|
| **S1** | FLORES many→en eval (held-out) + sacrebleu | Published FLORES BLEU/chrF |
| **S2** | 50k–100k parallel / lang phrase+bigram (Tatoeba+OPUS) | BLEU-1 / U-F1 jump |
| **S3** | CJK SentencePiece / char-n-gram densify | ja/zh BLEU leave floor |
| **S4** | NLLB/Marian teacher densify (offline batch) | Phrase mass quality ↑ |
| **S5** | Optional local NLLB-600M or distilled student in pathway | Approach neural bars on EU pairs |
| **S6** | COMET / human spot-check | Honest parity report |

## Storage policy

- HF cache / downloads → `D:\training data\pflt_linguistics\13_huggingface\`  
- Full models **not** on GitHub  
- Hub model card only: sample densify + metrics  

## Competitor honesty

Google/DeepL train massive neural MT + re-ranking.  
We climb the **same eval sets** (FLORES, Tatoeba) while keeping **FSOT uniqueness**. Parity is measured, not claimed early.
