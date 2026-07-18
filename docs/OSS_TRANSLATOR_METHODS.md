# Open-source translator methods → FSOT-safe orientation

We study classical / historical OSS pipelines for **structure**, not to import free neural MT cores. PFLT stays **FSOT 2.1–aligned** (scalar teacher, zero free params on the scalar path).

## What successful classical tools do

| System / tradition | Approach | Transferable idea |
|--------------------|----------|-------------------|
| **Whitaker’s WORDS** | Exhaustive Latin **prefix + stem + ending** tables → lemma → English gloss | Finite analyze-then-gloss; never invent from embedding alone |
| **Morpheus / Perseus** | Greek/Latin morphological analysis → dictionary headword | Surface form ≠ meaning unit; lemma is the unit |
| **CLTK** | Pipeline: tokenize → normalize → POS/morph → lexicon | Stage separation; dual metrics (lex vs open) |
| **LEMLAT / Collatinus** | Rule morphology + large lemma lexicon | Precision over recall on short stems |
| **Historical linguistics pipelines** | Cognate tables, sound laws, Swadesh/ASJP | Lineage neighborhood under gates (we already have ASJP hooks) |
| **Gazetteers (Pleiades)** | Entity table + multilingual aliases | Names off the morph path (we split dual-track) |

## What we deliberately do *not* do

- LLM / NMT as the translation core  
- Soft generative “guessing” that breaks FSOT teacher gates  
- Mixing unique entities into morph open-set metrics  

## Applied in PFLT (v0.1 → now)

1. **Dual track** — core lexicon vs name gazetteer (Pleiades contacts)  
2. **Analyze-then-gloss** — reverse morph + paradigm expand + **prefix strip**  
3. **Lemma-first donors** — inject prefers content glosses for transfer  
4. **Precision gates** — short-stem collisions blocked unless high form similarity  

## Next increments

- Richer Latin/Greek **prefix inventories** (Whitaker-style)  
- Sense preference by FSOT domain context  
- Cognate bridges only when multi-source support exists  
