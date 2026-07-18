# Protofluid Language Translator (PFLT)

**FSOT 2.1–aligned** historical → modern language translation stack: morphology gap-fill, paradigm tables, dual-track **core lexicon** vs **proper-name gazetteer**, multilayer vision scaffolding, and IPA + waveform audio.

This repository is the working implementation of the *Proto-Fluid Language Translator* concept under **FSOT 2.1** (seed scalar \(S = K(T_1+T_2+T_3)\); zero free parameters in the teacher scalar path). It does **not** use an LLM as the translation core.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## Status (v0.1 baseline)

Honest dual-track open-set (see `data/dual_track_report.json` when regenerated locally):

| Track | Role | Typical partial (90/10) |
|--------|------|-------------------------|
| **Core** | Common vocabulary (morph / paradigms / gap-fill) | ~16–22% by language |
| **Name open** | Train-only gazetteer + classical seeds | ~17% |
| **Name + Pleiades** | + ancient-place contacts | ~18% |
| **Name deployed** | Full Dictionary + Pleiades gaz | ~79% |
| **Train closed** | Injected train forms | ~98% |

Open-set is still early; this tag freezes a **working multimodal stack** for versioning while we keep pushing accuracy.

## Features

- **FSOT 2.1 domain routing** — 400+ scientific / historical domains (`build_fsot_domain_catalog.py`)
- **Core open-set** — reverse morphology, precision-gated boosters, finite Latin/Greek/OE paradigms
- **Name track** — `name_gazetteer.py` + historical contacts; optional **Pleiades** ingest
- **Audio** — IPA + articulatory features + WAV (Windows SAPI or formant fallback)
- **Vision scaffolding** — multilayer gray + VIS + UV/NIR field student stubs
- **Hieroglyph / genetic code** hooks — Unikemet gold path, 64-codon symbols
- **Dual-track eval** — never mix unique entities into morph metrics

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

# Mine desktop Dictionary + Rosetta (paths in mine_desktop_assets.py)
python mine_desktop_assets.py

# Pleiades ancient places → gazetteer contacts
python ingest_pleiades.py

# Waveform demo
python audio_articulation.py

# Translate (API)
python -c "from PFLT_FSOT_2_1_aligned import PFLT; p=PFLT(); print(p.translate('aqua lingua', context='historical'))"
```

### Example

```python
from PFLT_FSOT_2_1_aligned import PFLT

p = PFLT(enable_gapfill=True)
print(p.translate("aqua", context="historical", include_audio=True))
print(p.translate("Κύπρος", context="mythological"))
```

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
