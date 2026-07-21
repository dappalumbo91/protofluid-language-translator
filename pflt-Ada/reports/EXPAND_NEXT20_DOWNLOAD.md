# Next 20 languages — download + ingest (game drive)

**Download root:** `D:\training data\pflt_linguistics\12_kaikki_downloads`
**Built:** 2026-07-21T15:02:11.138148+00:00
**Catalog size now:** 52

## Downloads (Kaikki / Wiktionary)

| Code | Name | Kind | OK | Rows | Size path |
|------|------|------|----|------|-----------|
| es | Spanish | modern | True | 150000 | 1013 MB |
| it | Italian | modern | True | 150001 | 761 MB |
| de | German | modern | True | 150002 | 1065 MB |
| fr | French | modern | True | 150004 | 571 MB |
| pt | Portuguese | modern | True | 150004 | 555 MB |
| ru | Russian | modern | True | 150000 | 936 MB |
| nl | Dutch | modern | True | 150004 | 247 MB |
| pl | Polish | modern | True | 150002 | 772 MB |
| sv | Swedish | modern | True | 150004 | 351 MB |
| tr | Turkish | modern | True | 150004 | 428 MB |
| ja | Japanese | modern | True | 150002 | 376 MB |
| ko | Korean | modern | True | 150000 | 195 MB |
| hi | Hindi | modern | True | 150002 | 159 MB |
| vi | Vietnamese | modern | True | 97180 | 78 MB |
| id | Indonesian | modern | True | 121064 | 63 MB |
| ca | Catalan | modern | True | 150004 | 222 MB |
| pi | Pali | ancient | True | 123326 | 35 MB |
| uga | Ugaritic | ancient | True | 2533 | 1 MB |
| akk | Akkadian | ancient | True | 12871 | 3 MB |
| egy | Egyptian | ancient | True | 67374 | 17 MB |

## Local historical codes mined


## Accuracy after merge + solidify

- OPEN-SET: **65.3%** partial (exact 63.3%, n=121792)

| Lang | New | Open partial | n |
|------|-----|--------------|---|
| ko | Y | 51.8% | 14646 |
| la |  | 98.6% | 10860 |
| pl | Y | 41.6% | 8037 |
| sv | Y | 46.6% | 6452 |
| ja | Y | 54.8% | 6342 |
| de | Y | 61.5% | 6002 |
| hi | Y | 55.6% | 5731 |
| ru | Y | 61.0% | 5564 |
| it | Y | 58.4% | 5428 |
| tr | Y | 73.6% | 5162 |
| es | Y | 56.6% | 5028 |
| pi | Y | 83.9% | 4765 |
| ca | Y | 64.3% | 4619 |
| fr | Y | 58.9% | 4566 |
| pt | Y | 62.4% | 4356 |
| nl | Y | 69.6% | 4305 |
| vi | Y | 62.7% | 4079 |
| id | Y | 67.5% | 3814 |
| grc |  | 100.0% | 3166 |
| egy | Y | 64.3% | 2044 |
| ang |  | 97.1% | 1989 |
| ar |  | 98.3% | 819 |
| got |  | 98.3% | 633 |
| akk | Y | 59.0% | 544 |
| he |  | 98.8% | 417 |
| san |  | 90.0% | 410 |
| non |  | 90.9% | 406 |
| fa |  | 94.2% | 240 |
| en |  | 98.7% | 228 |
| sga |  | 88.2% | 203 |
| cu |  | 95.5% | 200 |
| xcl |  | 100.0% | 175 |
| cop |  | 100.0% | 104 |
| arc |  | 88.8% | 98 |
| uga | Y | 88.5% | 96 |
| osx |  | 98.4% | 64 |
| roa-opt |  | 97.9% | 47 |
| orv |  | 100.0% | 36 |
| osp |  | 94.1% | 34 |
| mga |  | 100.0% | 25 |
| pro |  | 94.1% | 17 |
| peo |  | 100.0% | 15 |
| pal |  | 100.0% | 10 |

## Full catalog

`akk`, `ang`, `ar`, `arc`, `ca`, `cop`, `cu`, `de`, `egy`, `en`, `es`, `fa`, `fr`, `frm`, `fro`, `gmh`, `goh`, `got`, `grc`, `he`, `hi`, `hit`, `hy`, `id`, `it`, `ja`, `ko`, `la`, `mga`, `nl`, `non`, `orv`, `osp`, `osx`, `pal`, `peo`, `phn`, `pi`, `pl`, `pro`, `pt`, `roa-opt`, `ru`, `san`, `sga`, `sum`, `sv`, `syc`, `tr`, `uga`, `vi`, `xcl`

## Rebuild / climb

```powershell
cd pflt-Ada
python -u download_next20_languages.py   # re-download/ingest
python -u solidify_covered_95.py
alr build
.\bin\pflt_main.exe eval
.\bin\pflt_main.exe eval-product
```
