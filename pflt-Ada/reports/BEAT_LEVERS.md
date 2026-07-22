# Beat-the-competition levers — measured

**Built:** 2026-07-22T13:18:23.675085+00:00
**Law:** S=K(T1+T2+T3) pin **D1D38A** (unchanged)

## L1 — Product dual-student ensemble (no ref peek)

| System | sacreBLEU |
|--------|----------:|
| opus-mt-de-en b5 | 33.88 |
| NLLB-600M b5 | 33.37 |
| **Product ensemble (NLL pick)** | **34.54** |
| Oracle uF1 ensemble (upper) | 37.13 |
| Picks | {'opus': 1751, 'nllb': 1252} |

## L3 — WMT finetune student (opus-mt-de-en)

| Metric | Value |
|--------|------:|
| steps | 2500 |
| train pairs | 60000 |
| avg loss last 100 | 2.1199 |
| **WMT test sacreBLEU** | **32.2** |
| chrF | 58.85 |
| path | `D:\training data\pflt_linguistics\13_huggingface\models\Helsinki-NLP__opus-mt-de-en-wmt-ft` |

## L2 — Neural-first hybrid chat

| Metric | Value |
|--------|------:|
| sacreBLEU | **48.74** |
| BLEU-4 | 51.38 |
| routes | {'neural': 2800, 'densify': 400} |
| gap to chat 45 | -3.74 |

## Gaps to beat commercial mid-bar

| Bar | Gap |
|-----|----:|
| Best single → 40 | 6.12 |
| Product ensemble → 40 | 5.46 |
| Finetuned → 40 | 7.8 |
| Best single → 48 | 14.12 |

**Mid-40 cleared?** False

## Next if still short of 40

1. Longer finetune / full WMT train epoch
2. Ensemble finetuned-opus + NLLB
3. Larger student (NLLB-1.3B) when disk allows

## L3b — Safer finetune (freeze encoder, lr=2e-5, 1500 steps)

| Metric | Value |
|--------|------:|
| WMT test sacreBLEU | **33.86** |
| vs base opus 33.88 | **-0.02** (flat / no win) |
| Aggressive FT v1 (full model 2500 steps) | **32.2** (regressed) |

**Finding:** Short domain FT of opus-mt-de-en does not cross 40. Need longer careful training, better data filter, or larger student.

## L2 win

Neural-first hybrid chat **48.74 sacre** (routes neural=2800 densify=400) — **past chat mid bar 45**.

