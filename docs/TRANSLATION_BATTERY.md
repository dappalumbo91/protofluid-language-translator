# Translation accuracy & fluency battery

**Built:** 2026-07-23T13:32:37.967748+00:00  
**Elapsed:** 52.71s  
**Queries scored (all tracks):** ~9802  
**Law:** FSOT pin D1D38A · no NMT  

## Headlines

| Track | Exact % | Soft/Partial % | Mean fluency (0–1) |
|-------|--------:|---------------:|-------------------:|
| Sense curated single (n=84) | **100.0** | **100.0** | 1.0 |
| Sense curated phrases (n=25) | 100.0 | **100.0** | **1.0** |
| Sense held-out 2k (thin graph) | 0.0 | 0.05 | 0.4503 |
| Densify curated (Ada packs) | 72.62 | **77.38** | 0.9935 |
| **Densify held-out 3k (Ada packs)** | **46.83** | **55.03** | **0.8871** |
| Densify form_sense 1.5k | 1.4 | **19.93** | 0.9476 |
| PFLT curated single (seed lex) | **100.0** | **100.0** | 1.0 |
| PFLT curated phrases | 100.0 | **100.0** | **1.0** |
| PFLT held-out seed-only (no densify) | 0.55 | 2.4 | 0.513 |
| **Ada OPEN-SET binary (8k)** | 97.55 | **97.71** | — |
| **Ada PRODUCT binary (8k)** | 89.51 | **89.83** | — |

## Protocol

- **Exact:** normalized gold English gloss equality  
- **Soft:** gold in pred / token recall / stem-4 / phrase coverage  
- **Fluency:** heuristic 0–1 (penalize `unresolved`, garbage shells, non-alpha dumps)  
- **Densify track:** Ada `densify.tsv` + `gold_core.tsv` form→gloss index (shipping inventory)  
- **Not primary:** sacreBLEU / NMT paraphrase  

## Interpretation

1. **Curated core + phrases** — meaning identity (*aqua*≡*water*) and multi-token fluency.  
2. **Densify held-out** — fair inventory accuracy (same packs as Ada product).  
3. **Sense held-out low** — sense graph is intentionally sparse (expand by binding, not NMT).  
4. **PFLT seed-only held-out low** — expected without loading densify packs.  
5. **Ada binary eval** remains the shipping morph/product bar.

## Sample misses

### Sense curated
```json
[]
```

### Densify held-out
```json
[
  {
    "form": "کَرتے ہیں",
    "gold": "do",
    "pred": "unresolved",
    "fluency": 0.45,
    "hit": false
  },
  {
    "form": "notasen",
    "gold": "note (make a written record of and/or purposeful",
    "pred": "(reflexive) to show",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "horripilares",
    "gold": "horrify",
    "pred": "second-person singular preterite indicative of h",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "będzie lubiło",
    "gold": "like (to have positive emotions for",
    "pred": "like (to get pleasure from)",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "burlándote",
    "gold": "outwit",
    "pred": "circumvent",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "પતંગિયાંએ",
    "gold": "butterfly",
    "pred": "unresolved",
    "fluency": 0.45,
    "hit": false
  },
  {
    "form": "kʰännʌn",
    "gold": "eat",
    "pred": "unresolved",
    "fluency": 0.45,
    "hit": false
  },
  {
    "form": "pl-decl-noun-m-in",
    "gold": "Urals",
    "pred": "crane (machinery)",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "pantu",
    "gold": "verse",
    "pred": "unresolved",
    "fluency": 0.45,
    "hit": false
  },
  {
    "form": "pl-decl-noun-m-in",
    "gold": "Manchester (name of several towns and cities in ",
    "pred": "crane (machinery)",
    "fluency": 1.0,
    "hit": true
  },
  {
    "form": "sonariáu",
    "gold": "call (to name or refer to)",
    "pred": "unresolved",
    "fluency": 0.45,
    "hit": false
  },
  {
    "form": "食べぬ",
    "gold": "make a living",
    "pred": "eat or drink",
    "fluency": 1.0,
    "hit": true
  }
]
```

## Ada multi-token converse sample (shipping binary)

Query: `aqua lingua manus sol luna terra vita mors pater mater`

| Field | Value |
|-------|--------|
| map_rate | **1.0** (10/10 tokens mapped) |
| live_pin | true · D1D38A |
| S | ≈0.6513 |
| Surface gloss | water language hand (astronomy moon earth life annihilation father Primordial |

**Sense quality (not coverage):** densify maps all tokens, but polysemy can pick the wrong gloss:

| Token | Ideal | Observed |
|-------|--------|----------|
| aqua / lingua / manus | water / language / hand | ✓ |
| sol | sun | astronomy ✗ |
| luna / terra / vita / pater | moon / earth / life / father | ✓ |
| mors | death | annihilation ≈ soft |
| mater | mother | Primordial ✗ |

**Next accuracy lever:** domain-gated sense pick + `form_sense_prefer` (not more NMT).

## Reproduce

```powershell
cd C:\Users\damia\Desktop\pflt
python -u eval_translation_battery.py
cd pflt-Ada
.\bin\pflt_main.exe converse "aqua lingua manus sol luna terra vita mors pater mater"
```

JSON: `pflt-Ada/reports/TRANSLATION_BATTERY.json`  
Docs: `docs/TRANSLATION_BATTERY.md`
