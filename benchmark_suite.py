#!/usr/bin/env python3
"""
PFLT / FSOT communicator benchmarks (NOT LLM leaderboard metrics).

We intentionally do **not** optimize for:
  - MMLU / chat preference / next-token perplexity as primary goals

We DO report metrics that match this architecture:

1) Lexical grounding accuracy (historical + classical + hieroglyph closed-set)
2) FSOT scalar health (finite S, domain routing, quirk_mod active when observed)
3) Vision contract readiness (stub: labels → meanings map rate)
4) Optional: compare against a thin neural baseline later (same tasks)

This is how you stack against cutting-edge AI without becoming an LLM:
  - Same *task families* where useful (retrieval@1, F1, CER for OCR)
  - Different *objective* (FSOT-gated interlingua communicator)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PFLT_FSOT_2_1_aligned import PFLT, compute_S_D_chaotic, DOMAIN_PARAMS
from vision_stub import vision_translate


def bench_classical(pflt: PFLT, n: int = 100) -> Dict[str, Any]:
    path = Path(__file__).resolve().parent / "data" / "classical_grc_la_promoted_tierA.jsonl"
    if not path.exists():
        return {"ok": False, "error": "missing classical gold"}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    rows = rows[:n]
    hits = 0
    for r in rows:
        out = pflt.translate(r["source_word"], context="historical", target_lang="english")
        blob = " ".join(out["meanings"]).lower() + " " + out["translation"].lower()
        gold = r["target_word"].lower()
        mk = r.get("meaning_key", "").lower().replace("_", " ")
        if gold in blob or mk.replace("_", " ") in blob or r.get("meaning_key", "").lower() in blob:
            hits += 1
        elif any(t in blob for t in gold.split() if len(t) > 2):
            hits += 0.5
    return {
        "ok": True,
        "n": len(rows),
        "exactish_accuracy": hits / max(1, len(rows)),
        "task": "classical_grc_la_closed_set",
    }


def bench_hieroglyph(pflt: PFLT) -> Dict[str, Any]:
    codes = ["A1", "D21", "G17", "N5", "S34", "D4", "G5", "I9", "N35", "X1"]
    hits = 0
    details = []
    for c in codes:
        out = pflt.translate(c, context="hieroglyphic")
        ok = out["exact_map_rate"] >= 1.0 and out["meanings"] and "generic" not in out["meanings"][0]
        hits += int(ok)
        details.append({"code": c, "ok": ok, "meaning": out["meanings"], "S": out["fsot_coherence_S"]})
    return {
        "ok": True,
        "n": len(codes),
        "map_accuracy": hits / len(codes),
        "details": details,
        "task": "hieroglyph_unikemet_closed_set",
    }


def bench_vision_contract() -> Dict[str, Any]:
    r = vision_translate(gardiner=["A1", "N5", "S34"])
    ok = bool(r.hypotheses) and r.pflt.get("exact_map_rate", 0) >= 1.0
    return {
        "ok": ok,
        "task": "vision_stub_labels_to_meaning",
        "map_rate": r.pflt.get("exact_map_rate"),
        "pipeline": r.pipeline,
        "translation": r.pflt.get("translation"),
    }


def bench_scalar_health() -> Dict[str, Any]:
    rows = []
    for name, p in DOMAIN_PARAMS.items():
        panel = compute_S_D_chaotic(
            D_eff=float(p["D_eff"]),
            observed=bool(p["observed"]),
            delta_psi=float(p["delta_psi"]),
            delta_theta=float(p["delta_theta"]),
        )
        rows.append(
            {
                "domain": name,
                "S": panel.S,
                "finite": abs(panel.S) < 1e6 and panel.S == panel.S,
                "observed": panel.observed,
                "quirk_mod": panel.quirk_mod,
            }
        )
    return {
        "ok": all(r["finite"] for r in rows),
        "task": "fsot_scalar_domain_health",
        "n_domains": len(rows),
        "domains": rows,
    }


def positioning_block() -> Dict[str, Any]:
    return {
        "product_class": "FSOT interlingua communicator (symbolic + neural student slots)",
        "not_building": "frontier general LLM / chat assistant",
        "vs_cutting_edge": {
            "frontier_llm": {
                "strength": "open-domain fluency, broad world knowledge, tool use",
                "weakness_for_your_goal": "opaque params, weak formal guarantees, poor cross-domain physics unity",
                "overlap": "can share *benchmark task shapes* (retrieval, OCR CER, translation F1)",
            },
            "classical_mt_interlingua": {
                "strength": "explainable pipelines, domain lexica",
                "your_edge": "FSOT scalar teacher + multi-domain (DNA, myth, hieroglyph, cosmos) one geometry",
            },
            "vision_ocr_sota": {
                "strength": "image→text accuracy",
                "your_use": "U-Net/OCR as *student eyes* only; meaning remains Unikemet/FSOT gated",
            },
            "neuro_symbolic_ai": {
                "closest_peer_class": True,
                "your_edge": "seed-derived law + Lean cross-verification + historical curriculum",
            },
        },
        "benchmark_axes_we_own": [
            "closed_set_lexicon_accuracy (hist/classical/glyph)",
            "held_out_gap_fill under FSOT gates (future)",
            "glyph_detection_top1 / CER (when U-Net online)",
            "scalar_panel_coherence / kill_criteria pass rate",
            "cross_domain_same_engine (gene + myth + glyph + H0)",
        ],
        "benchmark_axes_we_borrow_not_chase": [
            "MMLU as primary KPI",
            "Chatbot Arena ELO",
            "next-token perplexity on Common Crawl",
        ],
    }


def main() -> None:
    pflt = PFLT()
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "positioning": positioning_block(),
        "lexicon_size": len(pflt.pul_terms),
        "benchmarks": {
            "scalar_health": bench_scalar_health(),
            "hieroglyph": bench_hieroglyph(pflt),
            "classical": bench_classical(pflt),
            "vision_contract": bench_vision_contract(),
        },
    }
    out = Path(__file__).resolve().parent / "data" / "benchmark_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    drive = Path(r"D:\training data\pflt_linguistics\00_manifests\benchmark_report.json")
    drive.parent.mkdir(parents=True, exist_ok=True)
    drive.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    b = report["benchmarks"]
    print("=== PFLT / FSOT communicator benchmark ===")
    print(f"lexicon_size: {report['lexicon_size']}")
    print(f"scalar_health: {b['scalar_health']['ok']} domains={b['scalar_health']['n_domains']}")
    print(f"hieroglyph map_accuracy: {b['hieroglyph'].get('map_accuracy')}")
    print(f"classical exactish: {b['classical']}")
    print(f"vision_contract: {b['vision_contract']['ok']} map={b['vision_contract'].get('map_rate')}")
    print(f"wrote {out}")
    print(f"wrote {drive}")


if __name__ == "__main__":
    main()
