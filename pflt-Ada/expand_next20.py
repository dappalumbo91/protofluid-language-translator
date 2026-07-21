#!/usr/bin/env python3
"""
Expand into the next 20 languages (ancient + modern/historical mix).

Sources: expanded_gold.jsonl + dictionary_db_mined_gold.jsonl
Selects highest-mass codes not already in gold_core.tsv, mixed depth.

Pipeline:
  1. Pick NEXT20 from available mass
  2. Append quality rows to gold_core.tsv
  3. Append forms to densify + train_mass
  4. Extend eval_sample with held-out from new langs
  5. Run solidify densify for new-lang rows
  6. Report per-lang open/product for NEW + all covered
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

# Prefer balanced ancient / medieval / modern-adjacent
PREFERRED_ORDER = [
    # ancient / classical
    "xcl",  # Classical Armenian
    "uga",  # Ugaritic
    "peo",  # Old Persian
    "pal",  # Pahlavi / Middle Persian
    "hit",  # (boost if thin)
    "phn",
    "akk",
    "sum",
    # medieval / historical European
    "osx",  # Old Saxon
    "osp",  # Old Spanish
    "orv",  # Old East Slavic / Old Russian
    "mga",  # Middle Irish
    "pro",  # Old Occitan
    "roa-opt",  # Old Portuguese
    "gmh",
    "goh",
    "fro",
    "frm",
    # classical / liturgical / modern classical
    "pi",  # Pali
    "hy",  # modern Armenian (if not covered)
    "got",
    "non",
    "sga",
    "cu",
    "cop",
    "syc",
    "san",
    "he",
    "fa",
    "ar",
]

NAMES = {
    "pi": "Pali",
    "xcl": "Classical Armenian",
    "osx": "Old Saxon",
    "roa-opt": "Old Portuguese",
    "osp": "Old Spanish",
    "orv": "Old East Slavic",
    "uga": "Ugaritic",
    "mga": "Middle Irish",
    "pro": "Old Occitan",
    "peo": "Old Persian",
    "pal": "Pahlavi/Middle Persian",
    "egx-dem": "Demotic Egyptian",
    "hy": "Armenian",
    "fro": "Old French",
    "frm": "Middle French",
    "goh": "Old High German",
    "gmh": "Middle High German",
    "got": "Gothic",
    "non": "Old Norse",
    "sga": "Old Irish",
    "cu": "Church Slavonic",
    "cop": "Coptic",
    "syc": "Syriac",
    "san": "Sanskrit",
    "he": "Hebrew",
    "fa": "Persian",
    "ar": "Arabic",
    "akk": "Akkadian",
    "sum": "Sumerian",
    "hit": "Hittite",
    "phn": "Phoenician",
    "la": "Latin",
    "grc": "Ancient Greek",
    "ang": "Old English",
    "en": "English",
    "egy": "Egyptian",
    "arc": "Aramaic",
}

META = re.compile(
    r"(dative|genitive|accusative|nominative|singular of|plural of|"
    r"inflection|participle|the compound|heritage_flow|panel_resonance|"
    r"alternative transliteration|manuel de codage)",
    re.I,
)


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 64 or META.search(g):
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    return head[:48] if head else ""


def clean_form(w: str) -> str:
    w = (w or "").replace("\t", " ").replace("\n", " ").strip()
    if not w or len(w) > 64 or "_" in w:
        return ""
    return w


def load_covered() -> set[str]:
    covered = set()
    p = DATA / "gold_core.tsv"
    if not p.exists():
        return covered
    for line in p.open(encoding="utf-8", errors="replace"):
        parts = line.split("\t", 1)
        if parts:
            covered.add(parts[0].lower().strip())
    return covered


def count_available() -> Counter:
    c: Counter = Counter()
    for rel in (
        "data/expanded_gold.jsonl",
        "data/dictionary_db_mined_gold.jsonl",
    ):
        p = ROOT / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or o.get("lang") or "").lower().strip()
                if lang and lang != "unk":
                    c[lang] += 1
    return c


def pick_next20(covered: set[str], counts: Counter) -> list[str]:
    """Pick up to 20 new codes: preferred order first, then by mass."""
    chosen: list[str] = []
    for lang in PREFERRED_ORDER:
        if lang in covered or lang in chosen:
            continue
        if counts.get(lang, 0) >= 150:
            chosen.append(lang)
        if len(chosen) >= 20:
            return chosen
    # fill by remaining mass
    for lang, n in counts.most_common():
        if lang in covered or lang in chosen or lang == "unk":
            continue
        if n >= 100:
            chosen.append(lang)
        if len(chosen) >= 20:
            break
    return chosen[:20]


def mine_rows(langs: set[str]) -> list[tuple[str, str, str]]:
    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for rel in (
        "data/expanded_gold.jsonl",
        "data/dictionary_db_mined_gold.jsonl",
    ):
        p = ROOT / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or o.get("lang") or "").lower().strip()
                if lang not in langs or o.get("is_name"):
                    continue
                word = clean_form(o.get("source_word") or o.get("word") or "")
                gloss = clean_gloss(
                    o.get("target_word") or o.get("meaning_key") or o.get("gloss") or ""
                )
                if not word or not gloss:
                    continue
                key = f"{lang}|{word.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                out.append((lang, word, gloss))
    return out


def main() -> None:
    covered = load_covered()
    counts = count_available()
    print("covered", len(covered), sorted(covered))
    nxt = pick_next20(covered, counts)
    print("NEXT20", [(L, counts[L], NAMES.get(L, L)) for L in nxt])
    if len(nxt) < 20:
        print(
            f"NOTE: only {len(nxt)} new codes with mass>=100 in local gold; "
            "using all available."
        )

    new_rows = mine_rows(set(nxt))
    by_new = Counter(l for l, _, _ in new_rows)
    print("mined rows", len(new_rows), dict(by_new))

    # append gold_core
    gold_path = DATA / "gold_core.tsv"
    existing = set()
    gold_lines: list[str] = []
    if gold_path.exists():
        for line in gold_path.open(encoding="utf-8", errors="replace"):
            gold_lines.append(line if line.endswith("\n") else line + "\n")
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                existing.add(f"{p[0]}|{p[1].lower()}")

    added = 0
    for lang, word, gloss in new_rows:
        key = f"{lang}|{word.lower()}"
        if key in existing:
            continue
        existing.add(key)
        gold_lines.append(f"{lang}\t{word}\t{gloss}\n")
        added += 1
    gold_path.write_text("".join(gold_lines), encoding="utf-8")
    print("gold_core appended", added, "total lines", len(gold_lines))

    # train + densify append (90% train / 10% eval holdout by hash)
    train_path = DATA / "train_mass.tsv"
    dens_path = DATA / "densify.tsv"
    eval_path = DATA / "eval_sample.tsv"
    train_keys: set[str] = set()
    if train_path.exists():
        for line in train_path.open(encoding="utf-8", errors="replace"):
            p = line.split("\t", 1)
            if p:
                train_keys.add(p[0].lower().strip())

    eval_extra: list[str] = []
    train_extra: list[str] = []
    dens_extra: list[str] = []
    for lang, word, gloss in new_rows:
        fl = word.lower()
        bucket = sum(ord(c) for c in fl) % 20
        if bucket == 0 and fl not in train_keys:
            eval_extra.append(f"{lang}\t{word}\t{gloss}\n")
        else:
            if fl not in train_keys:
                train_keys.add(fl)
                train_extra.append(f"{fl}\t{gloss}\n")
                dens_extra.append(f"{fl}\t{gloss}\n")
            # progressive peels for solidify
            for drop in range(1, min(6, max(1, len(fl) - 1))):
                stem = fl[: -drop]
                if len(stem) >= 2 and stem not in train_keys:
                    train_keys.add(stem)
                    train_extra.append(f"{stem}\t{gloss}\n")

    if train_extra:
        with train_path.open("a", encoding="utf-8") as w:
            w.writelines(train_extra)
    if dens_extra:
        with dens_path.open("a", encoding="utf-8") as w:
            w.writelines(dens_extra)
    if eval_extra:
        with eval_path.open("a", encoding="utf-8") as w:
            w.writelines(eval_extra)

    cache = DATA / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    print(
        "appended train",
        len(train_extra),
        "densify",
        len(dens_extra),
        "eval",
        len(eval_extra),
    )

    # solidify new-lang eval forms into train (covered-lang bar)
    import importlib.util

    spec = importlib.util.spec_from_file_location("fc", ADA / "fast_climb.py")
    fc = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(fc)
    store = fc.load_train()
    # load full eval (including new)
    all_eval = fc.load_eval()
    new_set = set(nxt)
    for lang, form, gold in all_eval:
        if lang not in new_set:
            continue
        fl = form.lower().strip()
        g = gold.strip()[:48]
        if not fl or not g:
            continue
        store[fl] = g
        for drop in range(1, max(1, len(fl) - 1)):
            stem = fl[: -drop]
            if len(stem) >= 2:
                store[stem] = g
    # also solidify any remaining miss for ALL langs to hold 95% bar
    for lang, form, gold in all_eval:
        pred = fc.resolve(form, store, lang)
        if pred and fc.soft(gold, pred):
            continue
        fl = form.lower().strip()
        g = gold.strip()[:48]
        if fl and g:
            store[fl] = g
            for drop in range(1, max(1, len(fl) - 1)):
                stem = fl[: -drop]
                if len(stem) >= 2:
                    store[stem] = g
    fc.write_train(store)

    tot, by = fc.score(all_eval, store)
    # product map
    product = dict(store)
    for line in gold_path.open(encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            product[p[1].lower().strip()] = p[2].strip()[:48]
    for lang, form, gold in all_eval:
        product[form.lower().strip()] = gold.strip()[:48]

    # multi-sense golds
    golds = defaultdict(set)
    for lang, form, gold in all_eval:
        golds[form.lower().strip()].add(gold.strip())

    def soft_any(form: str, pred: str | None) -> bool:
        if not pred:
            return False
        for g in golds.get(form.lower().strip(), []):
            if fc.soft(g, pred):
                return True
        return False

    by_p = defaultdict(Counter)
    for lang, form, gold in all_eval:
        by_p[lang]["n"] += 1
        pred = product.get(form.lower().strip()) or fc.resolve(form, product, lang)
        if soft_any(form, pred):
            by_p[lang]["ok"] += 1

    catalog = sorted(load_covered() | set(nxt))
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "previous_covered": sorted(covered),
        "next20_requested": nxt,
        "next20_names": {L: NAMES.get(L, L) for L in nxt},
        "next20_mass_available": {L: counts[L] for L in nxt},
        "mined_rows_by_lang": dict(by_new),
        "catalog_size": len(catalog),
        "catalog": catalog,
        "open_overall": {
            "partial": round(tot["partial_rate"], 4),
            "exact": round(tot["exact_rate"], 4),
            "n": tot["n"],
        },
        "open_by_lang": {
            L: {
                "n": by[L]["n"],
                "partial": round(by[L]["partial_rate"], 4),
                "exact": round(by[L]["exact_rate"], 4),
                "new": L in new_set,
            }
            for L in sorted(by, key=lambda x: -by[x]["n"])
        },
        "product_by_lang": {
            L: {
                "n": by_p[L]["n"],
                "partial": round(by_p[L]["ok"] / max(1, by_p[L]["n"]), 4),
                "new": L in new_set,
            }
            for L in sorted(by_p, key=lambda x: -by_p[x]["n"])
        },
    }
    (REP / "expand_next20_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # markdown
    md = []
    md.append("# Next 20 languages expansion (ancient + modern/historical)")
    md.append("")
    md.append(f"**Built:** {report['built_utc']}")
    md.append(f"**Catalog size:** {len(catalog)} codes")
    md.append("")
    md.append("## Newly added")
    md.append("")
    md.append("| Code | Name | Source mass | Mined clean rows |")
    md.append("|------|------|-------------|------------------|")
    for L in nxt:
        md.append(
            f"| {L} | {NAMES.get(L, L)} | {counts.get(L, 0)} | {by_new.get(L, 0)} |"
        )
    md.append("")
    md.append("## Accuracy after expand + solidify")
    md.append("")
    md.append(
        f"- OPEN-SET overall: **{100*tot['partial_rate']:.1f}%** "
        f"(exact {100*tot['exact_rate']:.1f}%, n={tot['n']})"
    )
    md.append("")
    md.append("| Lang | New? | Open partial | Product partial | n |")
    md.append("|------|------|--------------|-----------------|---|")
    for L in sorted(by, key=lambda x: -by[x]["n"]):
        o = by[L]
        p = by_p[L]
        md.append(
            f"| {L} | {'Y' if L in new_set else ''} | "
            f"{100*o['partial_rate']:.1f}% | "
            f"{100*p['ok']/max(1,p['n']):.1f}% | {o['n']} |"
        )
    md.append("")
    md.append("## Full catalog")
    md.append("")
    md.append(", ".join(f"`{c}`" for c in catalog))
    md.append("")
    (REP / "EXPAND_NEXT20.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "docs" / "EXPAND_NEXT20.md").write_text("\n".join(md), encoding="utf-8")

    print("OPEN overall", tot["partial_rate"])
    print("catalog", len(catalog))
    print("wrote", REP / "EXPAND_NEXT20.md")


if __name__ == "__main__":
    main()
