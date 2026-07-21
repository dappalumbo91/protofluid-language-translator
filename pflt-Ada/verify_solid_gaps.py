#!/usr/bin/env python3
"""Verify no thin langs remain and report open/product on former gaps."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
TARGETS = ["hit", "pal", "pro", "mga", "osp", "orv", "roa-opt", "uga"]


def main() -> None:
    c: Counter = Counter()
    with (DATA / "eval_sample.tsv").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                c[p[0]] += 1
    thin = sorted((L, n) for L, n in c.items() if n < 50)
    border = sorted((L, n) for L, n in c.items() if 50 <= n < 100)
    print(f"langs={len(c)} rows={sum(c.values())}", flush=True)
    print(f"thin n<50: {thin}", flush=True)
    print(f"border 50-99: {border}", flush=True)
    print(f"targets: {{{', '.join(f'{L}:{c[L]}' for L in TARGETS)}}}", flush=True)

    spec = importlib.util.spec_from_file_location("fc", ADA / "fast_climb.py")
    fc = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(fc)
    store = fc.load_train()
    rows = fc.load_eval()
    golds: dict[str, set[str]] = defaultdict(set)
    for lang, form, gold in rows:
        golds[form.lower().strip()].add((gold or "").strip())
    dens: dict[str, str] = {}
    with (DATA / "densify.tsv").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                dens[p[0].lower()] = p[1][:48]
    product = dict(dens)
    for k, v in store.items():
        product.setdefault(k, v)

    by: dict[str, Counter] = defaultdict(Counter)
    for lang, form, gold in rows:
        fl = form.lower().strip()
        by[lang]["n"] += 1
        pred_o = store.get(fl) or fc.resolve(form, store, lang)
        pred_p = product.get(fl) or fc.resolve(form, product, lang)

        def ok(pred: str | None) -> bool:
            if not pred:
                return False
            for g in golds[fl]:
                if g and fc.soft(g, pred):
                    return True
            return False

        if ok(pred_o):
            by[lang]["o"] += 1
        if ok(pred_p):
            by[lang]["p"] += 1

    o_tot = sum(by[L]["o"] for L in by) / max(1, sum(by[L]["n"] for L in by))
    p_tot = sum(by[L]["p"] for L in by) / max(1, sum(by[L]["n"] for L in by))
    weak = [
        L
        for L in by
        if by[L]["n"] >= 20
        and (by[L]["o"] / by[L]["n"] < 0.95 or by[L]["p"] / by[L]["n"] < 0.95)
    ]
    print(
        f"OVERALL OPEN={100*o_tot:.2f}% PRODUCT={100*p_tot:.2f}% "
        f"langs={len(by)} weak={weak}",
        flush=True,
    )
    print("--- former thin targets ---", flush=True)
    for L in TARGETS:
        n = by[L]["n"]
        o = 100 * by[L]["o"] / max(1, n)
        p = 100 * by[L]["p"] / max(1, n)
        flag = "OK" if n >= 50 and o >= 95 and p >= 95 else "GAP"
        print(f"{flag} {L:8} n={n:4} open={o:5.1f}% prod={p:5.1f}%", flush=True)

    solid = sum(1 for L in by if by[L]["n"] >= 50 and by[L]["o"] / by[L]["n"] >= 0.95)
    report = {
        "langs": len(by),
        "open_overall": round(100 * o_tot, 2),
        "product_overall": round(100 * p_tot, 2),
        "thin_n_lt_50": thin,
        "border_50_99": border,
        "solid_n50_ge95_open": solid,
        "weak": weak,
        "targets": {
            L: {
                "n": by[L]["n"],
                "open": round(100 * by[L]["o"] / max(1, by[L]["n"]), 2),
                "product": round(100 * by[L]["p"] / max(1, by[L]["n"]), 2),
            }
            for L in TARGETS
        },
        "ready_for_hf_packaging": len(thin) == 0 and len(weak) == 0,
    }
    (REP / "gap_fill_verify.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(f"wrote {REP / 'gap_fill_verify.json'}", flush=True)
    print(f"ready_for_hf_packaging={report['ready_for_hf_packaging']}", flush=True)


if __name__ == "__main__":
    main()
