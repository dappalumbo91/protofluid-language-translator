# Ada ↔ FSOT Physical Archive + sensory + gap-fill (V6)

**Archive master:** `I:\FSOT-Physical-Archive`  
**Product binary:** `pflt-Ada/bin/pflt_main.exe` (Ada-primary **V6**)

---

## Gaps filled (this pass)

| Gap | Implementation | CLI |
|-----|----------------|-----|
| **1. Full domain atlas (~400)** | `domain_atlas.tsv` (410 rows from catalog) + `PFLT_Atlas` keyword match → D_eff panel | `atlas "quantum photon"` |
| **2. Live SHA256 pin** | Pure Ada `PFLT_SHA256` hashes archive `fsot_compute.py` vs **D1D38A…** | `archive` → `live_hash_ok=TRUE` |
| **3. U-Net hypothesis slot** | Load TSV hyp file → Gardiner teacher (store/Unikemet); image path metadata | `vision unet` / `vision hyp PATH [image]` |
| **4. SR-ITE LTM / mulling** | Append-only `ltm_mulling.jsonl`; recall + densify mull notes | `ltm recall KEY` · auto on converse |
| **5. Certified math** | Law panel + refuse vibes S= | `cert "fsot scalar"` |
| **6. Linguistics anchors** | 60 archive derivations in TSV; zipf/entropy/… | `cert "zipf entropy"` · wired into converse |

---

## Archive binding (verified live)

```
live_hash_ok=TRUE
live_sha256=D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70
expected_sha256=D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70
note=LIVE pin OK: archive fsot_compute.py SHA256 = D1D38A
```

Formula still `S=K*(T1+T2+T3)`; golden linguistic S≈0.651324761885.

---

## Data export

```powershell
cd C:\Users\damia\Desktop\pflt\pflt-Ada
python export_atlas_for_ada.py   # domain_atlas + anchors + unet sample hyp
python export_data_for_ada.py    # densify/gold/train_mass
alr build
```

---

## CLI map

```powershell
.\bin\pflt_main.exe archive
.\bin\pflt_main.exe atlas "astronomy quantum linguistics"
.\bin\pflt_main.exe cert "what is zipf entropy and fsot scalar"
.\bin\pflt_main.exe vision unet
.\bin\pflt_main.exe vision A1 N5 S34
.\bin\pflt_main.exe audio aqua la
.\bin\pflt_main.exe converse "what is zipf and aqua lingua"
.\bin\pflt_main.exe ltm recall aqua
.\bin\pflt_main.exe status
.\bin\pflt_main.exe eval
```

---

## Architecture (students vs law)

```
I:\FSOT-Physical-Archive  (constitution)
   vendor/fsot_compute.py  --LIVE SHA256 D1D38A-->  Ada kernel pin
   linguistics_derivations --> anchors.tsv --> cert gate
   domain catalog 402      --> domain_atlas.tsv --> atlas route

Sensory students (never rewrite law):
   vision: multilayer field | Gardiner labels | U-Net hyp TSV
   audio:  IPA + articulatory + S→tempo/energy
   morph:  reverse peels + train_mass

Product surface:
   converse = translate + atlas + pathway + teach + cert + LTM + ledger
```

---

## Still later (honest residual)

- Real raster image decode + trained U-Net **weights** (hyp TSV contract is ready)
- Full Lean bridge process spawn on every numeric claim (Ada cert uses golden panel + anchors)
- SR-ITE continuous stream driver (Zig/photonic) — LTM file is the portable subset
- 402 domains fully drive pathway enum (today: atlas string match + core Domain_Id enum)

---

## One-line

> V6 closes the archive/sensory/cert gaps: **live D1D38A**, **410-domain atlas**, **anchors+cert**, **U-Net hyp load**, **LTM mulling** — all under Ada product binary.
