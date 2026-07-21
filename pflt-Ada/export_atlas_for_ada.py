#!/usr/bin/env python3
"""Export FSOT domain atlas + linguistics anchors for Ada gap-fill."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA = Path(__file__).resolve().parent / "data"
ARCHIVE_LING = Path(
    r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full"
    r"\vendor\linguistics\linguistics_derivations.json"
)


def main() -> None:
    ADA.mkdir(parents=True, exist_ok=True)
    cat = json.loads(
        (ROOT / "data" / "fsot_domain_catalog.json").read_text(encoding="utf-8")
    )
    domains = cat.get("domains") or {}
    out = ADA / "domain_atlas.tsv"
    n = 0
    with out.open("w", encoding="utf-8") as w:
        w.write("name\tD_eff\tdelta_psi\tdelta_theta\tobserved\tkeywords\n")
        for name, rec in sorted(domains.items(), key=lambda kv: kv[0].lower()):
            if not isinstance(rec, dict):
                continue
            de = rec.get("D_eff", 12.0)
            dp = rec.get("delta_psi", 0.8)
            dt = rec.get("delta_theta", 1.0)
            obs = 1 if rec.get("observed", True) else 0
            display = str(rec.get("display") or name)
            # keywords: snake/space split + name tokens
            toks = re.split(r"[_\s\-]+", display.lower())
            toks = [t for t in toks if len(t) >= 3]
            kw = " ".join(dict.fromkeys(toks))  # unique preserve order
            name_s = str(name).replace("\t", " ").replace("\n", " ")
            w.write(f"{name_s}\t{de}\t{dp}\t{dt}\t{obs}\t{kw}\n")
            n += 1
    print("domain_atlas", n, "->", out)

    # linguistics anchors
    ling_src = ARCHIVE_LING
    if not ling_src.exists():
        ling_src = ROOT / "data" / "linguistics_derivations.json"
    anchors_out = ADA / "linguistics_anchors.tsv"
    m = 0
    if ling_src.exists():
        obj = json.loads(ling_src.read_text(encoding="utf-8"))
        rows = obj.get("derivations") if isinstance(obj, dict) else obj
        with anchors_out.open("w", encoding="utf-8") as w:
            w.write("name\tcomputed\terror_pct\tformula\tstatus\n")
            for d in rows or []:
                if not isinstance(d, dict):
                    continue
                name = str(d.get("name", "")).replace("\t", " ")
                comp = d.get("computed", "")
                err = d.get("error_pct", "")
                form = str(d.get("formula", "")).replace("\t", " ").replace("\n", " ")
                st = d.get("status", "")
                w.write(f"{name}\t{comp}\t{err}\t{form}\t{st}\n")
                m += 1
    print("linguistics_anchors", m, "->", anchors_out)

    # sample U-Net hypothesis file (contract for vision student)
    hyp = ADA / "unet_hypotheses_sample.tsv"
    with hyp.open("w", encoding="utf-8") as w:
        w.write("gardiner\tconfidence\tsource\tbbox\n")
        w.write("A1\t0.91\tunet_slot\t0.10,0.20,0.15,0.25\n")
        w.write("N5\t0.87\tunet_slot\t0.40,0.18,0.12,0.20\n")
        w.write("S34\t0.84\tunet_slot\t0.65,0.22,0.14,0.22\n")
    print("unet_hypotheses_sample ->", hyp)


if __name__ == "__main__":
    main()
