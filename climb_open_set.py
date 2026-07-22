#!/usr/bin/env python3
"""
Climb held-out core open-set accuracy.

Pipeline:
  1) Train inject with multi-gloss sense banks
  2) Score held-out core
  3) Mine empty / wrong-sense patterns
  4) Report climb metrics

Usage:
  python climb_open_set.py
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dual_track_eval import split_90_10
from held_out_classical import score
from name_gazetteer import NameGazetteer
from PFLT_FSOT_2_1_aligned import PFLT
from promote_and_train_classical import inject, load_all_gold, partition_core_name

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "climb_open_set_report.json"


def main() -> None:
    gold = load_all_gold()
    core, names = partition_core_name(gold)
    train, test = split_90_10(core)
    print(
        f"gold={len(gold)} core={len(core)} name={len(names)} "
        f"train={len(train)} test={len(test)}",
        flush=True,
    )

    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=True)
    p._name_gaz = NameGazetteer(load=False)
    bank_n = sum(len(v) for v in (p.sense_bank or {}).values())
    print(
        f"pul={len(p.pul_terms)} para={len(getattr(p, 'paradigm_terms', {}) or {})} "
        f"sense_bank_forms={len(p.sense_bank or {})} sense_bank_glosses={bank_n}",
        flush=True,
    )

    s = score(p, test, miss_cap=80)
    print(
        f"CORE exact={s['exact_rate']*100:.2f}% partial={s['exact_or_partial_rate']*100:.2f}% "
        f"n={s['n']} misses={s.get('n_misses')}",
        flush=True,
    )

    # Mine miss patterns for next climb
    empty = 0
    wrong = 0
    for d in s.get("misses") or []:
        pred = " ".join(d.get("meanings") or [])
        if pred in {"narrative_flow", "heritage_flow", "generic_dynamics"} or not pred:
            empty += 1
        else:
            wrong += 1

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "climb open-set toward leading classical analyze-then-gloss systems",
        "n_train": len(train),
        "n_test": len(test),
        "pul_terms": len(p.pul_terms),
        "paradigm_terms": len(getattr(p, "paradigm_terms", {}) or {}),
        "sense_bank_forms": len(p.sense_bank or {}),
        "sense_bank_glosses": bank_n,
        "exact_rate": s["exact_rate"],
        "partial_rate": s["exact_or_partial_rate"],
        "n_misses": s.get("n_misses"),
        "miss_empty_sample": empty,
        "miss_wrong_sample": wrong,
        "hits_sample": s.get("hits_sample", [])[:8],
        "misses_sample": s.get("misses", [])[:12],
        "baseline_ref": {
            "original_partial": 0.1784,
            "meta_peak_partial": 0.2318,
            "prior_climb_partial": 0.2361,
        },
        "delta_pp_vs_original": (s["exact_or_partial_rate"] - 0.1784) * 100,
        "delta_pp_vs_prior": (s["exact_or_partial_rate"] - 0.2361) * 100,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    push = DATA / "push_open_report.json"
    d = {}
    if push.exists():
        try:
            d = json.loads(push.read_text(encoding="utf-8"))
        except Exception:
            d = {}
    d["core_only_partial"] = s["exact_or_partial_rate"]
    d["climb_open_set"] = {
        "partial": s["exact_or_partial_rate"],
        "exact": s["exact_rate"],
        "delta_pp_vs_original": report["delta_pp_vs_original"],
        "report": str(OUT),
    }
    push.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("wrote", OUT, flush=True)
    print(
        f"Δ vs original {report['delta_pp_vs_original']:+.2f}pp  "
        f"Δ vs prior {report['delta_pp_vs_prior']:+.2f}pp",
        flush=True,
    )


if __name__ == "__main__":
    main()
