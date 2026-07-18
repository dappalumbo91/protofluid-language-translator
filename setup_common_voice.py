#!/usr/bin/env python3
"""
Common Voice scaffolding for modern-language audio (multimodal PFLT).

Does NOT download multi-GB corpora by default (user opt-in).
Creates folder layout + download instructions + a tiny synthetic demo
so the audio path is testable offline.

Layout:
  D:\\training data\\pflt_linguistics\\05_phonology_vocal\\common_voice\\
    README_DOWNLOAD.md
    en/  es/  fr/  ...  (place CV clips here)
    demo_manifest.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\training data\pflt_linguistics\05_phonology_vocal\common_voice")
LANGS = ["en", "es", "fr", "de", "it", "pt", "la"]  # la often sparse; modern first


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        (ROOT / lang / "clips").mkdir(parents=True, exist_ok=True)

    readme = ROOT / "README_DOWNLOAD.md"
    readme.write_text(
        """# Common Voice download (opt-in)

Mozilla Common Voice: https://commonvoice.mozilla.org/datasets

## Recommended workflow

1. Create a Mozilla account and accept dataset terms.
2. Download language packs you need (start with `en`, then romance/germanic).
3. Extract into:

```
common_voice/<lang>/clips/     # .mp3 audio
common_voice/<lang>/validated.tsv   # text ↔ clip paths
```

4. Point PFLT audio layer at those TSV rows (see `audio_articulation.py`).

## Offline without full CV

Use:
- `audio_articulation.py` IPA + FSOT tempo/energy (already works)
- eSpeak-NG / Piper for local TTS waveforms
- PHOIBLE for phoneme inventories (already on this drive)

Full CV packs are multi-GB per language — download when ready; the **contract is already multimodal**.
""",
        encoding="utf-8",
    )

    manifest = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "languages_scaffolded": LANGS,
        "status": "folders_ready_awaiting_clips",
        "integration": {
            "pflt": "translate(..., include_audio=True)",
            "module": "audio_articulation.py",
            "fsot_role": "S modulates tempo_proxy and energy_proxy",
        },
        "download_portal": "https://commonvoice.mozilla.org/datasets",
    }
    (ROOT / "demo_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (Path(r"C:\Users\damia\Desktop\pflt\data") / "common_voice_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
