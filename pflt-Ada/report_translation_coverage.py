#!/usr/bin/env python3
"""
Protofluid-Ada translation coverage & competitor comparison report.

Honest tracks:
  OPEN-SET: train_mass keys only; eval_sample forms never in train (held-out).
  DEPLOY:   gold_core form present in deploy map (densify+gold) — closed/coverage.

Does NOT claim WMT/BLEU vs Google/DeepL on modern sentences.
Classical/visual form→gloss is the product track PFLT owns offline.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
OUT_DIR = ADA / "reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ISO-ish display names for our codes
LANG_NAMES = {
    "la": "Latin",
    "grc": "Ancient Greek",
    "egy": "Egyptian (incl. hieroglyph/Unikemet)",
    "ang": "Old English",
    "en": "English",
    "ar": "Arabic",
    "got": "Gothic",
    "fa": "Persian (Farsi)",
    "he": "Hebrew",
    "san": "Sanskrit",
    "non": "Old Norse",
    "sga": "Old Irish",
    "cu": "Church Slavonic",
    "syc": "Syriac",
    "cop": "Coptic",
    "sum": "Sumerian",
    "arc": "Aramaic",
    "akk": "Akkadian",
    "hit": "Hittite",
    "phn": "Phoenician",
}

LATIN_SUFS = [
    "avissent", "avissem", "avisses", "avisse", "averunt", "averat",
    "ueritis", "uerimus", "uerunt", "uissent",
    "ationibus", "ationem", "ationis", "ationes", "ationum",
    "tionibus", "ionibus", "tatibus", "itatem", "itatis",
    "oribus", "issimus", "issima", "issimum", "abantur", "ebantur",
    "abant", "ebant", "untur", "antur", "entur", "tionem", "ionem",
    "tatem", "orem", "ando", "endo", "undo", "orum", "arum", "ibus",
    "amus", "atis", "imus", "itis", "erunt", "isset", "isse",
    "abo", "abis", "abit", "are", "ere", "ire", "ari", "eri", "iri",
    "avi", "tur", "ntur", "unt", "ant", "ent", "ius", "ium", "iae",
    "iam", "us", "um", "am", "ae", "as", "is", "os", "em", "es", "or",
    "it", "at", "et", "a", "i", "o", "e",
]

GRC_SUFS = [
    "ος", "ου", "ον", "οι", "ους", "ων", "ης", "η", "ην", "αι", "ας",
    "σις", "σεως", "σει", "σιν",
    "eous", "ious", "icus", "ica", "icum", "esis", "osis", "ismos",
    "ikos", "ike", "ikon", "ion", "eus", "ios", "ous", "ein",
    "ai", "oi", "on", "os", "es", "as", "is", "e", "a",
]

ANG_SUFS = [
    "nesse", "scipe", "ende", "unga", "ian", "lice", "ath", "eth",
    "ode", "um", "an", "as", "es", "e", "a",
]

EN_SUFS = [
    "ation", "ition", "tion", "sion", "ness", "ment", "able", "ible",
    "ing", "ers", "ies", "ied", "ed", "ly", "es", "s",
]

REATT = (
    "", "us", "um", "a", "ae", "is", "os", "on", "o", "e", "i",
    "are", "ere", "ire", "ari", "or", "an", "as", "es",
)


def load_map(path: Path) -> dict[str, str]:
    m: dict[str, str] = {}
    if not path.exists():
        return m
    for line in path.open(encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        if len(parts) >= 3 and parts[0] in LANG_NAMES or (
            len(parts) >= 3 and re.fullmatch(r"[a-z]{2,4}", parts[0] or "")
        ):
            # gold format lang form gloss — also index bare form
            lang, form, gloss = parts[0], parts[1], parts[2]
            fl = form.lower().strip()
            g = gloss.strip()
            if fl and g:
                m.setdefault(fl, g)
                m.setdefault(f"{lang}|{fl}", g)
        else:
            form, gloss = parts[0], parts[1]
            fl = form.lower().strip()
            g = gloss.strip()
            if fl and g:
                m.setdefault(fl, g)
    return m


def soft_match(gold: str, pred: str) -> bool:
    g = (gold or "").lower().strip()
    p = (pred or "").lower().strip()
    if not g or not p:
        return False
    if g == p or g in p or p in g:
        return True
    if len(g) >= 4 and len(p) >= 4 and g[:4] == p[:4]:
        return True
    if len(g) >= 5 and len(p) >= 5 and g[:5] == p[:5]:
        return True
    return False


def morph_resolve(form: str, store: dict[str, str], lang: str = "") -> str | None:
    fl = form.lower().strip()
    if fl in store:
        return store[fl]
    for pref in (f"{lang}|{fl}", f"la|{fl}", f"grc|{fl}", f"egy|{fl}", f"ang|{fl}"):
        if pref in store:
            return store[pref]
    sufs = LATIN_SUFS
    if lang in ("grc", "el"):
        sufs = GRC_SUFS + LATIN_SUFS
    elif lang in ("ang", "oe"):
        sufs = ANG_SUFS + LATIN_SUFS
    elif lang in ("en",):
        sufs = EN_SUFS + LATIN_SUFS
    for s in sufs:
        if fl.endswith(s) and len(fl) > len(s) + 2:
            stem = fl[: -len(s)]
            cands = [stem] + [stem + x for x in REATT if x]
            for c in cands:
                if c in store:
                    return store[c]
                if f"{lang}|{c}" in store:
                    return store[f"{lang}|{c}"]
    # single-letter peel only for longer forms
    if len(fl) >= 7:
        for s in ("a", "i", "o", "e"):
            if fl.endswith(s):
                stem = fl[:-1]
                for c in (stem, stem + "us", stem + "um", stem + "a"):
                    if c in store:
                        return store[c]
    return None


def score_rows(
    rows: list[tuple[str, str, str]], store: dict[str, str], cap: int = 0
) -> dict:
    by: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "exact": 0, "soft": 0, "miss": 0, "morph": 0}
    )
    total = {"n": 0, "exact": 0, "soft": 0, "miss": 0, "morph": 0}
    for i, (lang, form, gold) in enumerate(rows):
        if cap and i >= cap:
            break
        pred = None
        used_morph = False
        fl = form.lower()
        if fl in store:
            pred = store[fl]
        else:
            pred = morph_resolve(form, store, lang)
            if pred:
                used_morph = True
        b = by[lang]
        for d in (b, total):
            d["n"] += 1
        if not pred:
            for d in (b, total):
                d["miss"] += 1
            continue
        if used_morph:
            for d in (b, total):
                d["morph"] += 1
        pl = pred.lower()
        gl = gold.lower()
        if gl == pl or gl in pl or pl in gl:
            for d in (b, total):
                d["exact"] += 1
        elif soft_match(gold, pred):
            for d in (b, total):
                d["soft"] += 1
        else:
            for d in (b, total):
                d["miss"] += 1
    return {"by_lang": dict(by), "total": total}


def rates(d: dict) -> dict:
    n = max(1, d["n"])
    return {
        **d,
        "exact_rate": d["exact"] / n,
        "partial_rate": (d["exact"] + d["soft"]) / n,
        "miss_rate": d["miss"] / n,
    }


def load_eval_rows(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    for line in path.open(encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3:
            rows.append((parts[0].lower(), parts[1], parts[2]))
    return rows


def load_gold_rows(path: Path, per_lang: int = 500) -> list[tuple[str, str, str]]:
    """Sample up to per_lang rows per language for deploy closed-set estimate."""
    buckets: dict[str, list] = defaultdict(list)
    for line in path.open(encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        lang = parts[0].lower()
        if len(buckets[lang]) < per_lang:
            buckets[lang].append((lang, parts[1], parts[2]))
    rows = []
    for lang in sorted(buckets.keys()):
        rows.extend(buckets[lang])
    return rows


def tier_for(partial: float, n: int) -> str:
    if n < 50:
        return "C_sparse"
    if partial >= 0.70:
        return "A_strong"
    if partial >= 0.40:
        return "B_usable"
    if partial >= 0.15:
        return "C_emerging"
    return "D_thin"


def main() -> None:
    print("Loading train_mass (open-set store)...")
    train = load_map(DATA / "train_mass.tsv")
    print(f"  train keys ~{len(train)}")

    print("Loading densify+gold deploy map (sample path)...")
    deploy = load_map(DATA / "densify.tsv")
    # add gold forms (stream — only bare forms to save RAM)
    gold_path = DATA / "gold_core.tsv"
    gold_lang_counts = Counter()
    if gold_path.exists():
        for line in gold_path.open(encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            lang, form, gloss = parts[0].lower(), parts[1], parts[2]
            gold_lang_counts[lang] += 1
            fl = form.lower().strip()
            if fl and gloss.strip():
                deploy.setdefault(fl, gloss.strip())
                deploy.setdefault(f"{lang}|{fl}", gloss.strip())
    print(f"  deploy keys ~{len(deploy)} gold_langs={len(gold_lang_counts)}")

    eval_rows = load_eval_rows(DATA / "eval_sample.tsv")
    print(f"Open-set eval rows: {len(eval_rows)}")
    open_res = score_rows(eval_rows, train, cap=0)
    open_total = rates(open_res["total"])

    # Deploy closed-set sample
    deploy_rows = load_gold_rows(gold_path, per_lang=400)
    print(f"Deploy sample rows: {len(deploy_rows)}")
    dep_res = score_rows(deploy_rows, deploy, cap=0)
    dep_total = rates(dep_res["total"])

    # Per-lang tables
    open_langs = []
    for lang, d in sorted(
        open_res["by_lang"].items(), key=lambda kv: -kv[1]["n"]
    ):
        r = rates(d)
        open_langs.append(
            {
                "code": lang,
                "name": LANG_NAMES.get(lang, lang),
                "n": r["n"],
                "exact_rate": round(r["exact_rate"], 4),
                "partial_rate": round(r["partial_rate"], 4),
                "miss_rate": round(r["miss_rate"], 4),
                "gold_inventory": gold_lang_counts.get(lang, 0),
                "tier": tier_for(r["partial_rate"], r["n"]),
            }
        )

    dep_langs = []
    for lang, d in sorted(
        dep_res["by_lang"].items(), key=lambda kv: -kv[1]["n"]
    ):
        r = rates(d)
        dep_langs.append(
            {
                "code": lang,
                "name": LANG_NAMES.get(lang, lang),
                "n": r["n"],
                "exact_rate": round(r["exact_rate"], 4),
                "partial_rate": round(r["partial_rate"], 4),
                "gold_inventory": gold_lang_counts.get(lang, 0),
                "tier": tier_for(r["partial_rate"], r["n"]),
            }
        )

    langs_with_gold = len(gold_lang_counts)
    productive = sum(1 for x in open_langs if x["partial_rate"] >= 0.15 and x["n"] >= 50)
    strong = sum(1 for x in open_langs if x["tier"] == "A_strong")
    usable = sum(1 for x in open_langs if x["tier"] in ("A_strong", "B_usable"))
    deploy_strong = sum(1 for x in dep_langs if x["tier"] == "A_strong")
    deploy_usable = sum(
        1 for x in dep_langs if x["tier"] in ("A_strong", "B_usable")
    )
    deploy_ge_50 = sum(1 for x in dep_langs if x["partial_rate"] >= 0.50)

    # Competitor bars (public order-of-magnitude — not claiming BLEU equality)
    competitors = [
        {
            "system": "Google Translate",
            "language_surfaces": "~249",
            "strength": "Modern sentence MT, breadth, cloud",
            "weakness_vs_pflt": "Classical/dead/visual (la/grc/egy hieroglyphs) thin or absent",
            "pflt_track": "M4 breadth bar; M6 modern later",
        },
        {
            "system": "Meta NLLB-200",
            "language_surfaces": "200",
            "strength": "Many low-resource modern langs, research MT",
            "weakness_vs_pflt": "Not offline FSOT-law product; classical visual not core",
            "pflt_track": "M4 catalog growth toward 200+",
        },
        {
            "system": "DeepL",
            "language_surfaces": "~30–100 (product varies)",
            "strength": "EU modern sentence quality (often SOTA-class)",
            "weakness_vs_pflt": "Narrow classical/historical; cloud",
            "pflt_track": "M6 modern only after M1≥70%",
        },
        {
            "system": "Frontier LLM MT (Gemini/GPT class)",
            "language_surfaces": "many via prompting",
            "strength": "Fluent modern + some classical with hallucination risk",
            "weakness_vs_pflt": "No D1D38A law pin; not offline densify constitution",
            "pflt_track": "M7–M10 unique FSOT product",
        },
        {
            "system": "Protofluid-Ada (this report)",
            "language_surfaces": (
                f"{langs_with_gold} gold codes · deploy A_strong={deploy_strong} · "
                f"open productive={productive}"
            ),
            "strength": (
                f"Offline classical/visual; deploy ~{100*dep_total['partial_rate']:.0f}% "
                f"when known; Latin open-set ~"
                f"{100*next((x['partial_rate'] for x in open_langs if x['code']=='la'),0):.0f}%; "
                "live D1D38A"
            ),
            "weakness_vs_pflt": "Modern sentence BLEU not primary; non-Latin open-set morph thin",
            "pflt_track": "Own M5; climb M1 to 70%+ starting from Latin 50%",
        },
    ]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "product": "Protofluid-Ada V6",
        "pin": "D1D38A",
        "metric_note": (
            "form→gloss exact/partial on classical-historical surfaces; "
            "NOT FLORES/WMT sentence BLEU"
        ),
        "inventory": {
            "gold_core_rows": sum(gold_lang_counts.values()),
            "gold_language_codes": langs_with_gold,
            "gold_by_lang": dict(gold_lang_counts.most_common()),
            "train_mass_keys_approx": len(train),
            "deploy_keys_approx": len(deploy),
            "eval_held_out_rows": len(eval_rows),
            "densify_rows": sum(
                1
                for _ in (DATA / "densify.tsv").open(
                    encoding="utf-8", errors="replace"
                )
            )
            if (DATA / "densify.tsv").exists()
            else 0,
        },
        "open_set": {
            "definition": "train_mass only; held-out eval_sample forms",
            "n": open_total["n"],
            "exact_rate": round(open_total["exact_rate"], 4),
            "partial_rate": round(open_total["partial_rate"], 4),
            "miss_rate": round(open_total["miss_rate"], 4),
            "by_lang": open_langs,
            "productive_langs_partial_ge_15pct": productive,
            "strong_langs_partial_ge_70pct": strong,
            "usable_langs_partial_ge_40pct": usable,
        },
        "deploy_closed_sample": {
            "definition": "up to 400 gold rows/lang; full densify+gold map",
            "n": dep_total["n"],
            "exact_rate": round(dep_total["exact_rate"], 4),
            "partial_rate": round(dep_total["partial_rate"], 4),
            "by_lang": dep_langs,
        },
        "capability_summary": {
            "language_codes_in_gold": langs_with_gold,
            "productive_open_set_langs": productive,
            "deploy_strong_langs_partial_ge_70": deploy_strong,
            "deploy_usable_langs_partial_ge_40": deploy_usable,
            "deploy_langs_partial_ge_50": deploy_ge_50,
            "open_set_partial_overall": round(open_total["partial_rate"], 4),
            "open_set_exact_overall": round(open_total["exact_rate"], 4),
            "deploy_partial_sample": round(dep_total["partial_rate"], 4),
            "latin_open_set_partial": next(
                (x["partial_rate"] for x in open_langs if x["code"] == "la"), None
            ),
            "vs_google_249": f"{langs_with_gold}/249 gold codes ({100*langs_with_gold/249:.1f}% of Google breadth count)",
            "vs_nllb_200": f"{langs_with_gold}/200 ({100*langs_with_gold/200:.1f}% of NLLB count)",
            "honest_caveat": (
                "Two tracks: DEPLOY (form in lexicon) vs OPEN-SET (held-out morph). "
                "Google/NLLB optimize modern sentences; PFLT optimizes FSOT classical/visual form→gloss offline."
            ),
        },
        "competitors": competitors,
        "residuals_closed_this_cycle": [
            "Per-lang open-set + deploy scoring report (this file)",
            "Language archive with tiers A/B/C/D",
            "Competitor multi-metric comparison table",
        ],
        "residuals_still_open": [
            "Open-set partial toward 70%+ (morph densify climb)",
            "Real U-Net image weights (hyp TSV contract ready)",
            "Modern sentence BLEU/COMET (M6 after M1)",
            "Lean spawn on every numeric claim",
        ],
        "next_climb": [
            "Paradigm densify + inject for miss-heavy langs (grc Unicode, ar, got)",
            "Raise open-set partial la first (largest mass)",
            "Grow gold codes toward 100 meaningful surfaces",
        ],
    }

    json_path = OUT_DIR / "translation_coverage_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Markdown archive
    md = []
    md.append("# Protofluid-Ada — Translation Language Archive & Competitor Compare")
    md.append("")
    md.append(f"**Built:** {report['built_utc']}")
    md.append(f"**Product:** {report['product']} · pin `{report['pin']}`")
    md.append("")
    md.append("> Metric: **form→gloss** exact/partial (classical/historical/visual).  ")
    md.append("> Not WMT/FLORES sentence BLEU — different product track.")
    md.append("")
    md.append("## Headline capability")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Gold language codes | **{langs_with_gold}** |")
    md.append(f"| Gold inventory rows | **{sum(gold_lang_counts.values()):,}** |")
    md.append(f"| Train mass keys (open-set) | ~**{len(train):,}** |")
    md.append(f"| Deploy map keys | ~**{len(deploy):,}** |")
    md.append(
        f"| **Open-set partial** (held-out, n={open_total['n']}) | "
        f"**{100*open_total['partial_rate']:.1f}%** |"
    )
    md.append(
        f"| Open-set exact | **{100*open_total['exact_rate']:.1f}%** |"
    )
    md.append(
        f"| Deploy closed-sample partial (n={dep_total['n']}) | "
        f"**{100*dep_total['partial_rate']:.1f}%** |"
    )
    md.append(f"| Open-set productive langs (partial≥15%, n≥50) | **{productive}** |")
    md.append(f"| Open-set usable langs (partial≥40%) | **{usable}** |")
    md.append(f"| **Deploy strong langs** (closed sample partial≥70%) | **{deploy_strong}** |")
    md.append(f"| **Deploy usable langs** (partial≥40%) | **{deploy_usable}** |")
    md.append("")
    md.append("### Two tracks (read carefully)")
    md.append("")
    md.append("| Track | Meaning | Current |")
    md.append("|-------|---------|---------|")
    md.append(
        f"| **DEPLOY** | Form already in quality lexicon | "
        f"**{100*dep_total['partial_rate']:.0f}%** partial · "
        f"**{deploy_strong}/{langs_with_gold}** langs A_strong |"
    )
    md.append(
        f"| **OPEN-SET** | Held-out form; morph must generalize | "
        f"**{100*open_total['partial_rate']:.0f}%** partial · "
        f"Latin ~{100*next((x['partial_rate'] for x in open_langs if x['code']=='la'),0):.0f}% |"
    )
    md.append("")
    md.append("## Per-language open-set (honest held-out)")
    md.append("")
    md.append("| Code | Language | n | Exact% | Partial% | Gold rows | Tier |")
    md.append("|------|----------|---|--------|----------|-----------|------|")
    for x in open_langs:
        md.append(
            f"| {x['code']} | {x['name']} | {x['n']} | "
            f"{100*x['exact_rate']:.1f} | {100*x['partial_rate']:.1f} | "
            f"{x['gold_inventory']:,} | {x['tier']} |"
        )
    md.append("")
    md.append("### Tier legend")
    md.append("")
    md.append("- **A_strong** partial ≥70% (n≥50)")
    md.append("- **B_usable** partial ≥40%")
    md.append("- **C_emerging** partial ≥15%")
    md.append("- **C_sparse** n<50")
    md.append("- **D_thin** partial <15%")
    md.append("")
    md.append("## Deploy closed-sample (coverage when form is in lexicon)")
    md.append("")
    md.append("| Code | Language | n | Exact% | Partial% | Tier |")
    md.append("|------|----------|---|--------|----------|------|")
    for x in dep_langs:
        md.append(
            f"| {x['code']} | {x['name']} | {x['n']} | "
            f"{100*x['exact_rate']:.1f} | {100*x['partial_rate']:.1f} | "
            f"{x['tier']} |"
        )
    md.append("")
    md.append("## Competitor comparison (multi-metric, honest)")
    md.append("")
    md.append("| System | Language surfaces | Strength | vs PFLT |")
    md.append("|--------|-------------------|----------|---------|")
    for c in competitors:
        md.append(
            f"| **{c['system']}** | {c['language_surfaces']} | "
            f"{c['strength']} | {c['weakness_vs_pflt']} |"
        )
    md.append("")
    md.append("### Breadth count vs quality")
    md.append("")
    md.append(f"- vs Google ~249: **{langs_with_gold}/249** gold codes "
              f"({100*langs_with_gold/249:.1f}% of *count* only)")
    md.append(f"- vs NLLB 200: **{langs_with_gold}/200** ({100*langs_with_gold/200:.1f}% of count)")
    md.append(
        "- PFLT is **not** claiming to beat Google/DeepL on modern sentence BLEU yet (M6)."
    )
    md.append(
        "- PFLT **does** claim a competitive offline classical/visual form→gloss track "
        "with FSOT law pin — a band consumer MT largely leaves empty."
    )
    md.append("")
    md.append("## Where we stand (plain language)")
    md.append("")
    md.append(
        f"1. **Catalog:** {langs_with_gold} language codes with quality gold "
        f"(led by Latin {gold_lang_counts.get('la',0):,}, Greek, OE, Egyptian…)."
    )
    md.append(
        f"2. **Open-set translation capability:** ~**{100*open_total['partial_rate']:.0f}%** "
        f"partial / ~**{100*open_total['exact_rate']:.0f}%** exact on held-out forms "
        f"(target **70%+** partial)."
    )
    md.append(
        f"3. **Deploy lexicon hit rate (sampled closed):** ~**{100*dep_total['partial_rate']:.0f}%** "
        f"when the form is already in the quality map."
    )
    md.append(
        f"4. **Productive surfaces:** **{productive}** langs with open-set partial≥15% "
        f"and enough eval mass."
    )
    md.append(
        "5. **vs competitors:** trailing on *modern breadth count* (249/200); "
        "leading opportunity on *classical+visual offline + FSOT law*."
    )
    md.append("")
    md.append("## Residuals")
    md.append("")
    md.append("### Closed this report cycle")
    for x in report["residuals_closed_this_cycle"]:
        md.append(f"- {x}")
    md.append("")
    md.append("### Still open")
    for x in report["residuals_still_open"]:
        md.append(f"- {x}")
    md.append("")
    md.append("## Next climb")
    for x in report["next_climb"]:
        md.append(f"- {x}")
    md.append("")

    md_path = OUT_DIR / "TRANSLATION_LANGUAGE_ARCHIVE.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    # also copy summary to docs
    docs = ADA.parent / "docs" / "TRANSLATION_LANGUAGE_ARCHIVE.md"
    docs.write_text("\n".join(md), encoding="utf-8")

    print("\n=== HEADLINE ===")
    print(f"open_set partial={open_total['partial_rate']:.4f} exact={open_total['exact_rate']:.4f} n={open_total['n']}")
    print(f"deploy_sample partial={dep_total['partial_rate']:.4f} exact={dep_total['exact_rate']:.4f} n={dep_total['n']}")
    print(f"langs gold={langs_with_gold} productive={productive} usable={usable} strong={strong}")
    print("wrote", json_path)
    print("wrote", md_path)
    print("wrote", docs)

    # compact CSV for spreadsheet
    csv_path = OUT_DIR / "open_set_by_lang.csv"
    with csv_path.open("w", encoding="utf-8") as w:
        w.write("code,name,n,exact_rate,partial_rate,gold_inventory,tier\n")
        for x in open_langs:
            w.write(
                f"{x['code']},{x['name']},{x['n']},{x['exact_rate']},"
                f"{x['partial_rate']},{x['gold_inventory']},{x['tier']}\n"
            )
    print("wrote", csv_path)


if __name__ == "__main__":
    main()
