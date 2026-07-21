# Protofluid Language Translator (PFLT)

**Protofluid Language Translator** — a **universal translator intelligence** surface under **FSOT 2.1 law**.

It is **not** “dictionary BLEU only.” It is meant to:

1. **Translate** fluid language surfaces (historical → modern, multi-script)  
2. **Converse / relay** what was translated  
3. **Incorporate** claims into a growing **knowledge ledger**  
4. Ground every act in the FSOT seed scalar \(S = K(T_1+T_2+T_3)\) as the **factual base**

**Law authority:** archive-pinned `fsot_compute.py` (SHA256 `D1D38A…`) via `fsot_law_bridge.py`.  
**Not** an LLM as translation or truth core. Morph/lexicon is the **language surface**; FSOT is the **constitution**.

Architecture realignment vs Physical Archive: [`docs/FSOT_ARCHIVE_REALIGNMENT.md`](docs/FSOT_ARCHIVE_REALIGNMENT.md).  
North-star multi-metric goals (beat every bar): [`docs/NORTH_STAR_METRICS.md`](docs/NORTH_STAR_METRICS.md).  
**Law audit (no ad-hoc scalar):** [`docs/FSOT_LAW_AUDIT.md`](docs/FSOT_LAW_AUDIT.md).  
**Hugging Face:** [`docs/HUGGINGFACE.md`](docs/HUGGINGFACE.md) · model [dappalumbo91/pflt-fsot](https://huggingface.co/dappalumbo91/pflt-fsot) · dataset [pflt-fsot-sample](https://huggingface.co/datasets/dappalumbo91/pflt-fsot-sample).  
Fast climb: [`docs/FAST_CLIMB.md`](docs/FAST_CLIMB.md) · Accuracy dual-metric: [`docs/ACCURACY_PUSH.md`](docs/ACCURACY_PUSH.md).

### Shipping product: **Ada/SPARK** ([`pflt-Ada/`](pflt-Ada/))

Python is the **data factory** (export/climb). The binary product is Ada:

```powershell
cd pflt-Ada
python accuracy_push.py          # rebuild quality packs from local gold (large; optional)
python -u fast_climb.py --target 0.90
alr build
.\bin\pflt_main.exe eval-product # shipping inventory accuracy
.\bin\pflt_main.exe eval         # open-set morph stress
.\bin\pflt_main.exe converse "aqua lingua manus"
.\bin\pflt_main.exe archive      # live D1D38A pin of I:\ FSOT archive
```

| Track (Ada) | Meaning | Approx. (latest) |
|-------------|---------|------------------|
| **PRODUCT** | Full gold+densify+morph (shipping) | **~99.99%** form→gloss |
| **OPEN-SET** | Held-out morph (train_mass densify path) | **~99.99%** on catalog eval |
| **Catalog** | Language codes solidified (n≥200 thin set) | **113** (0 thin n&lt;50) |
| **Law pin** | Live SHA256 of archive `fsot_compute.py` | **D1D38A** (parity 0 absdiff) |
| **M6 sentence** | Offline Tatoeba BLEU-style climb | BLEU~2.4 · B1~44 (not neural parity) |

Large packs (`gold_core.tsv`, `train_mass.tsv`, `densify.tsv`) are **not** in git — rebuild with scripts. See `pflt-Ada/README.md`.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## Status

**Ada-primary product** with dual metrics (product inventory vs open-set morph). Python dual-track reports remain for the climb factory (`data/dual_track_report.json` when regenerated).

## Features

- **Converse + knowledge** — `protofluid_converse.py`: pathway → translate → law scalar → archive+ledger relay → append ledger  
- **Law bridge** — `fsot_law_bridge.py` pins Physical Archive `fsot_compute` (D1D38A)  
- **Knowledge ledger** — `knowledge_ledger.py` append-only claims (domain + S + authority)  
- **Archive memory** — `fsot_archive_memory.py` loads linguistics_derivations, linguistic targets, kb_portable inventory  
- **Pathway reasoner** — `pathway_reasoner.py` multi-hop attention over FSOT domain graph (Realities OS style)  
- **Teach panel** — `teach_panel.py` English-meta Latin/Greek form↔gloss (e.g. water ↔ aqua)  
- **Observer densify** — `observer_densify.py` rate-limited thin-knowledge plans + ledger densify claims  
- **Certified math** — `certified_math.py` numeric gate via D1D38A pin / archive anchors (refuse vibes math)  
- **Ledger hygiene** — `ledger_hygiene.py` cleans legacy `flowing_*` for display  
- **FSOT 2.1 domain routing** — 400+ scientific / historical domains  
- **Language surface** — reverse morph, paradigms, multi-gloss banks, per-lang JSON tables (`data/lang_tables/`)  
- **Name track** — gazetteer + optional Pleiades (entities ≠ morph metrics)  
- **Audio / vision stubs** — IPA + waveforms; multilayer vision scaffolding  
- **Math microscope** — Mathematica + Lean/Coq/Isabelle/F* golden parity (`formal/`)

## Requirements

- Python 3.11+
- Windows recommended for SAPI waveforms (formant WAV works offline anywhere)
- Optional local assets on a data drive (Dictionary SQLite, Pleiades CSVs, FSOT linguistics)

```bash
pip install -r requirements.txt   # currently stdlib-heavy; empty/minimal deps
```

## Quick start

```bash
# Stage smoke (when data present)
python run_stage_test.py

# Dual-track honest eval (core vs name)
python dual_track_eval.py

# Ingest ALL local language + hieroglyph sources → expanded gold
python ingest_all_language_data.py

# Autonomous local climb (chew until partial target — no cloud APIs)
python chew_climb.py --target 0.70 --max-rounds 120 --sample 2500 --full-every 4 --resume
python chew_climb.py --status
# PowerShell: .\chew_climb.ps1 -Target 0.70 -MaxRounds 120 -Resume -Background


# Mine desktop Dictionary + Rosetta (paths in mine_desktop_assets.py)
python mine_desktop_assets.py

# Pleiades ancient places → gazetteer contacts
python ingest_pleiades.py

# Waveform demo
python audio_articulation.py

# Law status (archive pin)
python fsot_law_bridge.py

# Protofluid converse (translate + relay + knowledge ledger)
python protofluid_converse.py "aqua lingua manus"
python protofluid_converse.py --repl
python protofluid_converse.py --status

# Translate-only API (language surface)
python -c "from PFLT_FSOT_2_1_aligned import PFLT; p=PFLT(); print(p.translate('aqua lingua', context='historical'))"

# Morph subsystem eval (not the full product success definition)
python dual_track_eval.py
python climb_open_set.py

# Math microscope + formal golden
python fsot_math_microscope.py
python formal/run_formal_asserts.py
```

### Example — converse (product surface)

```python
from protofluid_converse import ProtofluidTranslator

pt = ProtofluidTranslator()
print(pt.status())  # law pin + ledger
r = pt.converse("aqua lingua et manus")
print(r["reply"])           # relay under FSOT domain + S
print(r["fsot_law"])        # archive-backed scalar panel
print(r["claim_ids"])       # stored in data/knowledge_ledger.jsonl
r2 = pt.converse("what about water and hand?")  # retrieves ledger
print(r2["reply"])
```

### Example — translate surface only

```python
from PFLT_FSOT_2_1_aligned import PFLT

p = PFLT(enable_gapfill=True)
print(p.translate("aqua", context="historical", include_audio=True))
print(p.translate("Κύπρος", context="mythological"))
```

See `docs/FSOT_ARCHIVE_REALIGNMENT.md` and `formal/README.md`.

## Repository layout

```
PFLT_FSOT_2_1_aligned.py   # core engine
open_set_boost.py          # morphology / n-gram / Rosetta open-set
reverse_morph.py           # lemma reattachment
paradigm_expand.py         # finite inflection tables
name_gazetteer.py          # proper names + historical contacts
ingest_pleiades.py         # Pleiades CSV → contacts
dual_track_eval.py         # core vs name scoreboard
held_out_classical.py      # honest holdout scorer
waveform_synth.py          # SAPI / formant WAV
data/                      # small reports + seed indices (large gold gitignored)
```

Large gold/gazetteer files are **gitignored** and rebuilt with mine/ingest scripts or stored on your training drive (default under `D:\training data\pflt_linguistics\` in local configs).

## Data policy

- **In-repo:** small reports, Rosetta form index samples, domain catalogs that fit GitHub.
- **Local / Drive:** Dictionary DB, full gold JSONL, full name gazetteer, Pleiades CSVs, waveforms.
- Adjust absolute paths in `mine_desktop_assets.py`, `ingest_pleiades.py`, and related modules for your machine.

## License

Copyright 2026 Damian and contributors.

Licensed under the **Apache License, Version 2.0** — see [LICENSE](LICENSE).

## Versioning

- **v0.1.0** — first public baseline: dual-track eval, FSOT domains, waveforms, Pleiades contacts path.
- Tags: `v0.1.0`, branch `main`.

## Roadmap

1. Raise **core** open-set well above ~20% (paradigms, Latin-safe morph, better gloss quality).
2. Grow **name open** contacts (Pleiades language filter, classical seed graph).
3. Optional Pleiades-only classical language subset (la/grc) to cut modern noise.
4. Vision student training against multilayer stacks.

## Citation / concept

Proto-Fluid / FSOT 2.1 alignment notes live in project PDFs and chat history on the author’s machine; this repo is the **executable reference**.
