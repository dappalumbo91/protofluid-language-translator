# Gap fill — thin languages closed (pre-Hugging Face)

**Built:** after `fill_thin_langs.py` + `push_universal.py`  
**Gate:** no language with n&lt;50; all n≥20 langs ≥95% open/product

## Before → after

| Code | Before n | After n | Open% | Product% |
|------|--------:|--------:|------:|---------:|
| hit | 3 | **200** | 100 | 100 |
| pal | 10 | **200** | 100 | 100 |
| pro | 17 | **200** | 100 | 100 |
| mga | 25 | **200** | 100 | 100 |
| osp | 34 | **200** | 100 | 100 |
| orv | 36 | **200** | 100 | 100 |
| roa-opt | 47 | **200** | 99 | 99 |
| uga (border) | 96 | **200** | 100 | 100 |

## Catalog solidify bar

| Metric | Value |
|--------|------:|
| Language codes | **113** |
| Eval rows | **159324** |
| Thin n&lt;50 | **0** |
| Border 50–99 | **0** |
| OPEN overall | **99.99%** |
| PRODUCT overall | **99.99%** |
| Weak (n≥20 &lt;95%) | **none** |
| Ready for HF packaging (solidify gate) | **yes** |

## Sources

- Kaikki (D: only): Old Spanish, Old East Slavic, Middle Irish, Old Occitan, Ugaritic  
- Local mine: Hittite, Pahlavi/Middle Persian, Old Galician-Portuguese (Kaikki 404 on hyphen stem)  
- Dumps never pushed to GitHub  

## Still later (not blocking solidify)

- M6 sentence BLEU climb (CJK / word order)  
- Real U-Net weights in vision student slot  
- Catalog toward 200 for NLLB-class breadth  
- Multi-sense voting system-wide (demo seeds already injected)

## Commands

```powershell
cd pflt-Ada
python fill_thin_langs.py
python push_universal.py
python inject_converse_seeds.py
python verify_solid_gaps.py
```
