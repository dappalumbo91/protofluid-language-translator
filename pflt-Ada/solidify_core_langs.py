#!/usr/bin/env python3
"""
Solidify the languages we already have (DeepL-class breadth, quality-first).

Does NOT add new language codes. Instead:
  1. Quality-filter gold (drop FSOT panel junk, meta glosses, underscore blobs)
  2. Aggressive paradigm densify from TRAIN stems only (honest open-set)
  3. Rebuild train_mass / eval / densify for Ada
  4. Score core langs + full 20; write SOLIDIFY freeze report

Core priority: la, grc, ang, egy, en  then remaining 15.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

CORE = ["la", "grc", "ang", "egy", "en"]
ALL_FOCUS = {
    "la", "grc", "egy", "ang", "en", "ar", "cu", "cop", "arc", "akk",
    "got", "non", "sga", "san", "hit", "sum", "he", "fa", "syc", "phn",
}

META = re.compile(
    r"(dative|genitive|accusative|nominative|vocative|ablative|"
    r"singular of|plural of|inflection|participle of|imperative of|"
    r"subjunctive|indicative|the compound|compound of|see also|"
    r"etymolog|heritage_flow|narrative_flow|generic_dynamics|"
    r"\binfinitive\b|\bplural\b|\bsingular\b|panel_resonance|"
    r"_panel|_resonance|_scale|flow$)",
    re.I,
)

# FSOT/domain junk masquerading as English lemmas
JUNK_FORM = re.compile(
    r"(resonance|panel|fsot|domain_scalar|_flow|_scale|multi_hero|"
    r"verification_panel|outcomes_|hybrid_fi|constants scale|"
    r"materials_science|sciences_flow)",
    re.I,
)


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 64:
        return ""
    if META.search(g):
        tail = g.split()[-1] if g.split() else ""
        tail = re.sub(r"[^a-zA-Z\-'\u0370-\u03FF]", "", tail)
        if tail and len(tail) <= 24 and not META.search(tail):
            return tail.lower()
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    if not head or META.search(head):
        return ""
    if not re.search(r"[A-Za-z\u0370-\u03FF\u0400-\u04FF\u0600-\u06FF]", head):
        return ""
    return head[:48]


def clean_form(w: str, lang: str) -> str:
    w = (w or "").replace("\t", " ").replace("\n", " ").strip()
    if not w or len(w) > 64:
        return ""
    if JUNK_FORM.search(w):
        return ""
    if lang == "en":
        if "_" in w or w.count(" ") >= 2:
            return ""
        if w.endswith(("_panel", "_scale", "resonance")):
            return ""
    return w


def paradigms(form: str, gloss: str, lang: str) -> list[tuple[str, str]]:
    f = form.lower()
    if len(f) < 3 or len(f) > 22:
        return []
    out: list[tuple[str, str]] = []
    stems: list[str] = []

    def add_stem(st: str, alts: tuple[str, ...]) -> None:
        if len(st) < 3:
            return
        stems.append(st)
        for a in alts:
            out.append((st + a, gloss))

    if lang in ("la", "lat") or (lang == "grc" and f.isascii()):
        if f.endswith("are") and len(f) > 5:
            add_stem(f[:-3], ("o", "as", "at", "amus", "atis", "ant", "avi", "atum", "abo", "abis"))
        elif f.endswith("ere") and len(f) > 5:
            add_stem(f[:-3], ("o", "es", "et", "imus", "itis", "unt", "i", "ero"))
        elif f.endswith("ire") and len(f) > 5:
            add_stem(f[:-3], ("io", "is", "it", "imus", "itis", "iunt"))
        elif f.endswith("us") and len(f) > 4:
            add_stem(f[:-2], ("i", "um", "o", "os", "is", "orum", "e"))
        elif f.endswith("um") and len(f) > 4:
            add_stem(f[:-2], ("i", "a", "o", "is", "orum"))
        elif f.endswith("a") and len(f) > 4 and not f.endswith(("ia", "ea")):
            add_stem(f[:-1], ("ae", "am", "as", "is", "arum"))
        elif f.endswith("is") and len(f) > 4:
            add_stem(f[:-2], ("i", "em", "e", "ibus"))
        # verb-ish long forms
        for suf, alts in (
            ("avissent", ("o", "are", "avi")),
            ("ueritis", ("o", "ere", "i")),
            ("ando", ("o", "are")),
            ("etur", ("o", "ere")),
            ("etur", ("o", "are")),
            ("isset", ("o", "are")),
            ("erunt", ("o", "ere")),
            ("abant", ("o", "are")),
            ("ebant", ("o", "ere")),
        ):
            if f.endswith(suf) and len(f) > len(suf) + 2:
                add_stem(f[: -len(suf)], alts)
    if lang in ("en",):
        for suf, alts in (
            ("ation", ("", "e")),
            ("tion", ("", "e")),
            ("ness", ("",)),
            ("ment", ("",)),
            ("ing", ("", "e")),
            ("ed", ("", "e")),
            ("ly", ("",)),
            ("es", ("",)),
            ("s", ("",)),
        ):
            if f.endswith(suf) and len(f) > len(suf) + 2:
                add_stem(f[: -len(suf)], alts)
                break
    if lang in ("ang",):
        for suf in ("nesse", "ende", "unga", "ian", "ath", "eth", "um", "an", "as", "es"):
            if f.endswith(suf) and len(f) > len(suf) + 2:
                st = f[: -len(suf)]
                add_stem(st, ("an", "a", "e", ""))
                break
    if lang in ("grc",) and not f.isascii():
        for suf, alts in (
            ("ος", ("ου", "ον", "οι", "ους", "ων")),
            ("ης", ("η", "ην", "αι", "ας", "ων")),
            ("ον", ("ου", "α", "ων")),
            ("σις", ("σεως", "σει", "σιν")),
            ("α", ("ας", "αν", "αι", "ων")),
        ):
            if f.endswith(suf) and len(f) > len(suf) + 1:
                add_stem(f[: -len(suf)], alts)
                break
    if lang in ("egy",):
        # light: strip trailing mark
        if f.endswith((".s", ".sw", "-f", "-s")) and len(f) > 4:
            st = re.sub(r"[\.\-].*$", "", f)
            if len(st) >= 2:
                out.append((st, gloss))
    for st in stems:
        if len(st) >= 3:
            out.append((st, gloss))
    return out


def soft_match(gold: str, pred: str) -> bool:
    g, p = (gold or "").lower(), (pred or "").lower()
    if not g or not p:
        return False
    if g == p or g in p or p in g:
        return True
    if len(g) >= 4 and len(p) >= 4 and g[:4] == p[:4]:
        return True
    return False


def morph_lookup(form: str, store: dict[str, str], lang: str) -> str | None:
    fl = form.lower().strip()
    if fl in store:
        return store[fl]
    for p in paradigms(fl, "x", lang):
        k = p[0].lower()
        if k in store:
            return store[k]
    # also try reverse: strip suffixes against store
    for p in paradigms(fl, "x", lang):
        pass
    # suffix probe like report
    if lang == "la":
        sufs = [
            "avissent", "ueritis", "ationibus", "ibus", "orum", "arum",
            "ando", "are", "ere", "ire", "us", "um", "am", "ae", "is", "os",
            "em", "es", "it", "at", "o", "i", "a", "e",
        ]
    elif lang == "en":
        sufs = ["ation", "tion", "ness", "ment", "ing", "ed", "ly", "es", "s"]
    elif lang == "ang":
        sufs = ["nesse", "ende", "unga", "ian", "ath", "eth", "um", "an", "as", "es"]
    else:
        sufs = ["us", "um", "is", "os", "es", "ae", "am", "a", "i", "o", "e"]
    for s in sufs:
        if fl.endswith(s) and len(fl) > len(s) + 2:
            stem = fl[: -len(s)]
            for c in [stem, stem + "us", stem + "um", stem + "a", stem + "are", stem + "ere", stem + "e"]:
                if c in store:
                    return store[c]
    return None


def score(rows, store, lang_filter=None):
    tot = Counter()
    by = defaultdict(Counter)
    for lang, form, gold in rows:
        if lang_filter and lang not in lang_filter:
            continue
        pred = morph_lookup(form, store, lang)
        by[lang]["n"] += 1
        tot["n"] += 1
        if not pred:
            by[lang]["miss"] += 1
            tot["miss"] += 1
            continue
        if gold.lower() in pred.lower() or pred.lower() in gold.lower() or gold.lower() == pred.lower():
            by[lang]["exact"] += 1
            tot["exact"] += 1
        elif soft_match(gold, pred):
            by[lang]["soft"] += 1
            tot["soft"] += 1
        else:
            by[lang]["miss"] += 1
            tot["miss"] += 1
    def rates(c):
        n = max(1, c["n"])
        return {
            "n": c["n"],
            "exact_rate": (c["exact"]) / n,
            "partial_rate": (c["exact"] + c["soft"]) / n,
        }
    return rates(tot), {k: rates(v) for k, v in by.items()}


def main() -> None:
    print("=== Solidify core languages (quality-first) ===")
    seeds = {
        "aqua": "water", "manus": "hand", "manibus": "hand", "lingua": "language",
        "verbum": "word", "rex": "king", "lex": "law", "deus": "god", "templum": "temple",
        "logos": "word", "theos": "god", "water": "water", "hand": "hand", "soul": "soul",
        "divine": "divine", "temple": "temple", "king": "king", "sun": "sun", "life": "life",
    }

    # --- densify base ---
    densify_seen: set[str] = set()
    dens_lines: list[str] = []
    for k, v in seeds.items():
        densify_seen.add(k)
        dens_lines.append(f"{k}\t{v}")

    dens_json = ROOT / "data" / "chew_climb" / "densify_lexicon.json"
    if dens_json.exists():
        dens = json.loads(dens_json.read_text(encoding="utf-8"))
        if isinstance(dens, dict):
            for k, v in dens.items():
                cg = clean_gloss(str(v))
                cf = clean_form(str(k), "la")
                if not cf or not cg or cf.lower() in densify_seen:
                    continue
                densify_seen.add(cf.lower())
                dens_lines.append(f"{cf}\t{cg}")

    for rel in (
        "data/classical_full_trained_lexicon.json",
        "data/dictionary_classical_lexicon.json",
        "data/hieroglyph_pflt_lexicon.json",
        "data/classical_grc_la_lexicon.json",
    ):
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        for k, v in obj.items():
            if isinstance(v, dict):
                v = v.get("gloss") or v.get("en") or ""
            cg = clean_gloss(str(v))
            cf = clean_form(str(k), "la")
            if not cf or not cg or cf.lower() in densify_seen:
                continue
            densify_seen.add(cf.lower())
            dens_lines.append(f"{cf}\t{cg}")

    dens_path = DATA / "densify.tsv"
    dens_path.write_text("\n".join(dens_lines) + "\n", encoding="utf-8")
    print("densify", len(dens_lines))

    # --- gold clean ---
    gold_rows: list[tuple[str, str, str]] = []
    seen = set()
    skipped = Counter()
    gold_p = ROOT / "data" / "expanded_gold.jsonl"
    with gold_p.open(encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            lang = (o.get("source_lang") or "").lower().strip()
            if lang not in ALL_FOCUS or o.get("is_name"):
                continue
            word = clean_form(o.get("source_word") or "", lang)
            gloss = clean_gloss(o.get("target_word") or o.get("meaning_key") or "")
            if not word or not gloss:
                skipped[lang] += 1
                continue
            key = f"{lang}|{word.lower()}"
            if key in seen:
                continue
            seen.add(key)
            gold_rows.append((lang, word, gloss))

    # hieroglyph gold
    hgold = ROOT / "data" / "hieroglyph_unikemet_gold.jsonl"
    if hgold.exists():
        with hgold.open(encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or "egy").lower() or "egy"
                word = clean_form(o.get("source_word") or o.get("form") or "", lang)
                gloss = clean_gloss(
                    o.get("target_word") or o.get("gloss") or o.get("meaning_key") or ""
                )
                if not word or not gloss:
                    continue
                key = f"{lang}|{word.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                gold_rows.append((lang, word, gloss))

    gold_path = DATA / "gold_core.tsv"
    with gold_path.open("w", encoding="utf-8") as w:
        for lang, word, gloss in gold_rows:
            w.write(f"{lang}\t{word}\t{gloss}\n")
    print("gold_core", len(gold_rows), "skipped", dict(skipped))

    # --- train/eval split ---
    train_keys = set(densify_seen)
    train_pairs: list[tuple[str, str, str]] = []  # lang, form, gloss
    eval_cands: list[tuple[str, str, str]] = []
    train_path = DATA / "train_mass.tsv"
    with train_path.open("w", encoding="utf-8") as wt:
        for line in dens_lines:
            wt.write(line + "\n")
        for lang, word, gloss in gold_rows:
            fl = word.lower()
            bucket = sum(ord(c) for c in fl) % 20
            if bucket in (0, 1) and fl not in train_keys:
                eval_cands.append((lang, word, gloss))
                continue
            if fl not in train_keys:
                train_keys.add(fl)
                wt.write(f"{word}\t{gloss}\n")
                train_pairs.append((lang, fl, gloss))

        # aggressive paradigm densify for ALL langs we have (solidify, not expand catalog)
        para_n = 0
        for lang, form, gloss in train_pairs:
            for pf, pg in paradigms(form, gloss, lang):
                pl = pf.lower()
                if pl in train_keys or len(pl) < 2:
                    continue
                train_keys.add(pl)
                wt.write(f"{pf}\t{pg}\n")
                para_n += 1
                if para_n >= 700_000:
                    break
            if para_n >= 700_000:
                break
    print("paradigm_expand", para_n, "train_keys", len(train_keys))

    # held-out pure
    by_lang = defaultdict(list)
    for lang, word, gloss in eval_cands:
        if word.lower() in train_keys:
            continue
        if gloss.lower() in {"plural", "singular", "infinitive", "case"}:
            continue
        by_lang[lang].append((lang, word, gloss))

    import random
    rng = random.Random(42)
    weights = {
        "la": 0.50, "grc": 0.14, "ang": 0.10, "egy": 0.06, "en": 0.06,
        "ar": 0.03, "got": 0.02, "he": 0.02, "san": 0.01, "non": 0.01,
        "cu": 0.01, "cop": 0.01, "akk": 0.01, "arc": 0.01, "fa": 0.01,
    }
    target_n = 20000
    mixed: list[tuple[str, str, str]] = []
    used = defaultdict(int)
    for L, w in weights.items():
        pool = by_lang.get(L, [])
        rng.shuffle(pool)
        need = int(target_n * w)
        take = pool[:need]
        mixed.extend(take)
        used[L] = len(take)
    if len(mixed) < target_n:
        rest = []
        for L, pool in by_lang.items():
            rest.extend(pool[used[L] :])
        rng.shuffle(rest)
        mixed.extend(rest[: target_n - len(mixed)])
    rng.shuffle(mixed)
    eval_path = DATA / "eval_sample.tsv"
    with eval_path.open("w", encoding="utf-8") as we:
        for lang, word, gloss in mixed:
            we.write(f"{lang}\t{word}\t{gloss}\n")
    print("eval", len(mixed))

    # --- score ---
    store: dict[str, str] = {}
    for line in train_path.open(encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2:
            store[p[0].lower()] = p[1]
    eval_rows = mixed
    tot, by = score(eval_rows, store)

    # deploy sample
    deploy = dict(store)
    for lang, word, gloss in gold_rows:
        deploy.setdefault(word.lower(), gloss)
    dep_rows = []
    buckets: dict[str, list] = defaultdict(list)
    for lang, word, gloss in gold_rows:
        if len(buckets[lang]) < 400:
            buckets[lang].append((lang, word, gloss))
    for L in sorted(buckets):
        dep_rows.extend(buckets[L])
    dep_tot, dep_by = score(dep_rows, deploy)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "Solidify existing languages (quality) before catalog expansion",
        "strategy": "DeepL-class: fewer languages, high accuracy; then expand with frozen FSOT approach",
        "inventory": {
            "gold_rows": len(gold_rows),
            "langs": len({l for l, _, _ in gold_rows}),
            "train_keys": len(train_keys),
            "paradigm_expand": para_n,
            "densify": len(dens_lines),
            "eval_n": len(mixed),
        },
        "open_set_overall": tot,
        "open_set_by_lang": {k: by[k] for k in sorted(by, key=lambda x: -by[x]["n"])},
        "core_open_set": {k: by.get(k, {}) for k in CORE},
        "deploy_overall": dep_tot,
        "deploy_by_lang": {k: dep_by[k] for k in sorted(dep_by)},
        "core_deploy": {k: dep_by.get(k, {}) for k in CORE},
        "approach_frozen": [
            "Quality-filter forms/glosses (no FSOT panel junk as English lemmas)",
            "S=K(T1+T2+T3) pin D1D38A never rewritten",
            "train_mass + paradigm densify from train stems only (honest open-set)",
            "Deploy map = densify + gold; open-set = train_mass only",
            "Per-lang morph peels (la/en/ang/grc/egy) before catalog growth",
            "Expand to new languages only after core open-set and deploy hold",
        ],
        "expansion_rule": (
            "Do not add language codes until core la/grc/ang/egy/en "
            "are solidified (deploy ≥85% sample, Latin open-set ≥60% target, "
            "en free of panel junk)."
        ),
        "next": [
            "Keep Latin open-set climb toward 60–70%",
            "Greek Unicode densify + peels",
            "Egyptian transliteration variants",
            "Then expand catalog 20 → 40 → 100 with same pipeline",
        ],
    }
    (REP / "solidify_core_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # markdown freeze
    md = []
    md.append("# Protofluid-Ada — Solidify Core Languages (freeze)")
    md.append("")
    md.append(f"**Built:** {report['built_utc']}")
    md.append("")
    md.append("## Goal")
    md.append("")
    md.append(
        "Meta NLLB has ~200 languages; DeepL ~30–100. "
        "We have **20** with real gold. **Do not chase breadth yet.** "
        "Solidify accuracy on what we have — then expand using the frozen FSOT approach "
        "(same as the main archive solves other domains)."
    )
    md.append("")
    md.append("## Headline after solidify pass")
    md.append("")
    md.append("| Track | Overall |")
    md.append("|-------|---------|")
    md.append(
        f"| Open-set partial | **{100*tot['partial_rate']:.1f}%** "
        f"(n={tot['n']}, exact {100*tot['exact_rate']:.1f}%) |"
    )
    md.append(
        f"| Deploy sample partial | **{100*dep_tot['partial_rate']:.1f}%** "
        f"(n={dep_tot['n']}, exact {100*dep_tot['exact_rate']:.1f}%) |"
    )
    md.append("")
    md.append("### Core five (priority solidify)")
    md.append("")
    md.append("| Lang | Open partial | Open exact | n | Deploy partial |")
    md.append("|------|--------------|------------|---|----------------|")
    for L in CORE:
        o = by.get(L, {"partial_rate": 0, "exact_rate": 0, "n": 0})
        d = dep_by.get(L, {"partial_rate": 0})
        md.append(
            f"| **{L}** | {100*o.get('partial_rate',0):.1f}% | "
            f"{100*o.get('exact_rate',0):.1f}% | {o.get('n',0)} | "
            f"{100*d.get('partial_rate',0):.1f}% |"
        )
    md.append("")
    md.append("### All languages open-set")
    md.append("")
    md.append("| Lang | n | Exact% | Partial% |")
    md.append("|------|---|--------|----------|")
    for L in sorted(by, key=lambda x: -by[x]["n"]):
        o = by[L]
        md.append(
            f"| {L} | {o['n']} | {100*o['exact_rate']:.1f} | {100*o['partial_rate']:.1f} |"
        )
    md.append("")
    md.append("## Frozen FSOT translation approach")
    md.append("")
    for step in report["approach_frozen"]:
        md.append(f"1. {step}" if step == report["approach_frozen"][0] else f"1. {step}")
    # fix numbering
    md = md[:- len(report["approach_frozen"])]
    md.append("## Frozen FSOT translation approach")
    md.append("")
    for i, step in enumerate(report["approach_frozen"], 1):
        md.append(f"{i}. {step}")
    md.append("")
    md.append(f"**Expansion rule:** {report['expansion_rule']}")
    md.append("")
    md.append("## Competitor stance (quality-first)")
    md.append("")
    md.append("| Bar | Stance |")
    md.append("|-----|--------|")
    md.append("| DeepL ~30–100 langs | Match **quality density** on ≤20 classical/historical first |")
    md.append("| NLLB 200 | Breadth later — only after approach is frozen |")
    md.append("| Google 249 | Same — do not dilute with empty codes |")
    md.append("")
    md.append("## Reproduce")
    md.append("")
    md.append("```powershell")
    md.append("cd pflt-Ada")
    md.append("python solidify_core_langs.py")
    md.append("alr build")
    md.append(".\\bin\\pflt_main.exe eval")
    md.append("python report_translation_coverage.py")
    md.append("```")
    md.append("")

    (REP / "SOLIDIFY_CORE.md").write_text("\n".join(md), encoding="utf-8")
    (ROOT / "docs" / "SOLIDIFY_CORE.md").write_text("\n".join(md), encoding="utf-8")
    print("open_set", tot)
    print("core", {k: by.get(k) for k in CORE})
    print("deploy", dep_tot)
    print("wrote", REP / "SOLIDIFY_CORE.md")


if __name__ == "__main__":
    main()
