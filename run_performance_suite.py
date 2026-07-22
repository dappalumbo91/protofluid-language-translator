#!/usr/bin/env python3
"""
Honest performance suite for PFLT open-set translator.

Runs:
  1) lang_tables load check
  2) gap-pack / demonym smoke forms
  3) held-out CORE climb (90/10, train inject, no test leakage)
  4) formal FSOT golden asserts (if available)
  5) writes data/performance_suite_report.json

Usage:
  python run_performance_suite.py
  python run_performance_suite.py --skip-formal
  python run_performance_suite.py --skip-climb   # tables + formal only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "performance_suite_report.json"


def _run(args: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        r = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or ""))[-4000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, str(e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-formal", action="store_true")
    ap.add_argument("--skip-climb", action="store_true")
    args = ap.parse_args()

    report: dict = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Honest open-set PFLT performance (analyze→gloss, not NMT BLEU)",
        "layers": {},
    }

    # --- 1) JSON tables ---
    print("=== 1) lang_tables ===", flush=True)
    try:
        from lang_tables import (
            demonym_seeds,
            form_sense_prefer,
            gap_seeds,
            load_lang,
            sense_clusters,
        )

        report["layers"]["lang_tables"] = {
            "ok": True,
            "form_sense": len(form_sense_prefer()),
            "seeds": len(gap_seeds()),
            "clusters": len(sense_clusters()),
            "demonyms": len(demonym_seeds()),
            "langs": {
                "grc": bool(load_lang("grc")),
                "la": bool(load_lang("la")),
                "ang": bool(load_lang("ang")),
                "en": bool(load_lang("en")),
            },
        }
        print("  ok", report["layers"]["lang_tables"], flush=True)
    except Exception as e:
        report["layers"]["lang_tables"] = {"ok": False, "error": str(e)}
        print("  FAIL", e, flush=True)

    # --- 2) Smoke forms (with train inject for morph) ---
    print("=== 2) smoke map_token ===", flush=True)
    smoke = {}
    try:
        from dual_track_eval import split_90_10
        from gap_pack import resolve_gap
        from demonym_resolve import demonym_resolve
        from name_gazetteer import NameGazetteer
        from PFLT_FSOT_2_1_aligned import PFLT
        from promote_and_train_classical import inject, load_all_gold, partition_core_name

        gold = load_all_gold()
        core, _ = partition_core_name(gold)
        train, _test = split_90_10(core)
        p = PFLT(
            load_historical=True,
            load_classical=False,
            load_hieroglyphs=False,
            load_domain_lexica=False,
            enable_gapfill=True,
        )
        inject(p, train[:15000], expand_paradigms=True)  # lighter inject for smoke speed
        p._name_gaz = NameGazetteer(load=False)

        cases = [
            ("aqua", "historical", "water"),
            ("manibus", "historical", "hand"),
            ("γνώμων", "mythological", "sundial"),
            ("βεβιασμένος", "mythological", "forced"),
            ("γοητεία", "mythological", "witchcraft"),
            ("Κρής", "mythological", "cretan"),
            ("γράμμα", "mythological", "letter"),
            ("δεσπότης", "mythological", "master"),
        ]
        rows = []
        hits = 0
        for w, ctx, expect in cases:
            m, exact = p.map_token(w, ctx)
            ml = (m or "").lower().replace("_", " ")
            ok = expect.lower() in ml or ml in expect.lower()
            if ok:
                hits += 1
            rows.append({"word": w, "pred": m, "expect": expect, "exact_flag": exact, "ok": ok})
        smoke = {
            "ok": hits >= 6,
            "hits": hits,
            "n": len(cases),
            "rate": hits / len(cases),
            "cases": rows,
            "gap_pack_gnomon": resolve_gap("γνώμων", {}, {}),
            "demonym_kres": demonym_resolve("Κρής", {}),
        }
        report["layers"]["smoke_map"] = smoke
        print(f"  smoke {hits}/{len(cases)} ok={smoke['ok']}", flush=True)
        for r in rows:
            print(f"    {r['word']:16s} -> {r['pred']!s:20s} expect={r['expect']} ok={r['ok']}", flush=True)
    except Exception as e:
        report["layers"]["smoke_map"] = {"ok": False, "error": str(e)}
        print("  FAIL", e, flush=True)

    # --- 3) Held-out core climb ---
    if not args.skip_climb:
        print("=== 3) held-out CORE climb ===", flush=True)
        code, out = _run([sys.executable, "climb_open_set.py"], timeout=900)
        climb_path = DATA / "climb_open_set_report.json"
        climb = {}
        if climb_path.exists():
            climb = json.loads(climb_path.read_text(encoding="utf-8"))
        report["layers"]["core_held_out"] = {
            "ok": code == 0 and bool(climb),
            "exit_code": code,
            "exact_rate": climb.get("exact_rate"),
            "partial_rate": climb.get("partial_rate"),
            "n_test": climb.get("n_test"),
            "n_misses": climb.get("n_misses"),
            "pul_terms": climb.get("pul_terms"),
            "paradigm_terms": climb.get("paradigm_terms"),
            "sense_bank_forms": climb.get("sense_bank_forms"),
            "delta_pp_vs_original": climb.get("delta_pp_vs_original"),
            "baseline_ref": climb.get("baseline_ref"),
            "tail": out[-800:],
        }
        pr = climb.get("partial_rate")
        print(
            f"  CORE exact={100*(climb.get('exact_rate') or 0):.2f}% "
            f"partial={100*(pr or 0):.2f}% n={climb.get('n_test')} "
            f"Δorig={climb.get('delta_pp_vs_original')}",
            flush=True,
        )
    else:
        report["layers"]["core_held_out"] = {"skipped": True}

    # --- 4) Formal ---
    if not args.skip_formal:
        print("=== 4) formal golden asserts ===", flush=True)
        code, out = _run([sys.executable, "formal/run_formal_asserts.py"], timeout=300)
        formal_path = ROOT / "formal" / "assert_report.json"
        formal = {}
        if formal_path.exists():
            formal = json.loads(formal_path.read_text(encoding="utf-8"))
        report["layers"]["formal"] = {
            "ok": bool(formal.get("overall_ok")),
            "exit_code": code,
            "python_ok": (formal.get("python") or {}).get("ok"),
            "lean_ok": (formal.get("lean") or {}).get("ok"),
            "coq_ok": (formal.get("coq") or {}).get("ok"),
            "tail": out[-500:],
        }
        print(f"  formal overall_ok={formal.get('overall_ok')}", flush=True)
    else:
        report["layers"]["formal"] = {"skipped": True}

    # dual-track snapshot if present
    dual = DATA / "dual_track_report.json"
    if dual.exists():
        try:
            d = json.loads(dual.read_text(encoding="utf-8"))
            report["layers"]["dual_track_snapshot"] = {
                "built_utc": d.get("built_utc"),
                "core_partial": (d.get("core_90_10") or {}).get("partial"),
                "name_open": (d.get("name_open_train_seeds") or {}).get("partial"),
                "name_pleiades": (d.get("name_open_train_seeds_pleiades") or {}).get("partial"),
                "name_deployed": (d.get("name_deployed_full_gaz") or {}).get("partial"),
                "note": "From last dual_track_eval.py run (not re-run in this suite unless separate)",
            }
        except Exception:
            pass

    # overall
    layers = report["layers"]
    checks = []
    for k in ("lang_tables", "smoke_map", "core_held_out", "formal"):
        layer = layers.get(k) or {}
        if layer.get("skipped"):
            continue
        checks.append(bool(layer.get("ok")))
    report["overall_ok"] = all(checks) if checks else False
    report["summary"] = {
        "core_partial_pct": 100 * ((layers.get("core_held_out") or {}).get("partial_rate") or 0),
        "core_exact_pct": 100 * ((layers.get("core_held_out") or {}).get("exact_rate") or 0),
        "smoke_rate": (layers.get("smoke_map") or {}).get("rate"),
        "formal_ok": (layers.get("formal") or {}).get("ok"),
        "delta_pp_vs_original_17_8": (layers.get("core_held_out") or {}).get("delta_pp_vs_original"),
    }

    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== SUMMARY ===", flush=True)
    print(json.dumps(report["summary"], indent=2), flush=True)
    print("overall_ok=", report["overall_ok"], "->", OUT, flush=True)
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
