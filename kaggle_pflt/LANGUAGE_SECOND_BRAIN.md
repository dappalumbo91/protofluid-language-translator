# FSOT Language Second Brain

**Purpose:** **FSOT** connective graph of form ↔ sense ↔ language ↔ lineage for the universal translator — not a personal-notes app as runtime.

**Naming rule:** Anything that is *our product* is labeled **FSOT** first. Competitor systems keep their names (NLLB, OPUS, DeepL).

## Quick start

```powershell
cd C:\Users\damia\Desktop\pflt
python language_brain.py all          # build + hole map + climb + Obsidian vault
python language_brain.py query water
python language_brain.py holes --min-langs 20
python language_brain.py export-obsidian
```

## Layout

| Path | Role |
|------|------|
| `language_brain.py` | Build / query / climb / export CLI |
| `data/language_brain/nodes.jsonl` | Graph nodes (sense, form, language, claim, note) |
| `data/language_brain/edges.jsonl` | Edges (expresses, cognate, prefer, …) |
| `data/language_brain/modern_core_labels.json` | Curated modern multi-lang core senses |
| `data/language_brain/extra_bindings.jsonl` | Gold-climb form↔sense (quality-gated) |
| `data/language_brain/hole_map.json` | Core-sense × target-lang holes |
| `data/language_brain/vault/` | Optional Obsidian browse (`00_INDEX.md`) |
| `pflt-Ada/reports/LANGUAGE_BRAIN.md` | Latest status report |

## Sources ingested

- `sense_interlingua` seeds + universal labels  
- `modern_core_labels.json` (de/fr/es/…/zh/ja/hi/…)  
- `sense_prefer.tsv` + wrong-sense notes  
- ASJP lineage Tier-B proposals  
- Knowledge ledger claims  
- `expanded_gold.jsonl` (lang-tagged classical/historical)  
- Catalog gold_by_lang from coverage report  

## Mission fit

Largest error margin for **universal meaning** was thin sense coverage.  
The brain makes holes **visible and fillable** without multi-hour NMT.

Law pin **D1D38A** is external — the brain densifies **knowledge**, never rewrites \(K,T_i\).

### Breadth (do not undercount)

| Track | Count | Meaning |
|-------|------:|---------|
| **Solidify catalog** | **113** | Form→gloss inventory ≥95% open (competitive breadth we already have) |
| Gold-core historical | ~20 | Classical densify slice only — **not** total languages |
| Sense modern core | mean ~46 langs / sense | Meaning hubs across modern + classical codes |

### FSOT mathematical pathways

Edges/nodes cite the pinned formula:

\[
S = K(T_1+T_2+T_3)
\]

- Law note node: live pin + linguistic panel \(S \approx 0.6513\)  
- Domain families (universe, earth_weather, cellular, mind_language, matter_energy) couple under shared law  
- Every catalog language → `domain:linguistic` via `fsot_pathway`  
- Every sense hub → `certified_under` law  

This is how systems **connect mathematically** — not free graph vibes.

### Fluency competitive frame (WMT de→en)

| Layer | sacre | What it is |
|-------|------:|------------|
| Product (= gen_score) | **36.79** | What we ship ≈ NLLB-3.3B class |
| DeepL mid bar | ~40 | External competitor (~3.2 gap) |
| **Oracle** | **46.12** | Best hyp **already in our pool** — internal ceiling, **not** DeepL |

We are **at** gen_score (by definition of product).  
We are **~9 points under oracle** — almost all **selection**.  
Oracle is the pool upper bound we are climbing toward by picking better; it is not a third-party MT brand.

## Open vault in Obsidian

1. Open folder `data/language_brain/vault` as a vault  
2. Start at `00_INDEX.md`  
3. Follow `[[water]]` / language notes  
