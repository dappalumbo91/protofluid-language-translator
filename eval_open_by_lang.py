#!/usr/bin/env python3
import hashlib
from collections import defaultdict

from promote_and_train_classical import inject, load_all_gold
from held_out_classical import score
from PFLT_FSOT_2_1_aligned import PFLT


def main() -> None:
    gold = load_all_gold()
    train, test = [], []
    for r in gold:
        h = int(
            hashlib.sha256(f"{r['source_lang']}:{r['source_word']}".encode()).hexdigest(),
            16,
        ) % 10000
        (train if h < 9000 else test).append(r)
    print(f"90/10 train={len(train)} test={len(test)}")
    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train)
    by = defaultdict(list)
    for r in test:
        by[r["source_lang"]].append(r)
    for lang, rows in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(rows) < 20:
            continue
        s = score(p, rows)
        print(
            f"{lang:5s} n={len(rows):4d} "
            f"exact={s['exact_rate']*100:5.2f}% "
            f"partial={s['exact_or_partial_rate']*100:5.2f}%"
        )
    s = score(p, test)
    print(
        f"ALL   n={len(test):4d} "
        f"exact={s['exact_rate']*100:5.2f}% "
        f"partial={s['exact_or_partial_rate']*100:5.2f}%"
    )


if __name__ == "__main__":
    main()
