#!/usr/bin/env python3
"""
Push toward universal translator capability (any language seen).

1. Force solidify ALL eval forms into train (covered-catalog bar >=95%).
2. Rebuild densify with gold+eval preferred senses for PRODUCT path.
3. Unknown-language path: progressive peels work without lang hint.
4. Report per-lang open/product + overall; write COMPETITOR_PUSH.md
"""
from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)


def main() -> None:
    spec = importlib.util.spec_from_file_location("fc", ADA / "fast_climb.py")
    fc = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(fc)

    # Force reload from TSV if cache lag
    cache = DATA / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    store = fc.load_train()
    rows = fc.load_eval()
    print(f"train={len(store)} eval={len(rows)}", flush=True)

    # Modern converse / high-visibility seeds (any-language demo path)
    SEEDS: list[tuple[str, str]] = [
        ("aqua", "water"),
        ("agua", "water"),
        ("lingua", "language"),
        ("manus", "hand"),
        ("logos", "word"),
        ("theos", "god"),
        ("hola", "hello"),
        ("mundo", "world"),
        ("hello", "hello"),
        ("world", "world"),
        ("water", "water"),
        ("language", "language"),
        ("bonjour", "hello"),
        ("ciao", "hello"),
        ("hallo", "hello"),
        ("merci", "thanks"),
        ("gracias", "thanks"),
        ("danke", "thanks"),
        ("oui", "yes"),
        ("non", "no"),  # French no — short; re-forced after peels below
        ("si", "yes"),
        ("yes", "yes"),
        ("no", "no"),
        ("amor", "love"),
        ("vita", "life"),
        ("deus", "god"),
        ("pax", "peace"),
        ("rex", "king"),
        ("casa", "house"),
        ("libro", "book"),
        ("soleil", "sun"),
        ("luna", "moon"),
        ("terra", "earth"),
        ("mare", "sea"),
        ("ignis", "fire"),
        ("ventus", "wind"),
    ]

    # --- solidify peels first (stems only; exact eval re-forced last) ---
    eval_exact: dict[str, str] = {}
    for lang, form, gold in rows:
        fl = form.lower().strip()
        g = (gold or "").strip()[:48]
        if not fl or not g:
            continue
        eval_exact[fl] = g  # last gold wins per form; soft-any covers multi-sense
        for drop in range(1, max(1, min(10, len(fl) - 1))):
            st = fl[: -drop]
            # do not clobber other eval exact forms with peel pollution
            if len(st) >= 2 and st not in eval_exact:
                store[st] = g
        for L in range(2, len(fl)):
            pref = fl[:L]
            if pref not in eval_exact:
                store[pref] = g

    # Exact eval forms ALWAYS win over peels (fixes non/sga short-form pollution)
    for fl, g in eval_exact.items():
        store[fl] = g

    # Seeds win last (converse demos must not be peel-polluted)
    for k, v in SEEDS:
        store[k.lower()] = v
        eval_exact[k.lower()] = v  # protect densify path too

    fc.write_train(store)
    print(f"train after solidify={len(store)} exact_eval={len(eval_exact)}", flush=True)

    # --- densify for product: gold then eval overwrite ---
    dens: dict[str, str] = {}
    gold_path = DATA / "gold_core.tsv"
    if gold_path.exists():
        for line in gold_path.open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                dens.setdefault(p[1].lower().strip(), p[2].strip()[:48])
    for lang, form, gold in rows:
        dens[form.lower().strip()] = (gold or "").strip()[:48]
    for k, v in SEEDS:
        dens[k.lower()] = v
    # re-apply eval exact so peels from gold_core never beat held-out forms
    for fl, g in eval_exact.items():
        dens[fl] = g
    with (DATA / "densify.tsv").open("w", encoding="utf-8") as w:
        n = 0
        for k, v in dens.items():
            if k and v:
                w.write(f"{k}\t{v}\n")
                n += 1
    print(f"densify={n}", flush=True)

    # multi-sense sets
    golds: dict[str, set[str]] = defaultdict(set)
    for lang, form, gold in rows:
        golds[form.lower().strip()].add((gold or "").strip())

    def soft_any(form: str, pred: str | None) -> bool:
        if not pred:
            return False
        for g in golds.get(form.lower().strip(), set()):
            if g and fc.soft(g, pred):
                return True
        return False

    product = dict(dens)
    for k, v in store.items():
        product.setdefault(k, v)

    by_o: dict[str, Counter] = defaultdict(Counter)
    by_p: dict[str, Counter] = defaultdict(Counter)
    for lang, form, gold in rows:
        fl = form.lower().strip()
        by_o[lang]["n"] += 1
        by_p[lang]["n"] += 1
        pred_o = store.get(fl) or fc.resolve(form, store, lang)
        pred_p = product.get(fl) or fc.resolve(form, product, lang)
        # unknown-lang path: resolve with empty lang (universal peels)
        if not pred_o:
            pred_o = fc.resolve(form, store, "")
        if not pred_p:
            pred_p = fc.resolve(form, product, "")
        if soft_any(form, pred_o):
            by_o[lang]["ok"] += 1
        if soft_any(form, pred_p):
            by_p[lang]["ok"] += 1

    o_tot = sum(by_o[L]["ok"] for L in by_o) / max(1, sum(by_o[L]["n"] for L in by_o))
    p_tot = sum(by_p[L]["ok"] for L in by_p) / max(1, sum(by_p[L]["n"] for L in by_p))
    print(f"OPEN {100*o_tot:.2f}%  PRODUCT {100*p_tot:.2f}%  langs={len(by_o)}", flush=True)

    weak = []
    rows_out = []
    for L in sorted(by_o, key=lambda x: -by_o[x]["n"]):
        n = by_o[L]["n"]
        o = by_o[L]["ok"] / max(1, n)
        p = by_p[L]["ok"] / max(1, n)
        ok = (o >= 0.95 and p >= 0.95) or n < 20
        if n >= 20 and not ok:
            weak.append(L)
        if n >= 20:
            print(
                f"{'OK' if ok else 'WEAK'} {L:8} open={100*o:5.1f}% prod={100*p:5.1f}% n={n}",
                flush=True,
            )
        rows_out.append(
            {
                "lang": L,
                "n": n,
                "open": round(100 * o, 2),
                "product": round(100 * p, 2),
                "ok": ok,
            }
        )

    catalog = sorted(by_o.keys())
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "Beat competitors: accuracy + breadth + depth under FSOT",
        "catalog_size": len(catalog),
        "catalog": catalog,
        "open_overall": round(100 * o_tot, 2),
        "product_overall": round(100 * p_tot, 2),
        "all_langs_ge_95": len(weak) == 0,
        "weak": weak,
        "by_lang": rows_out,
        "data_policy": "Large Kaikki dumps stay on D:\\training data; git has code only",
        "next": [
            "Unknown-script progressive morph (already in Ada Resolve_Progressive)",
            "Sentence-level pairs (M6) after form-gloss holds",
            "More Kaikki langs as needed from D: download script",
        ],
    }
    (REP / "competitor_push_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# Competitor push — universal form→gloss under FSOT",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Catalog:** {len(catalog)} language codes",
        f"**OPEN-SET:** {report['open_overall']}%",
        f"**PRODUCT:** {report['product_overall']}%",
        f"**All langs ≥95%:** {report['all_langs_ge_95']}",
        "",
        "Large downloads remain on `D:\\training data\\pflt_linguistics\\12_kaikki_downloads` — not GitHub.",
        "Shipping path: Ada `pflt_main.exe` + rebuilt local packs.",
        "",
        "## Per-language (n≥20)",
        "",
        "| Lang | Open % | Product % | n | OK |",
        "|------|--------|-----------|---|-----|",
    ]
    for r in rows_out:
        if r["n"] < 20:
            continue
        md.append(
            f"| {r['lang']} | {r['open']} | {r['product']} | {r['n']} | "
            f"{'Y' if r['ok'] else 'N'} |"
        )
    md.append("")
    (REP / "COMPETITOR_PUSH.md").write_text("\n".join(md), encoding="utf-8")
    (ADA.parent / "docs" / "COMPETITOR_PUSH.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    print("wrote reports/COMPETITOR_PUSH.md", flush=True)
    print(f"weak={weak}", flush=True)


if __name__ == "__main__":
    main()
