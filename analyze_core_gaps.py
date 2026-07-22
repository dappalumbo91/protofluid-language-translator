#!/usr/bin/env python3
"""
Diagnose held-out CORE gap classes using dual-track-style train inject.

Outputs data/core_gap_diagnosis.json with miss taxonomy so we can fix
what the math microscope already showed: S is fine — lexicon/morph fails.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from held_out_classical import score
from meaning_clean import content_score, fold_form, is_meta_meaning
from name_gazetteer import NameGazetteer
from PFLT_FSOT_2_1_aligned import PFLT
from promote_and_train_classical import inject, is_name_record, load_all_gold, partition_core_name

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "core_gap_diagnosis.json"


def classify_miss(d: Dict[str, Any]) -> str:
    pred = " ".join(d.get("meanings") or []).lower()
    gold = (d.get("gold") or "").lower()
    word = d.get("word") or ""
    if pred in {
        "narrative_flow",
        "heritage_flow",
        "generic_dynamics",
        "fluid_resonance",
        "primordial_signal",
    } or not pred.strip():
        return "fallback_empty"
    if is_meta_meaning(pred.replace(" ", "_")) or pred.startswith("name_of_"):
        return "meta_or_name_dump"
    # mangled form-as-gloss (dek_mbrios style)
    flat = re.sub(r"[^a-z]", "", pred)
    if flat and len(flat) >= 4:
        eng = len(re.findall(r"[aeiouy]", flat))
        if eng / max(1, len(flat)) < 0.15 and "_" in pred:
            return "garbage_translit"
        if fold_form(word) and fold_form(word)[:4] in fold_form(pred):
            if content_score(pred.replace(" ", "_")) < 0.35:
                return "form_echo_gloss"
    if len(pred) > 80 or pred.count(" ") > 12:
        return "wiki_dump_long"
    # ethnonym-shaped surface
    if re.search(
        r"(ίτης|ιτης|αῖος|αιος|ικός|ικος|ηνός|ηνος|ensis|anus)$",
        fold_form(word),
        re.I,
    ) or re.search(r"^(a |an )?[A-Z]", d.get("gold") or ""):
        if any(
            x in gold
            for x in (
                "ian",
                "ean",
                "ese",
                "ite",
                "an ",
                "ic ",
            )
        ) or (d.get("gold") or "")[:1].isupper():
            return "ethnonym_missense"
    if d.get("map_rate", 0) >= 1.0:
        return "exact_wrong_sense"
    return "near_miss_or_other"


def main() -> None:
    gold = load_all_gold()
    core_all, _ = partition_core_name(gold)
    seed_keys = set()
    try:
        from core_lemma_seeds import seed_keys as _sk

        seed_keys = _sk()
    except Exception:
        pass
    train, test = [], []
    for r in core_all:
        key = f"{r.get('source_lang')}|{r.get('source_word')}"
        if key in seed_keys or r.get("source_title") == "core_lemma_seeds":
            train.append(r)
            continue
        h = int(
            hashlib.sha256(f"{r['source_lang']}:{r['source_word']}".encode()).hexdigest(),
            16,
        ) % 10000
        (train if h < 9000 else test).append(r)
    print(f"core train={len(train)} test={len(test)}", flush=True)

    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=True)
    p._name_gaz = NameGazetteer(load=False)
    print(f"pul={len(p.pul_terms)} para={len(getattr(p, 'paradigm_terms', {}) or {})}", flush=True)

    # Full core test can be ~3.6k — score all for diagnosis
    s = score(p, test, miss_cap=5000)
    print(
        f"exact={s['exact_rate']*100:.2f}% partial={s['exact_or_partial_rate']*100:.2f}% "
        f"n_miss={s['n_misses']}",
        flush=True,
    )

    tax = Counter()
    by_lang = defaultdict(Counter)
    samples: Dict[str, List] = defaultdict(list)
    for d in s.get("misses") or []:
        cls = classify_miss(d)
        tax[cls] += 1
        by_lang[d.get("lang") or "?"][cls] += 1
        if len(samples[cls]) < 8:
            samples[cls].append(
                {
                    "lang": d.get("lang"),
                    "word": d.get("word"),
                    "gold": d.get("gold"),
                    "meanings": d.get("meanings"),
                    "map_rate": d.get("map_rate"),
                }
            )

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_train": len(train),
        "n_test": len(test),
        "exact_rate": s["exact_rate"],
        "partial_rate": s["exact_or_partial_rate"],
        "n_misses": s["n_misses"],
        "taxonomy": dict(tax.most_common()),
        "by_lang": {k: dict(v) for k, v in by_lang.items()},
        "samples": {k: v for k, v in samples.items()},
        "hits_sample": s.get("hits_sample", [])[:8],
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("taxonomy:", tax.most_common(), flush=True)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
