#!/usr/bin/env python3
"""
Fast Protofluid sense translate CLI — the real killshot path.

Uses sense_interlingua (form → SENSE → form) + archive-pinned FSOT law panel.
No NMT, no QLoRA, no multi-hour beam decode.

Examples:
  python pflt_sense_translate.py "aqua manus lingua" --src la --tgt en
  python pflt_sense_translate.py --smoke
  python pflt_sense_translate.py "water" --src en --tgt de
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sense_interlingua import SenseInterlingua, smoke_identity


def main() -> int:
    ap = argparse.ArgumentParser(description="PFLT sense-identity translate (FSOT-pinned)")
    ap.add_argument("text", nargs="?", default="", help="Source text")
    ap.add_argument("--src", default="la", help="Source language code")
    ap.add_argument("--tgt", default="en", help="Target language code")
    ap.add_argument("--domain", default="linguistic", help="FSOT domain frame")
    ap.add_argument("--smoke", action="store_true", help="Run identity battery")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    if args.smoke or not args.text.strip():
        if not args.text.strip():
            out = smoke_identity()
        else:
            out = smoke_identity()
        if args.json or args.smoke:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(f"sense smoke {out['passed']}/{out['total']} ({out['pct']}%)")
            print(f"authority_ok={out['authority_ok']} S={out['S_linguistic']}")
            for c in out["cases"]:
                mark = "OK" if c["ok"] else "FAIL"
                print(f"  [{mark}] {c['in']} ({c['src']}→{c['tgt']}) expect={c['expect']} got={c['got']}")
        if not args.text.strip():
            return 0 if out["passed"] == out["total"] else 1
        # fall through if text also given

    if args.text.strip():
        ix = SenseInterlingua()
        r = ix.translate(
            args.text, source_lang=args.src, target_lang=args.tgt, domain=args.domain
        )
        payload = {
            "input": r.input_text,
            "source_lang": r.source_lang,
            "target_lang": r.target_lang,
            "meanings_en": r.meanings_en,
            "senses": r.senses,
            "target_forms": r.target_forms,
            "translation": " ".join(r.target_forms),
            "resolution": r.resolution,
            "exact_rate": r.exact_rate,
            "elapsed_ms": r.elapsed_ms,
            "fsot": r.fsot,
            "authority_ok": r.authority_ok,
            "note": r.note,
            "stats": ix.stats(),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"IN  [{r.source_lang}] {r.input_text}")
            print(f"OUT [{r.target_lang}] {' '.join(r.target_forms)}")
            print(f"EN  meanings: {', '.join(r.meanings_en)}")
            print(f"exact_rate={r.exact_rate:.2f}  {r.elapsed_ms} ms")
            if r.fsot.get("authority_ok"):
                print(
                    f"FSOT S={r.fsot.get('S'):.6f} "
                    f"T1={r.fsot.get('T1'):.4f} T2={r.fsot.get('T2'):.4f} T3={r.fsot.get('T3'):.4f} "
                    f"pin={r.fsot.get('pin')} authority_ok=True"
                )
            else:
                print(f"FSOT panel: {r.fsot}")
            for line in r.resolution:
                print(f"  {line}")
        return 0 if r.exact_rate >= 1.0 or r.meanings_en else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
