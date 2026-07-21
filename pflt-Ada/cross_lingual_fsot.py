#!/usr/bin/env python3
"""
FSOT cross-lingual analysis + translation probe.

Uses solidified form→gloss packs under the FSOT constitution:
  S = K(T1 + T2 + T3), pin D1D38A

Reports:
  - Catalog breadth vs Google ~249 / NLLB 200 / DeepL ~30–100
  - Per-lang open/product bars (from push_universal report or live score)
  - Cross-lingual hub: EN as gloss pivot (form_L1 → gloss_en ← form_L2)
  - Shared-concept connectivity (same English gloss across languages)
  - Sample multi-source translations under FSOT framing
  - Weak spots (thin eval, low M6) and next fill plan

Writes:
  reports/CROSS_LINGUAL_FSOT.md
  reports/cross_lingual_fsot_report.json
  docs/CROSS_LINGUAL_FSOT.md
"""
from __future__ import annotations

import importlib.util
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

# Demo multi-source phrases (surface tokens → EN gloss path)
PROBES = [
    ("es", "hola mundo"),
    ("fr", "bonjour monde"),
    ("de", "hallo welt"),
    ("it", "ciao mondo"),
    ("la", "aqua lingua"),
    ("pt", "ola mundo"),
    ("nl", "hallo wereld"),
    ("ru", "привет мир"),  # may be sparse if peels fail
    ("ja", "水"),  # water
    ("zh", "水"),
    ("ar", "ماء"),  # water-ish
    ("hi", "नमस्ते"),
    ("sw", "jambo"),
    ("tr", "merhaba dünya"),
    ("pl", "cześć świecie"),
    ("ko", "안녕"),
    ("he", "שלום"),
    ("el", "γεια"),
    ("ga", "dia dhuit"),
    ("eo", "saluton mondo"),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def load_fc():
    spec = importlib.util.spec_from_file_location("fc", ADA / "fast_climb.py")
    fc = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(fc)
    return fc


def soft_any(golds: dict[str, set[str]], form: str, pred: str | None, soft) -> bool:
    if not pred:
        return False
    for g in golds.get(form.lower().strip(), set()):
        if g and soft(g, pred):
            return True
    return False


def score_catalog(fc, store, rows) -> dict:
    golds: dict[str, set[str]] = defaultdict(set)
    for lang, form, gold in rows:
        golds[form.lower().strip()].add((gold or "").strip())

    dens: dict[str, str] = {}
    dens_path = DATA / "densify.tsv"
    if dens_path.exists():
        with dens_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    dens[p[0].lower()] = p[1][:48]
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
        if soft_any(golds, form, pred_o, fc.soft):
            by_o[lang]["ok"] += 1
        if soft_any(golds, form, pred_p, fc.soft):
            by_p[lang]["ok"] += 1

    by_lang = []
    weak = []
    for L in sorted(by_o, key=lambda x: -by_o[x]["n"]):
        n = by_o[L]["n"]
        o = by_o[L]["ok"] / max(1, n)
        p = by_p[L]["ok"] / max(1, n)
        ok = (o >= 0.95 and p >= 0.95) or n < 20
        if n >= 20 and not ok:
            weak.append(L)
        by_lang.append(
            {
                "lang": L,
                "n": n,
                "open": round(100 * o, 2),
                "product": round(100 * p, 2),
                "ok": ok,
            }
        )
    o_tot = sum(by_o[L]["ok"] for L in by_o) / max(1, sum(by_o[L]["n"] for L in by_o))
    p_tot = sum(by_p[L]["ok"] for L in by_p) / max(1, sum(by_p[L]["n"] for L in by_p))
    return {
        "catalog_size": len(by_o),
        "open_overall": round(100 * o_tot, 2),
        "product_overall": round(100 * p_tot, 2),
        "weak": weak,
        "by_lang": by_lang,
        "all_ge_95": len(weak) == 0,
    }


def gloss_hub_stats(fc, store, rows, max_forms: int = 80_000) -> dict:
    """EN gloss as hub: which languages share the same English meaning key."""
    # sample from densify + eval for connectivity
    gloss_to_langs: dict[str, set[str]] = defaultdict(set)
    form_to_gloss: dict[str, str] = {}
    n = 0
    for lang, form, gold in rows:
        g = (gold or "").strip().lower()[:40]
        if not g or len(g) < 2:
            continue
        gloss_to_langs[g].add(lang)
        form_to_gloss[form.lower()] = g
        n += 1
        if n >= max_forms:
            break
    # densify also
    dens = DATA / "densify.tsv"
    if dens.exists() and n < max_forms:
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if n >= max_forms:
                    break
                p = line.rstrip("\n").split("\t")
                if len(p) < 2:
                    continue
                g = p[1].strip().lower()[:40]
                if len(g) < 2:
                    continue
                form_to_gloss[p[0].lower()] = g
                n += 1

    multi = {g: langs for g, langs in gloss_to_langs.items() if len(langs) >= 3}
    top = sorted(multi.items(), key=lambda x: -len(x[1]))[:30]
    # language pair co-occurrence via shared gloss
    pair_c: Counter = Counter()
    for g, langs in multi.items():
        L = sorted(langs)
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                pair_c[(L[i], L[j])] += 1
    top_pairs = pair_c.most_common(25)
    return {
        "gloss_keys_sampled": len(gloss_to_langs),
        "cross_lingual_glosses_ge3": len(multi),
        "top_shared_concepts": [
            {"gloss": g, "n_langs": len(langs), "langs": sorted(langs)[:20]}
            for g, langs in top
        ],
        "top_lang_pairs_via_gloss": [
            {"pair": f"{a}-{b}", "shared_concepts": c} for (a, b), c in top_pairs
        ],
    }


def translate_probe(fc, store, dens: dict[str, str], lang: str, text: str) -> dict:
    toks = [t for t in text.replace(",", " ").split() if t]
    outs = []
    mapped = 0
    for t in toks:
        fl = t.lower()
        hit = dens.get(fl) or store.get(fl) or fc.resolve(t, dens, lang) or fc.resolve(
            t, store, lang
        )
        if hit:
            outs.append(hit.split()[0])
            mapped += 1
        else:
            outs.append(f"[{t}]")
    return {
        "lang": lang,
        "src": text,
        "hyp": " ".join(outs),
        "coverage": round(mapped / max(1, len(toks)), 3),
        "mapped": mapped,
        "tokens": len(toks),
    }


def fsot_panel_note() -> dict:
    """Lightweight FSOT framing for the report (law constants; full scalar in Ada)."""
    # Same structure as product identity — not recomputing full panel here
    return {
        "formula": "S=K(T1+T2+T3)",
        "pin": "D1D38A",
        "domains": ["linguistic", "historical", "mythological", "quantum", "cosmological"],
        "note": (
            "Cross-lingual mapping is a surface of FSOT intelligence: densify "
            "knowledge without rewriting seed law. English gloss is a temporary "
            "pivot for analysis; meaning is law-grounded densify, not a cloud API."
        ),
    }


def main() -> None:
    log("=== FSOT cross-lingual analysis ===")
    fc = load_fc()
    store = fc.load_train()
    rows = fc.load_eval()
    log(f"train={len(store)} eval={len(rows)}")

    dens: dict[str, str] = {}
    dens_path = DATA / "densify.tsv"
    if dens_path.exists():
        with dens_path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    dens[p[0].lower()] = p[1][:48]
    log(f"densify={len(dens)}")

    cat = score_catalog(fc, store, rows)
    log(
        f"catalog={cat['catalog_size']} OPEN={cat['open_overall']}% "
        f"PRODUCT={cat['product_overall']}% weak={cat['weak']}"
    )

    hub = gloss_hub_stats(fc, store, rows)
    log(
        f"hub glosses={hub['gloss_keys_sampled']} "
        f"cross_ge3={hub['cross_lingual_glosses_ge3']}"
    )

    probes = [translate_probe(fc, store, dens, lang, text) for lang, text in PROBES]
    for p in probes:
        log(f"  {p['lang']:4} cov={p['coverage']:.2f} {p['src']!r} → {p['hyp']!r}")

    # M6 snippet if present
    m6 = {}
    m6p = REP / "m6_sentence_bleu_report.json"
    if m6p.exists():
        m6 = json.loads(m6p.read_text(encoding="utf-8"))
        m6 = {
            "overall": m6.get("overall"),
            "note": m6.get("honest_note") or m6.get("decoder"),
        }

    # competitor breadth
    breadth = {
        "pflt_catalog": cat["catalog_size"],
        "google_approx": 249,
        "nllb_approx": 200,
        "deepl_approx": "30–100",
        "pflt_fraction_of_google": round(cat["catalog_size"] / 249, 3),
        "pflt_fraction_of_nllb": round(cat["catalog_size"] / 200, 3),
        "toward_100": cat["catalog_size"] >= 100,
        "gap_to_100": max(0, 100 - cat["catalog_size"]),
    }

    thin = [r for r in cat["by_lang"] if r["n"] < 50]
    solid = [r for r in cat["by_lang"] if r["n"] >= 50 and r["ok"]]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "Cross-lingual analysis and translation under FSOT",
        "fsot": fsot_panel_note(),
        "catalog": cat,
        "breadth_vs_competitors": breadth,
        "gloss_hub": hub,
        "probes": probes,
        "m6_snapshot": m6,
        "solid_langs_n50": len(solid),
        "thin_langs": thin,
        "unique": (
            "Intrinsic free-parameter FSOT model — competitors have no law pin, "
            "no offline classical+visual densify stack, and no cert-gated converse "
            "under the same constitution."
        ),
        "next": [
            "Continue Kaikki to100 until catalog≥100 with all n≥50 solid",
            "Boost thin historical codes (hit/sum/syc/pal/peo)",
            "M6 CJK BPE / larger phrase mass for ja/zh",
            "Optional Ada converse smoke on multi-lang probes",
        ],
    }
    (REP / "cross_lingual_fsot_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# Cross-lingual analysis under FSOT",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Law:** `{report['fsot']['formula']}` · pin **{report['fsot']['pin']}**",
        "",
        "## Unique stack (already shipping)",
        "",
        report["unique"],
        "",
        report["fsot"]["note"],
        "",
        "## Catalog solidification",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Language codes | **{cat['catalog_size']}** |",
        f"| OPEN-SET form→gloss | **{cat['open_overall']}%** |",
        f"| PRODUCT form→gloss | **{cat['product_overall']}%** |",
        f"| All langs ≥95% (n≥20) | **{cat['all_ge_95']}** |",
        f"| Solid (n≥50 & OK) | {len(solid)} |",
        f"| Thin (n<50) | {len(thin)} |",
        f"| Gap to 100 codes | {breadth['gap_to_100']} |",
        "",
        "## Breadth vs competitors",
        "",
        f"| System | Languages (order of magnitude) |",
        f"|--------|-------------------------------:|",
        f"| Google Translate | ~{breadth['google_approx']} |",
        f"| NLLB | ~{breadth['nllb_approx']} |",
        f"| DeepL | {breadth['deepl_approx']} |",
        f"| **PFLT (FSOT)** | **{breadth['pflt_catalog']}** ({100*breadth['pflt_fraction_of_nllb']:.0f}% of NLLB, {100*breadth['pflt_fraction_of_google']:.0f}% of Google) |",
        "",
        "## English-gloss hub (cross-lingual connectivity)",
        "",
        f"- Gloss keys sampled: {hub['gloss_keys_sampled']}",
        f"- Concepts shared by ≥3 languages: **{hub['cross_lingual_glosses_ge3']}**",
        "",
        "### Top shared concepts",
        "",
        "| Gloss | # langs | Sample langs |",
        "|-------|--------:|--------------|",
    ]
    for c in hub["top_shared_concepts"][:15]:
        md.append(
            f"| {c['gloss']} | {c['n_langs']} | {', '.join(c['langs'][:12])} |"
        )
    md += [
        "",
        "### Top language pairs (via shared gloss)",
        "",
        "| Pair | Shared concepts |",
        "|------|----------------:|",
    ]
    for p in hub["top_lang_pairs_via_gloss"][:15]:
        md.append(f"| {p['pair']} | {p['shared_concepts']} |")

    md += [
        "",
        "## Multi-source translation probes (form→EN gloss path)",
        "",
        "| Lang | Coverage | Source | Hyp (EN surface) |",
        "|------|----------|--------|------------------|",
    ]
    for p in probes:
        md.append(
            f"| {p['lang']} | {p['coverage']} | {p['src']} | {p['hyp']} |"
        )

    if m6.get("overall"):
        o = m6["overall"]
        md += [
            "",
            "## M6 sentence snapshot (not parity claim)",
            "",
            f"BLEU-4 **{o.get('bleu')}** · B1 **{o.get('bleu1')}** · U-F1 **{o.get('u_f1')}** · cov **{o.get('token_coverage')}%**",
            "",
            "Climbing offline toward competitive sentence bars; law remains master.",
        ]

    md += [
        "",
        "## Thin languages (fill next)",
        "",
        "| Lang | n | Open% | Product% |",
        "|------|--:|------:|---------:|",
    ]
    for r in thin:
        md.append(f"| {r['lang']} | {r['n']} | {r['open']} | {r['product']} |")

    md += [
        "",
        "## Per-language (n≥20)",
        "",
        "| Lang | n | Open% | Product% | OK |",
        "|------|--:|------:|---------:|:--:|",
    ]
    for r in cat["by_lang"]:
        if r["n"] < 20:
            continue
        md.append(
            f"| {r['lang']} | {r['n']} | {r['open']} | {r['product']} | "
            f"{'Y' if r['ok'] else 'N'} |"
        )

    md += [
        "",
        "## Next under FSOT",
        "",
    ]
    for x in report["next"]:
        md.append(f"- {x}")
    md.append("")
    text = "\n".join(md)
    (REP / "CROSS_LINGUAL_FSOT.md").write_text(text, encoding="utf-8")
    (ADA.parent / "docs" / "CROSS_LINGUAL_FSOT.md").write_text(text, encoding="utf-8")
    log("wrote CROSS_LINGUAL_FSOT.md")


if __name__ == "__main__":
    main()
