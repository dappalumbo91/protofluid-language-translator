#!/usr/bin/env python3
"""
Honest open-set eval for classical Latin/Greek gold.

Split promoted Tier-A list 80/20 by hash (stable).
Inject ONLY train half into a fresh PFLT (no classical full inject).
Score test half — this is the number that matters for generalization claims.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PFLT_FSOT_2_1_aligned import PFLT

PROMOTED = Path(__file__).resolve().parent / "data" / "classical_grc_la_promoted_tierA.jsonl"
OUT = Path(__file__).resolve().parent / "data" / "held_out_classical_report.json"
DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold\held_out_classical_report.json")


def load_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def split_rows(rows: List[Dict[str, Any]], train_frac: float = 0.8) -> Tuple[List, List]:
    train, test = [], []
    for r in rows:
        key = f"{r['source_lang']}:{r['source_word']}".encode("utf-8")
        h = int(hashlib.sha256(key).hexdigest(), 16) % 1000
        if h < int(train_frac * 1000):
            train.append(r)
        else:
            test.append(r)
    return train, test


_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "onto", "upon",
    "flowing", "resonant", "stabilized", "softened", "fluid", "translation",
    "fsot", "aligned", "heritage", "generic", "dynamics", "process", "flow",
    "field", "narrative", "domain", "aspect", "structure", "related",
}


def _soft_overlap(gold: str, blob: str, meaning_key: str) -> bool:
    """Partial credit: real content overlap only (len>=4, no stopwords/system words)."""
    g = gold.lower().replace("_", " ")
    # strip common dictionary wrappers
    g = re.sub(r"^(a|an|the)\s+", "", g)
    g = re.sub(r"^to\s+", "", g)
    b = (blob or "").lower().replace("_", " ")
    mk = (meaning_key or "").lower().replace("_", " ")
    # strip system prefixes from blob
    b = re.sub(r"\b(flowing|resonant|stabilized|softened|fluid)_?", " ", b)
    # demonym / inhabitant glosses: "an inhabitant of thespiae" ↔ thespiae / thespian
    g_core = re.sub(
        r"\b(inhabitant|inhabitants|native|natives|people|citizen|citizens)\s+(of\s+)?",
        " ",
        g,
    )
    g_core = re.sub(r"\b(ancient|classical|roman|greek|city of|town of)\b", " ", g_core)
    content = [
        t for t in re.findall(r"[a-z]{4,}", g + " " + g_core)
        if t not in _STOP
    ]
    # dedupe preserve order
    seen_c = set()
    content = [t for t in content if not (t in seen_c or seen_c.add(t))]
    if not content:
        # short glosses (eye, ant, law): allow exact 3-letter content match
        short = [t for t in re.findall(r"[a-z]{3}", g) if t not in _STOP]
        b_tokens = set(re.findall(r"[a-z]{3,}", b + " " + mk))
        return any(t in b_tokens for t in short)
    b_tokens = set(re.findall(r"[a-z]{3,}", b + " " + mk))
    # full token hit
    if any(t in b.split() or t in mk.split() or f"_{t}_" in f"_{b.replace(' ','_')}_" for t in content):
        return True
    # substring containment (celt ⊂ celtic, tooth ⊂ teeth) for len>=4
    for t in content:
        if len(t) >= 4 and (t in mk or t in b):
            return True
        for pt in b_tokens:
            if len(pt) >= 4 and (t in pt or pt in t):
                if min(len(t), len(pt)) / max(len(t), len(pt)) >= 0.5:
                    return True
    # ethnonym / stem neighbor: shared prefix of 4+ between gold content and pred tokens
    for t in content:
        if len(t) < 4:
            continue
        for pt in b_tokens:
            if len(pt) < 4:
                continue
            pref = 4 if min(len(t), len(pt)) < 6 else 5
            if t.startswith(pt[:pref]) or pt.startswith(t[:pref]):
                if min(len(t), len(pt)) / max(len(t), len(pt)) >= 0.5:
                    return True
    return False


def score(pflt: PFLT, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    exact = 0
    partial = 0
    details = []
    for r in rows:
        # language-aware context for better booster
        lang = (r.get("source_lang") or "la").lower()
        ctx = "historical"
        if lang in {"grc", "el"}:
            ctx = "mythological"  # routes booster to greek stems
        elif lang == "en":
            ctx = "english"
        out = pflt.translate(r["source_word"], context=ctx, target_lang="english")
        # Predicted meanings only — never score against gold meaning_key (that leaked 99% partial)
        pred = " ".join(out.get("meanings") or []).lower()
        blob = (pred + " " + (out.get("translation") or "")).lower()
        gold = r["target_word"].lower()
        gold_mk = (r.get("meaning_key") or "").lower()
        # strip leading articles for exact match (dict glosses often "a/an/the X")
        gold_core = re.sub(r"^(a|an|the)\s+", "", gold).strip()
        gold_mk_core = re.sub(r"^(a|an|the)_", "", gold_mk).strip("_")
        pred_flat = pred.replace("_", " ")
        hit = (
            gold in pred
            or gold_core in pred
            or gold_core.replace(" ", "_") in pred
            or gold_mk.replace("_", " ") in pred_flat
            or gold_mk in pred
            or gold_mk_core in pred
            or gold_mk_core.replace("_", " ") in pred_flat
            or (
                gold_mk
                and gold_mk in blob
                and gold_mk not in {"heritage_flow", "generic_dynamics", "narrative_flow"}
            )
        )
        soft = _soft_overlap(gold, pred, pred)  # only predicted meaning side
        if hit:
            exact += 1
            kind = "exact"
        elif soft:
            partial += 1
            kind = "partial"
        else:
            kind = "miss"
        details.append(
            {
                "lang": r["source_lang"],
                "word": r["source_word"],
                "gold": r["target_word"],
                "meanings": out["meanings"],
                "kind": kind,
                "map_rate": out["exact_map_rate"],
            }
        )
    n = max(1, len(rows))
    return {
        "n": len(rows),
        "exact": exact,
        "partial": partial,
        "exact_rate": exact / n,
        "exact_or_partial_rate": (exact + partial) / n,
        "misses": [d for d in details if d["kind"] == "miss"][:25],
        "hits_sample": [d for d in details if d["kind"] == "exact"][:10],
    }


def main() -> None:
    if not PROMOTED.exists():
        raise SystemExit(f"missing {PROMOTED} — run grow_classical_gold.py first")
    rows = load_rows(PROMOTED)
    train, test = split_rows(rows, 0.8)

    # Fresh engine: historical seed OK, classical ONLY from train split
    # Gap-fill student ON for open-set lift
    pflt = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    for r in train:
        w = r["source_word"]
        m = r.get("meaning_key") or r["target_word"].lower().replace(" ", "_")
        pflt.pul_terms[w] = m
        pflt.pul_terms[w.lower()] = m
    pflt._keys_sorted = sorted(pflt.pul_terms.keys(), key=len, reverse=True)

    train_closed = score(pflt, train)
    test_open = score(pflt, test)

    # Ablation: no gap-fill
    p_nofill = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=False,
    )
    for r in train:
        w = r["source_word"]
        m = r.get("meaning_key") or r["target_word"].lower().replace(" ", "_")
        p_nofill.pul_terms[w] = m
        p_nofill.pul_terms[w.lower()] = m
    p_nofill._keys_sorted = sorted(p_nofill.pul_terms.keys(), key=len, reverse=True)
    test_no_gapfill = score(p_nofill, test)

    # Zero classical baseline
    p0 = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=False,
    )
    baseline = score(p0, test)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_total": len(rows),
        "n_train": len(train),
        "n_test": len(test),
        "train_closed_set": {
            "exact_rate": train_closed["exact_rate"],
            "exact_or_partial_rate": train_closed["exact_or_partial_rate"],
            "n": train_closed["n"],
        },
        "test_open_set_with_gapfill": {
            "exact_rate": test_open["exact_rate"],
            "exact_or_partial_rate": test_open["exact_or_partial_rate"],
            "n": test_open["n"],
            "misses_sample": test_open["misses"][:15],
            "hits_sample": test_open.get("hits_sample", [])[:10],
        },
        "test_open_set_no_gapfill": {
            "exact_rate": test_no_gapfill["exact_rate"],
            "exact_or_partial_rate": test_no_gapfill["exact_or_partial_rate"],
            "n": test_no_gapfill["n"],
        },
        "test_baseline_no_classical_inject": {
            "exact_rate": baseline["exact_rate"],
            "exact_or_partial_rate": baseline["exact_or_partial_rate"],
            "n": baseline["n"],
        },
        "gapfill_lift_exact": test_open["exact_rate"] - test_no_gapfill["exact_rate"],
        "gapfill_lift_partial": (
            test_open["exact_or_partial_rate"] - test_no_gapfill["exact_or_partial_rate"]
        ),
        "interpretation": (
            "Train closed-set should stay near 1.0. "
            "Gap-fill student should lift open-set above pure miss baseline without inventing freely."
        ),
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    DRIVE.parent.mkdir(parents=True, exist_ok=True)
    DRIVE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
