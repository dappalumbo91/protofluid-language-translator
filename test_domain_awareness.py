#!/usr/bin/env python3
from PFLT_FSOT_2_1_aligned import PFLT

p = PFLT()
cases = [
    ("cosmological", "s8", "structure"),
    ("hieroglyphic", "s8", "atef"),
    ("nuclear", "H2", "deuterium"),
    ("genomic", "ATG-GTG-CAC-CTG-ACT", "start"),
    ("mythological", "me", "divine"),
]
ok = 0
for ctx, text, needle in cases:
    r = p.translate(text, context=ctx)
    blob = " ".join(r["meanings"]).lower()
    hit = needle in blob
    ok += int(hit)
    print(f"[{'OK' if hit else 'FAIL'}] {ctx:14s} {text!r:30s} -> {r['meanings']}")
print(f"{ok}/{len(cases)} domain-awareness checks")
raise SystemExit(0 if ok == len(cases) else 1)
