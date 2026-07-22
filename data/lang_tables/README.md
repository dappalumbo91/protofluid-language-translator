# Per-language translation tables

These JSON files hold **keywords and lookup tables** for the translation layer
(form→sense, seeds, demonyms, soft-score clusters). Logic stays in Python;
data lives here so you can extend without growing a monolith.

## Layout

| File | Role |
|------|------|
| `_shared.json` | English **sense clusters** (soft partial) + **domain keywords** |
| `grc.json` | Greek form-sense, seeds, participles, demonyms |
| `la.json` | Latin seeds / ethnonym suffixes |
| `ang.json` | Old English seeds |
| `en.json` | English extras (extend as needed) |

## Schema (per language)

```json
{
  "lang": "grc",
  "form_sense_prefer": { "γνωμων": ["sundial", "gnomon"] },
  "seeds": [ { "form": "γνώμων", "gloss": "sundial" } ],
  "participle_stems": [ { "stem": "βιασμεν", "gloss": "forced" } ],
  "demonym_seeds": { "κρης": "cretan" },
  "ethnonym_suffixes": ["ίτης", "αῖος"]
}
```

## Load API

```python
from lang_tables import form_sense_prefer, gap_seeds, sense_clusters, load_lang, reload_all

load_lang("grc")           # one language pack
form_sense_prefer()        # merged form → senses
gap_seeds()                # (lang, form, gloss) for inject
sense_clusters()           # soft-score clusters
reload_all()               # after you edit JSON on disk
```

## Editing workflow

1. Add a miss fix to the right `*.json` (e.g. new seed or form_sense).
2. Call `reload_all()` or restart the process.
3. Re-run `python climb_open_set.py`.

Do **not** put FSOT scalar math or map_token control flow here — only tables.
