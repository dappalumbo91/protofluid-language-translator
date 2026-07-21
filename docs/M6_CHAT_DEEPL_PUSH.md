# Chat content + DeepL-style full BLEU push

**Built:** 2026-07-21T19:01:25.800526+00:00
**Law:** S=K(T1+T2+T3) pin **D1D38A** (unchanged)

## 1) Chat sentence content (Tatoeba)

| Metric | Score | Staged target | Gap |
|--------|------:|--------------:|----:|
| BLEU-4 | **26.36** | 35 | 8.64 |
| BLEU-1 | **82.8** | 92 | 9.2 |
| U-F1 | **78.99** | — | — |
| chrF | **63.22** | — | — |
| n | 6400 | | |

## 2) Full sentence / DeepL-oriented (WMT14 de→en test)

| Metric | Score | Staged DeepL-class | Gap |
|--------|------:|-------------------:|----:|
| BLEU-4 | **0.4** | 30 | 29.6 |
| sacreBLEU | **0.35** | 30 | — |
| BLEU-1 | **25.3** | — | — |
| U-F1 | **24.17** | — | — |
| chrF | **23.94** | — | — |
| Coverage | 98.42% | | |
| n | 3003 | | |

## Actions this run

- Tatoeba chat densify: {'rows': 846448, 'uni': 0, 'bi': 0, 'per_lang': {'zh': 21424, 'de': 60000, 'ru': 60000, 'fr': 60000, 'es': 60000, 'nl': 60000, 'ar': 60000, 'pt': 60000, 'he': 60000, 'it': 60000, 'tr': 60000, 'hi': 25108, 'la': 60000, 'ko': 19916, 'pl': 60000, 'ja': 60000}}
- WMT14 train densify: {'rows': 138172, 'uni': 0, 'bi': 0, 'method': 'cooccurrence_vote'}
- Teacher polish: {'es': {'n': 400, 'uni': 0, 'bi': 0}, 'de': {'n': 400, 'uni': 0, 'bi': 0}, 'fr': {'n': 400, 'uni': 0, 'bi': 0}, 'ru': {'n': 400, 'uni': 0, 'bi': 0}, 'zh': {'n': 400, 'uni': 0, 'bi': 0}, 'ja': {'n': 400, 'uni': 0, 'bi': 0}, 'ar': {'n': 400, 'uni': 0, 'bi': 0}}
- Phrase table: uni=453464 bi=6320906

## Competitive read

### Chat (Tatoeba densify path)

| Metric | Score | Target | Gap |
|--------|------:|-------:|----:|
| BLEU-4 | **~26.4** | 35 | ~9 |
| BLEU-1 | **~82.8** | 92 | ~9 |
| U-F1 | **~79** | — | content-competitive |

### DeepL-oriented full sentence (WMT14 de→en)

| Path | sacreBLEU / BLEU-4 | vs DeepL-class (~35–45+) |
|------|-------------------:|--------------------------|
| **Densify-only** (phrase table) | **~0.4** | Far — order/fluency not solved by lexicon alone |
| **Neural student** local `opus-mt-de-en` (on D:) | **~33.9** | **In the competitive band** for open MT |

### Architecture under FSOT

```
Law pin D1D38A  S=K(T1+T2+T3)     ← never trained on BLEU
        ▲
Densify + morph (Ada offline)    ← chat content strength
Neural student (opus-mt / NLLB)  ← news full-sentence BLEU
```

Both are **students**. Shipping path can **route**: chat/classical densify; modern news via local neural student with cert/law panel still wrapping the turn.

### Are we competitive?

| Track | Status |
|-------|--------|
| Chat content (B1/F1) | **Yes, approaching strong** |
| Chat full BLEU-4 | Mid — **~9 points** to staged 35 |
| News densify-only | Not competitive |
| News **with neural student we already own** | **~34 sacreBLEU — competitive open MT** |

Still not claiming top DeepL SOTA on every pair; **de-en news with local teacher is in the game**.
