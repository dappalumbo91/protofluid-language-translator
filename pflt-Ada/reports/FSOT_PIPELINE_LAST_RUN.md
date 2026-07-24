# FSOT automated pipeline — last run

**UTC:** 2026-07-24T00:38:08.356742+00:00
**OK:** True
**Methodology:** [`docs/FSOT_INTRINSIC_METHODOLOGY.md`](../../docs/FSOT_INTRINSIC_METHODOLOGY.md)
**Pin OK:** True

## Product lock

- **Name:** `FSOT_C_ac_S`
- **sacreBLEU:** **36.9**
- **Beats student gen:** True
- **Gap → DeepL mid-40:** 3.1
- **Gap → student:** -0.11

## Steps

- verify_pin ok=True
- fsot_seed_push skipped
- product_lock FSOT_C_ac_S sacre=36.9
- metrics_snapshot updated (release/hf/kaggle packs)

## Reproduce

```powershell
cd C:\Users\damia\Desktop\pflt
python -u scripts\fsot_automate_pipeline.py --update-metrics
```

Do **not** git push / HF / Kaggle from this script (public publish is manual).
