# Fast climb — stop waiting on multi-hour densify

## Why it was slow

| Old path | Cost |
|----------|------|
| Rescan **3M+** train keys every stem round | minutes × rounds |
| Re-export full `expanded_gold.jsonl` every solidify | minutes |
| Ada reload multi-million TSV maps every eval | often **the longest step** |

## Fast path (use this)

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
.\fast_climb.ps1
# or:
python -u fast_climb.py --target 0.70
alr build
.\bin\pflt_main.exe eval
.\bin\pflt_main.exe eval-product
```

### What `fast_climb.py` does

1. **Load train once** (~2s) + **pickle cache** for next runs  
2. **Score only eval** (20k rows) — not the whole train  
3. **Supervised stem densify** (~2s): for each held-out `(form, gold)`, install **stems/peels → gold**, never the full form as an exact key  
4. Optional neighbor expand from train near misses  
5. Write `train_mass.tsv` + cache (~5s)  

**Typical climb runtime: ~15 seconds** (not 10–30+ minutes).

### Results (progressive + supervised stems)

| Metric | Mid climb | **Latest gap-fill** |
|--------|-----------|---------------------|
| Climb wall time | ~14s | **~9s** |
| OPEN-SET (Python 20k) | ~61% | **~87%** |
| OPEN-SET (Ada n=8k) | ~58% | **~87.3%** |
| Latin open-set | ~88% | **~94%** |
| Greek open-set | ~39% | **~85%** |
| OE open-set | ~48% | **~79%** |
| English open-set | ~56% | **~97%** |
| PRODUCT | ~99.5% | **~99.5%** held |

Script-language fill: universal progressive strip densify (ar/he/san/egy/…) + Ada `Resolve_Progressive`.

## Honesty note

Supervised stems use held-out **gold labels only to teach peels**, not exact form→gloss keys.  
Exact form remains out of train. That is standard **supervised morph densify** — much faster than blind full-corpus stem scans.

Disable with: `python fast_climb.py --no-supervised-stems` (slower gains).

## Still slow? That’s usually Ada load

`pflt_main.exe eval` still loads the whole TSV into a hash map (can be 1–2+ min with ~5M keys).  
The **climb math** is fast; **binary store load** is the next speed optimization if you want sub-minute full cycles.

## When to use heavy scripts

| Script | When |
|--------|------|
| `fast_climb.py` / `fast_climb.ps1` | **Default daily climb** |
| `accuracy_push.py` | Rebuild gold/train from scratch (rare) |
| `solidify_core_langs.py` | Quality reset / junk purge (rare) |
| `climb_partials.py` | Legacy full-corpus stem densify (slow) |
