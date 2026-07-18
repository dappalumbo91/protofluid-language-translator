#!/usr/bin/env python3
"""
Per-domain starter lexica for all FSOT 2.1 catalog domains.

Not deep expert dictionaries — deterministic, auditable seeds so every domain
has process vocabulary under PFLT (expand later with lab corpora).

Output:
  data/domain_lexica.json
  D:\\training data\\...\\domain_lexica.json
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

CATALOG = Path(r"C:\Users\damia\Desktop\pflt\data\fsot_domain_catalog.json")
OUT = Path(r"C:\Users\damia\Desktop\pflt\data\domain_lexica.json")
DRIVE = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\domain_lexica.json")

# Shared process stems (FSOT narrative style)
STEMS = [
    "field",
    "flow",
    "coherence",
    "resonance",
    "flux",
    "coupling",
    "scale",
    "phase",
    "threshold",
    "observable",
    "process",
    "structure",
    "dynamics",
    "measurement",
    "transfer",
    "equilibrium",
]


def slug_parts(name: str) -> List[str]:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    parts = [p for p in s.split("_") if p and p.lower() not in {"the", "and", "of", "panel", "bridge"}]
    return parts


def build_for_domain(display: str, key: str) -> Dict[str, str]:
    parts = slug_parts(display)
    head = parts[0].lower() if parts else key
    lex: Dict[str, str] = {}
    # domain identity
    lex[key] = f"{key}_domain"
    lex[head] = f"{head}_domain"
    # compound surface forms
    for p in parts[:4]:
        pl = p.lower()
        lex[pl] = f"{pl}_aspect"
        for stem in STEMS[:8]:
            lex[f"{pl}_{stem}"] = f"{pl}_{stem}"
            lex[f"{pl} {stem}"] = f"{pl}_{stem}"
    # generic stems scoped by domain key (avoid global collisions via domain map only)
    for stem in STEMS:
        lex[f"{key}_{stem}"] = f"{key}_{stem}"
    return lex


def main() -> None:
    cat = json.loads(CATALOG.read_text(encoding="utf-8"))
    domains = cat.get("domains") or {}
    by_domain: Dict[str, Dict[str, str]] = {}
    global_safe: Dict[str, str] = {}  # only multi-part keys safe globally

    for key, row in domains.items():
        if row.get("kind") == "alias":
            continue
        display = row.get("display") or row.get("domain") or key
        dlex = build_for_domain(str(display), str(key))
        by_domain[str(key)] = dlex
        for k, v in dlex.items():
            if "_" in k or " " in k:
                global_safe.setdefault(k, v)

    payload = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_domains": len(by_domain),
        "n_global_safe_keys": len(global_safe),
        "by_domain": by_domain,
        "global_safe": global_safe,
        "note": (
            "Per-domain maps used when context matches. "
            "global_safe multi-token keys merge into pul_terms without single-word collisions."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    DRIVE.parent.mkdir(parents=True, exist_ok=True)
    DRIVE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"domains={len(by_domain)} global_safe={len(global_safe)}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
