#!/usr/bin/env python3
"""
A) Mine densify wrong-sense pairs → form_sense_prefer + Ada lexicon seeds.

Sources:
  - core_lemma_seeds CORE_SEEDS (gold)
  - lang_tables form_sense_prefer (gold)
  - sense_interlingua UNIVERSAL_LABELS (gold)
  - compare densify/gold_core lookups when they disagree with gold

Writes:
  - data/lang_tables/la.json (merge prefer)
  - data/wrong_sense_mined.json (report)
  - pflt-Ada/data/sense_prefer.tsv (form\\tgloss for inject)
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
ADA = ROOT / "pflt-Ada" / "data"
TABLES = ROOT / "data" / "lang_tables"
OUT_JSON = ROOT / "data" / "wrong_sense_mined.json"
OUT_TSV = ADA / "sense_prefer.tsv"

# Glosses that are almost always wrong for core nouns (densify pollution)
BAN_SUBSTR = (
    "dative",
    "genitive",
    "accusative",
    "nominative",
    "participle",
    "subjunctive",
    "indicative",
    "inflection",
    "etymolog",
    "see also",
    "the compound",
    "unresolved",
    "narrative_flow",
    "generic_dynamics",
    "primordial",
    "astronomy",  # sol drift
    "annihilation",  # mors drift
)


def fold(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def is_bad_gloss(g: str) -> bool:
    gl = fold(g)
    if not gl or len(gl) > 48:
        return True
    return any(b in gl for b in BAN_SUBSTR)


def soft_ok(pred: str, gold: str) -> bool:
    p, g = fold(pred), fold(gold)
    if not p or not g:
        return False
    if p == g or g in p or p in g:
        return True
    # shared stem
    if len(g) >= 4 and len(p) >= 4 and p[:4] == g[:4]:
        return True
    return False


def load_gold_pairs() -> Dict[str, str]:
    """form_lower -> preferred english gloss (first wins)."""
    gold: Dict[str, str] = {}
    # core seeds
    try:
        from core_lemma_seeds import CORE_SEEDS

        for lang, form, gloss in CORE_SEEDS:
            if lang not in ("la", "grc", "en"):
                continue
            gold.setdefault(fold(form), fold(gloss).replace(" ", "_") if False else fold(gloss))
    except Exception:
        pass
    # lang tables
    for name in ("la.json", "grc.json", "en.json"):
        p = TABLES / name
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for form, senses in (data.get("form_sense_prefer") or {}).items():
            if isinstance(senses, list) and senses:
                gold.setdefault(fold(form), fold(str(senses[0])))
        for seed in data.get("seeds") or []:
            if isinstance(seed, dict) and seed.get("form") and seed.get("gloss"):
                gold.setdefault(fold(seed["form"]), fold(seed["gloss"]))
    # universal labels from sense_interlingua
    try:
        from sense_interlingua import UNIVERSAL_LABELS

        for gloss_en, by_lang in UNIVERSAL_LABELS.items():
            for lang, forms in by_lang.items():
                for form in forms:
                    gold.setdefault(fold(form), fold(gloss_en))
    except Exception:
        pass
    # explicit high-priority fixes
    forced = {
        "sol": "sun",
        "solem": "sun",
        "mater": "mother",
        "matrem": "mother",
        "mors": "death",
        "mortem": "death",
        "pater": "father",
        "patrem": "father",
        "aqua": "water",
        "manus": "hand",
        "lingua": "language",
        "domus": "house",
        "luna": "moon",
        "terra": "earth",
        "vita": "life",
        "ignis": "fire",
        "mare": "sea",
        "caelum": "sky",
        "urbs": "city",
        "bellum": "war",
        "pax": "peace",
        "deus": "god",
        "dea": "goddess",
        "rex": "king",
        "lex": "law",
        "homo": "man",
        "mulier": "woman",
        "puer": "boy",
        "filius": "son",
        "filia": "daughter",
        "dies": "day",
        "nox": "night",
        "annus": "year",
        "tempus": "time",
        "nomen": "name",
        "verbum": "word",
        "locus": "place",
        "via": "road",
        "cor": "heart",
        "sanguis": "blood",
        "oculus": "eye",
        "pes": "foot",
        "caput": "head",
        "corpus": "body",
        "vox": "voice",
        "flumen": "river",
        "mons": "mountain",
        "amicus": "friend",
        "hostis": "enemy",
        "populus": "people",
        "amor": "love",
        "templum": "temple",
        "casa": "house",  # la: house (not densify cottage/verb drift)
        "via": "road",
        "pes": "foot",
        "homo": "man",
        "corpus": "body",
        "filia": "daughter",
        "anima": "soul",
        "terra": "earth",
        "gramma": "letter",
        "vis": "force",
        "magister": "master",
        "agricultura": "agriculture",
    }
    gold.update(forced)
    return gold


def scan_densify(
    gold: Dict[str, str], max_lines: int = 3_000_000
) -> Tuple[List[dict], Counter]:
    """Find densify/gold rows where form is in gold but gloss disagrees."""
    mismatches: List[dict] = []
    counts: Counter = Counter()
    for name in ("densify.tsv", "gold_core.tsv"):
        path = ADA / name
        if not path.exists():
            continue
        n = 0
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                if n >= max_lines:
                    break
                n += 1
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3 and len(parts[0]) <= 8:
                    form, gloss = parts[1], parts[2]
                elif len(parts) >= 2:
                    form, gloss = parts[0], parts[1]
                else:
                    continue
                fl = fold(form)
                if fl not in gold:
                    continue
                g = gold[fl]
                pred = fold(gloss)
                if soft_ok(pred, g):
                    counts["ok"] += 1
                    continue
                if is_bad_gloss(pred) or not soft_ok(pred, g):
                    counts["mismatch"] += 1
                    mismatches.append(
                        {
                            "form": fl,
                            "gold": g,
                            "densify_pred": pred[:80],
                            "source": name,
                        }
                    )
    return mismatches, counts


def merge_la_prefer(gold: Dict[str, str], mismatches: List[dict]) -> int:
    path = TABLES / "la.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"lang": "la"}
    prefer = data.setdefault("form_sense_prefer", {})
    added = 0
    # all gold la-looking forms
    forms = {m["form"] for m in mismatches}
    forms.update(gold.keys())
    for form in sorted(forms):
        g = gold.get(form)
        if not g:
            continue
        # only latin-ish ascii for la table (skip greek)
        if re.search(r"[α-ωΑ-Ω]", form):
            continue
        cur = prefer.get(form) or []
        if not isinstance(cur, list):
            cur = [cur]
        if not cur or fold(str(cur[0])) != fold(g):
            prefer[form] = [g] + [c for c in cur if fold(str(c)) != fold(g)]
            added += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return added


def write_prefer_tsv(gold: Dict[str, str], mismatches: List[dict]) -> int:
    # unique form->gold, prioritize mismatched forms first
    order = []
    seen = set()
    for m in mismatches:
        f = m["form"]
        if f not in seen and f in gold:
            seen.add(f)
            order.append(f)
    for f in gold:
        if f not in seen:
            seen.add(f)
            order.append(f)
    lines = []
    for f in order:
        # skip greek forms in ada prefer tsv if needed - keep all
        lines.append(f"{f}\t{gold[f]}")
    OUT_TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main() -> None:
    print("=== Mine wrong-sense densify pairs ===", flush=True)
    gold = load_gold_pairs()
    print(f"gold forms={len(gold)}", flush=True)
    mismatches, counts = scan_densify(gold)
    # unique worst forms
    by_form = defaultdict(list)
    for m in mismatches:
        by_form[m["form"]].append(m["densify_pred"])
    top = sorted(
        ((f, Counter(preds).most_common(3)) for f, preds in by_form.items()),
        key=lambda x: -sum(c for _, c in x[1]),
    )[:40]
    print("mismatch counts", dict(counts), "unique forms", len(by_form), flush=True)
    print("top wrong forms:", flush=True)
    for f, preds in top[:15]:
        print(f"  {f} gold={gold.get(f)} densify={preds}", flush=True)

    added = merge_la_prefer(gold, mismatches)
    n_tsv = write_prefer_tsv(gold, mismatches)
    rep = {
        "gold_n": len(gold),
        "scan_counts": dict(counts),
        "mismatch_unique_forms": len(by_form),
        "la_prefer_updated": added,
        "sense_prefer_tsv_rows": n_tsv,
        "top_wrong": [
            {"form": f, "gold": gold.get(f), "densify_top": preds} for f, preds in top[:30]
        ],
    }
    OUT_JSON.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"updated la prefer entries~{added}", flush=True)
    print(f"WROTE {OUT_TSV} rows={n_tsv}", flush=True)
    print(f"WROTE {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
