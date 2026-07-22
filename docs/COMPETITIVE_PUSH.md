# Competitive push — measured

**Built:** 2026-07-22T12:21:35.589705+00:00
**Law pin:** D1D38A

## Where we stand after this push

### Product hybrid chat (no ref peeking)

| Metric | Value |
|--------|------:|
| sacreBLEU | **40.64** |
| BLEU-4 | **76.2** |
| BLEU-1 | **90.72** |
| chrF | **74.46** |
| Routes | densify=2800 neural=400 |
| Gap to chat mid bar 45 | 4.36 |

### WMT14 de→en news

| System | sacreBLEU |
|--------|----------:|
| opus-mt-de-en_b8 | **33.79** |
| nllb-600M_b8 | **33.49** |
| oracle_ensemble | **37.61** |
| **Best** | **37.61** (oracle_ensemble) |
| Gap to mid 40 | **2.39** |
| Gap to stretch 48 | **10.39** |

## Accurate competitive read

| Arena | Status |
|-------|--------|
| A Catalog / classical / FSOT | **Winning unique** |
| B1 Chat open-set product hybrid | **Climbing** |
| B2 News mid-parity (≥40) | **Short by 2.39 sacre** |
| B2 News stretch SOTA (≥48) | **Short by 10.39 sacre** |

## Left to beat commercial MT on news

1. Finetune student on WMT train (largest expected gain toward +6)
2. Optional larger NLLB / more pairs
3. FLORES multi-pair public bar when unlocked
4. Keep hybrid router as product default

See also: `docs/COMPETITIVE_ROADMAP.md`
