#!/usr/bin/env python3
"""Fast open-set eval after gold/paradigm/booster upgrades."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from promote_and_train_classical import inject, load_all_gold, split_rows
from held_out_classical import score
from PFLT_FSOT_2_1_aligned import PFLT

OUT = Path(__file__).resolve().parent / "data" / "fast_open_eval_report.json"


def main() -> None:
    gold = load_all_gold()
    train, test = split_rows(gold, 0.85)
    print(f"gold={len(gold)} train={len(train)} test={len(test)}", flush=True)

    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    n = inject(p, train, expand_paradigms=True)
    print(f"injected≈{n} pul_terms={len(p.pul_terms)}", flush=True)

    # train closed sample
    tr = score(p, train[:: max(1, len(train) // 1500)][:1500])
    print(f"train_closed exact={tr['exact_rate']*100:.2f}% n={tr['n']}", flush=True)

    # full test open
    te = score(p, test)
    print(
        f"test_open exact={te['exact_rate']*100:.2f}% "
        f"partial={te['exact_or_partial_rate']*100:.2f}% n={te['n']}",
        flush=True,
    )

    by = defaultdict(list)
    for d in te.get("misses", [])[:5]:
        pass
    # per-lang via re-score groups (only large langs)
    from held_out_classical import score as sc

    by_lang = defaultdict(list)
    for r in test:
        by_lang[r["source_lang"]].append(r)
    lang_stats = {}
    for lang, rows in sorted(by_lang.items(), key=lambda x: -len(x[1])):
        if len(rows) < 30:
            continue
        s = sc(p, rows)
        lang_stats[lang] = {
            "n": s["n"],
            "exact": s["exact_rate"],
            "partial": s["exact_or_partial_rate"],
        }
        print(
            f"  {lang:5s} n={s['n']:4d} exact={s['exact_rate']*100:5.2f}% "
            f"partial={s['exact_or_partial_rate']*100:5.2f}%",
            flush=True,
        )

    # no-gap ablation on sample
    p0 = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=False,
    )
    inject(p0, train, expand_paradigms=False)
    te0 = sc(p0, test[::3][:800])
    print(
        f"ablation no_gap+no_paradigm sample n={te0['n']} "
        f"exact={te0['exact_rate']*100:.2f}% partial={te0['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_gold": len(gold),
        "n_train": len(train),
        "n_test": len(test),
        "pul_terms": len(p.pul_terms),
        "train_closed": {"exact": tr["exact_rate"], "partial": tr["exact_or_partial_rate"], "n": tr["n"]},
        "test_open": {
            "exact": te["exact_rate"],
            "partial": te["exact_or_partial_rate"],
            "n": te["n"],
            "hits_sample": te.get("hits_sample", [])[:10],
            "misses_sample": te.get("misses", [])[:10],
        },
        "by_lang": lang_stats,
        "ablation_no_gap_sample": {
            "exact": te0["exact_rate"],
            "partial": te0["exact_or_partial_rate"],
            "n": te0["n"],
        },
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
