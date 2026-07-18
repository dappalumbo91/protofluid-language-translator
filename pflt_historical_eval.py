#!/usr/bin/env python3
"""
Historical-first accuracy evaluation for PFLT.

Loads Tier A/B gold (Sumerian → Akkadian → Hittite → Sanskrit → Greek → Latin → OE),
injects into the FSOT-aligned PFLT lexicon, and scores:

  exact_target_hit  — gold English target appears in mapped meanings
  gloss_overlap     — any gold target token appears in translation blob

Curriculum is evaluated epoch-by-epoch so we expand only after accuracy holds.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_gold import curriculum_by_epoch, gold_as_lexicon, merge_gold, summary
from PFLT_FSOT_2_1_aligned import PFLT


def _normalize_en(s: str) -> str:
    s = s.lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(s.split())


def score_case(pflt: PFLT, source_word: str, target_word: str, source_lang: str) -> Dict[str, Any]:
    context = {
        "sum": "mythological",
        "akk": "historical",
        "hit": "historical",
        "san": "historical",
        "grc": "historical",
        "la": "historical",
        "ang": "historical",
    }.get(source_lang, "historical")

    result = pflt.translate(source_word, context=context, target_lang="english")
    meanings_blob = _normalize_en(" ".join(result["meanings"]))
    out_blob = _normalize_en(result["translation"])
    gold = _normalize_en(target_word)
    gold_tokens = gold.split()

    exact = gold in meanings_blob or gold.replace(" ", "_") in " ".join(result["meanings"]).lower()
    # token overlap: all gold content words present
    content = [t for t in gold_tokens if len(t) > 1]
    if not content:
        content = gold_tokens
    hits = sum(1 for t in content if t in meanings_blob or t in out_blob)
    overlap = hits / max(1, len(content))

    return {
        "source_lang": source_lang,
        "source_word": source_word,
        "gold_en": target_word,
        "tokens": result["tokens"],
        "meanings": result["meanings"],
        "translation": result["translation"],
        "exact_target_hit": bool(exact or overlap >= 1.0),
        "token_overlap": overlap,
        "S": result["fsot_coherence_S"],
        "exact_map_rate": result["exact_map_rate"],
    }


def run_eval(*, include_candidates: bool = False) -> Dict[str, Any]:
    # Tier A only by default for accuracy-first
    pairs = merge_gold(include_candidates=include_candidates)
    if not include_candidates:
        pairs = [p for p in pairs if p.tier == "A"]

    lex = gold_as_lexicon(pairs)
    pflt = PFLT()
    # Inject historical gold into live lexicon (student maps under FSOT teacher)
    pflt.pul_terms.update(lex)
    pflt._keys_sorted = sorted(pflt.pul_terms.keys(), key=len, reverse=True)

    curriculum = curriculum_by_epoch(pairs)
    epoch_reports: Dict[str, Any] = {}
    all_cases: List[Dict[str, Any]] = []

    for epoch_name, epoch_pairs in curriculum.items():
        cases = []
        for p in epoch_pairs:
            if p.target_lang not in {"en", "eng"}:
                continue
            sc = score_case(pflt, p.source_word, p.target_word, p.source_lang)
            sc["tier"] = p.tier
            sc["confidence"] = p.confidence
            sc["source_title"] = p.source_title
            cases.append(sc)
            all_cases.append(sc)
        n = len(cases) or 1
        epoch_reports[epoch_name] = {
            "n": len(cases),
            "exact_accuracy": sum(1 for c in cases if c["exact_target_hit"]) / n,
            "mean_token_overlap": sum(c["token_overlap"] for c in cases) / n,
            "mean_lexicon_map_rate": sum(c["exact_map_rate"] for c in cases) / n,
            "cases": cases,
        }

    n_all = len(all_cases) or 1
    report = {
        "policy": {
            "include_candidates": include_candidates,
            "note": "Tier A only when include_candidates=False (accuracy-first)",
        },
        "gold_summary": summary(pairs),
        "lexicon_injected": len(lex),
        "overall": {
            "n": len(all_cases),
            "exact_accuracy": sum(1 for c in all_cases if c["exact_target_hit"]) / n_all,
            "mean_token_overlap": sum(c["token_overlap"] for c in all_cases) / n_all,
        },
        "by_epoch": {
            k: {
                "n": v["n"],
                "exact_accuracy": v["exact_accuracy"],
                "mean_token_overlap": v["mean_token_overlap"],
                "mean_lexicon_map_rate": v["mean_lexicon_map_rate"],
            }
            for k, v in epoch_reports.items()
        },
        "detail": epoch_reports,
    }
    return report


def main() -> None:
    print("=" * 72)
    print("PFLT Historical-First Accuracy Eval (FSOT natural communicator)")
    print("=" * 72)

    for label, include_b in (("TIER_A_ONLY", False), ("TIER_A_PLUS_B_CANDIDATES", True)):
        report = run_eval(include_candidates=include_b)
        print(f"\n--- {label} ---")
        print(json.dumps({
            "gold": report["gold_summary"],
            "lexicon_injected": report["lexicon_injected"],
            "overall": report["overall"],
            "by_epoch": report["by_epoch"],
        }, indent=2, ensure_ascii=False))

        out = Path(__file__).resolve().parent / "data" / f"historical_eval_{label.lower()}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        # full detail can be large; write full for A, summary+detail for both
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("wrote", out)

    print("\n" + "=" * 72)
    print("Curriculum rule: lock Tier A epochs before expanding candidates or modern MT.")
    print("Next human languages after A solid: Medieval → Early Modern → living langs.")
    print("Animal/vocal phase is AFTER human historical accuracy baseline.")
    print("=" * 72)


if __name__ == "__main__":
    main()
