#!/usr/bin/env python3
"""Lightweight smoke: core held-out miss math microscope (no full dual_track)."""
from __future__ import annotations

import hashlib

from held_out_classical import attach_core_miss_microscope, score
from name_gazetteer import NameGazetteer
from PFLT_FSOT_2_1_aligned import PFLT
from promote_and_train_classical import inject, load_all_gold, partition_core_name


def main() -> None:
    gold = load_all_gold()
    core_all, _ = partition_core_name(gold)
    train, test = [], []
    for r in core_all:
        h = int(
            hashlib.sha256(f"{r['source_lang']}:{r['source_word']}".encode()).hexdigest(),
            16,
        ) % 10000
        (train if h < 9000 else test).append(r)
    train = train[:800]
    test = test[:200]
    print(f"core train={len(train)} test={len(test)}", flush=True)

    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=False)
    p._name_gaz = NameGazetteer(load=False)

    s = score(p, test, miss_cap=40)
    print(
        f"exact={s['exact_rate']*100:.1f}% partial={s['exact_or_partial_rate']*100:.1f}% "
        f"n_miss={s['n_misses']}",
        flush=True,
    )
    idx = attach_core_miss_microscope(s["misses"], max_n=15, track="core_held_out_smoke")
    print("traced", idx["n_traced"], "by_domain", idx["by_domain"], flush=True)
    print("index", idx["index_path"], flush=True)
    if idx.get("samples"):
        sm = idx["samples"][0]
        print(
            "sample",
            sm.get("word"),
            "S",
            sm.get("S"),
            "T1",
            sm.get("T1"),
            "log",
            sm.get("math_log"),
            flush=True,
        )


if __name__ == "__main__":
    main()
