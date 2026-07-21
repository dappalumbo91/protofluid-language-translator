#!/usr/bin/env python3
"""Export competitive train mass for Ada product (Ada-primary path).

Builds quality-filtered packs so Ada can own form->gloss climb without
Python product runtime:

  densify.tsv      -- seeds + climb densify + classical + hieroglyph lexica
  gold_core.tsv    -- full quality gold (lang, form, gloss) for deploy store
  train_mass.tsv   -- open-set TRAIN (densify + classical + hieroglyph + ~85% gold)
  eval_sample.tsv  -- held-out forms NOT present as exact train keys

North-star: raise honest open-set partial toward 70%+ on classical/visual.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA_DATA = Path(__file__).resolve().parent / "data"

META = re.compile(
    r"(dative|genitive|accusative|nominative|vocative|ablative|"
    r"singular of|plural of|inflection|participle of|imperative of|"
    r"subjunctive|indicative|the compound|compound of|see also|"
    r"etymolog|heritage_flow|narrative_flow|generic_dynamics|"
    r"with genitive|with dative|first-person|second-person|third-person|"
    r"present tense|past tense|future tense|infinitive of|"
    r"\binfinitive\b|\bplural\b|\bsingular\b|\bparticiple\b|"
    r"\bimperative\b|\bobsolete form\b|\bdiminutive of\b|"
    r"third.person|first.person|second.person)",
    re.I,
)

# Competitive catalog: classical/visual first, then historical breadth
FOCUS_LANGS = {
    "la", "grc", "egy", "ang", "en", "ar", "cu", "cop", "arc", "akk",
    "got", "non", "sga", "san", "hit", "sum", "he", "fa", "syc", "phn",
}

SEEDS = {
    "aqua": "water",
    "manus": "hand",
    "manibus": "hand",
    "lingua": "language",
    "verbum": "word",
    "rex": "king",
    "lex": "law",
    "deus": "god",
    "templum": "temple",
    "logos": "word",
    "theos": "god",
    "zeus": "zeus",
    "temple": "temple",
    "divine": "divine",
    "soul": "soul",
    "water": "water",
    "hand": "hand",
    "hands": "hand",
    "latin": "latin",
    "mare": "sea",
    "terra": "earth",
    "caelum": "sky",
    "pax": "peace",
    "bellum": "war",
    "vita": "life",
    "mors": "death",
    "lux": "light",
    "nox": "night",
    "amor": "love",
    "fides": "faith",
    "virtus": "virtue",
    "nomen": "name",
    "urbs": "city",
    "homo": "human",
    "femina": "woman",
    "puer": "boy",
    "filius": "son",
    "pater": "father",
    "mater": "mother",
    "sol": "sun",
    "luna": "moon",
    "ignis": "fire",
    "ventus": "wind",
    "flumen": "river",
    "mons": "mountain",
    "domus": "home",
    "via": "way",
    "tempus": "time",
    "anima": "soul",
    "spiritus": "spirit",
    "sapientia": "wisdom",
    "veritas": "truth",
    "iustitia": "justice",
    "potentia": "power",
    "gloria": "glory",
    "honor": "honor",
    "corpus": "body",
    "caput": "head",
    "oculus": "eye",
    "auris": "ear",
    "os": "mouth",
    "cor": "heart",
    "pes": "foot",
    "sanguis": "blood",
    "vox": "voice",
    "liber": "book",
    "scribo": "write",
    "lego": "read",
    "dico": "say",
    "facio": "make",
    "venio": "come",
    "eo": "go",
    "sum": "be",
    "habeo": "have",
    "video": "see",
    "audio": "hear",
    "scio": "know",
    "credo": "believe",
    "amo": "love",
    "timeo": "fear",
    "do": "give",
    "accipio": "receive",
}


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 64:
        return ""
    if META.search(g):
        tail = g.split()[-1] if g.split() else ""
        tail = re.sub(r"[^a-zA-Z\-']", "", tail)
        if tail and len(tail) <= 24 and not META.search(tail):
            return tail.lower()
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    if not head or META.search(head):
        return ""
    # reject pure punctuation / digits
    if not re.search(r"[A-Za-z]", head):
        return ""
    return head[:48]


def clean_form(w: str) -> str:
    w = (w or "").replace("\t", " ").replace("\n", " ").strip()
    if not w or len(w) > 64:
        return ""
    if "\x00" in w:
        return ""
    return w


def write_pair(w, form: str, gloss: str, seen: set[str]) -> bool:
    key = form.lower()
    if key in seen:
        return False
    cg = clean_gloss(gloss)
    cf = clean_form(form)
    if not cf or not cg:
        return False
    seen.add(key)
    w.write(f"{cf}\t{cg}\n")
    return True


def load_json_lexicon(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                out[str(k)] = v
            elif isinstance(v, dict):
                g = v.get("gloss") or v.get("meaning") or v.get("en") or v.get("target")
                if isinstance(g, str):
                    out[str(k)] = g
                elif isinstance(v.get("senses"), list) and v["senses"]:
                    s0 = v["senses"][0]
                    if isinstance(s0, str):
                        out[str(k)] = s0
                    elif isinstance(s0, dict):
                        g2 = s0.get("gloss") or s0.get("en") or ""
                        if g2:
                            out[str(k)] = str(g2)
    return out


def main() -> None:
    ADA_DATA.mkdir(parents=True, exist_ok=True)
    densify_seen: set[str] = set()
    dens_n = 0

    dens_path = ADA_DATA / "densify.tsv"
    with dens_path.open("w", encoding="utf-8") as w:
        for k, v in SEEDS.items():
            if write_pair(w, k, v, densify_seen):
                dens_n += 1

        # Climb densify pack (Python factory output -- fuel only)
        dens_json = ROOT / "data" / "chew_climb" / "densify_lexicon.json"
        if dens_json.exists():
            try:
                dens = json.loads(dens_json.read_text(encoding="utf-8"))
            except Exception:
                dens = {}
            if isinstance(dens, dict):
                for k, v in dens.items():
                    if write_pair(w, str(k), str(v), densify_seen):
                        dens_n += 1

        # Classical full lexicon + dictionary mine + hieroglyph
        for rel in (
            "data/classical_full_trained_lexicon.json",
            "data/classical_grc_la_lexicon.json",
            "data/dictionary_classical_lexicon.json",
            "data/hieroglyph_pflt_lexicon.json",
            "data/domain_lexica.json",
        ):
            lex = load_json_lexicon(ROOT / rel)
            added = 0
            for k, v in lex.items():
                # domain_lexica may nest
                if write_pair(w, str(k), str(v), densify_seen):
                    dens_n += 1
                    added += 1
            print(f"lexicon {rel}: +{added} (total densify {dens_n})")

    print("densify_clean", dens_n)

    # --- gold_core: all quality focus-lang rows (no artificial small cap) ---
    gold_p = ROOT / "data" / "expanded_gold.jsonl"
    outg = ADA_DATA / "gold_core.tsv"
    gold_rows: list[tuple[str, str, str]] = []  # lang, form, gloss
    seen_gold: set[str] = set()
    skipped = 0
    raw_n = 0
    if gold_p.exists():
        with gold_p.open(encoding="utf-8") as f:
            for line in f:
                raw_n += 1
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or "").lower().strip()
                if lang not in FOCUS_LANGS or o.get("is_name"):
                    continue
                word = clean_form(o.get("source_word") or "")
                gloss = clean_gloss(
                    o.get("target_word") or o.get("meaning_key") or ""
                )
                if not word or not gloss:
                    skipped += 1
                    continue
                key = f"{lang}|{word.lower()}"
                if key in seen_gold:
                    continue
                seen_gold.add(key)
                gold_rows.append((lang, word, gloss))
    # also hieroglyph gold jsonl if present
    hgold = ROOT / "data" / "hieroglyph_unikemet_gold.jsonl"
    if hgold.exists():
        with hgold.open(encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or "egy").lower().strip() or "egy"
                word = clean_form(o.get("source_word") or o.get("form") or "")
                gloss = clean_gloss(
                    o.get("target_word") or o.get("meaning_key") or o.get("gloss") or ""
                )
                if not word or not gloss:
                    skipped += 1
                    continue
                key = f"{lang}|{word.lower()}"
                if key in seen_gold:
                    continue
                seen_gold.add(key)
                gold_rows.append((lang, word, gloss))

    with outg.open("w", encoding="utf-8") as w:
        for lang, word, gloss in gold_rows:
            w.write(f"{lang}\t{word}\t{gloss}\n")
    print(
        "gold_core_clean",
        len(gold_rows),
        "skipped_meta",
        skipped,
        "raw_lines",
        raw_n,
    )

    def latin_greek_paradigms(form: str, gloss: str) -> list[tuple[str, str]]:
        """Generate common classical / EN inflections for densify generalization."""
        f = form.lower()
        if len(f) < 3 or len(f) > 20:
            return []
        # allow unicode letters (Greek, etc.)
        if not any(ch.isalpha() for ch in f):
            return []
        out: list[tuple[str, str]] = []
        stems: list[str] = []
        if f.endswith(("ibus", "orum", "arum", "tionem", "ionem")):
            return []
        if f.endswith("us") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            for s in ("i", "um", "o", "os", "is", "orum", "e"):
                out.append((f[:-2] + s, gloss))
        elif f.endswith("um") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            for s in ("i", "a", "o", "is", "orum"):
                out.append((f[:-2] + s, gloss))
        elif f.endswith("a") and len(f) > 4 and f.isascii() and not f.endswith(("ia", "ea")):
            stems.append(f[:-1])
            for s in ("ae", "am", "as", "is", "arum"):
                out.append((f[:-1] + s, gloss))
        elif f.endswith("is") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            for s in ("i", "em", "e", "ibus"):
                out.append((f[:-2] + s, gloss))
        elif f.endswith("os") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            for s in ("ou", "on", "oi", "ous", "ois"):
                out.append((f[:-2] + s, gloss))
        elif f.endswith("on") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            for s in ("ou", "a", "ois"):
                out.append((f[:-2] + s, gloss))
        elif f.endswith("are") and len(f) > 5 and f.isascii():
            stems.append(f[:-3])
            for s in ("o", "as", "at", "amus", "atis", "ant", "avi", "atum"):
                out.append((f[:-3] + s, gloss))
        elif f.endswith("ere") and len(f) > 5 and f.isascii():
            stems.append(f[:-3])
            for s in ("o", "es", "et", "imus", "itis", "unt"):
                out.append((f[:-3] + s, gloss))
        # English light peels
        elif f.endswith("ing") and len(f) > 5 and f.isascii():
            stems.append(f[:-3])
            out.append((f[:-3], gloss))
            out.append((f[:-3] + "e", gloss))
        elif f.endswith("ed") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            out.append((f[:-2], gloss))
            out.append((f[:-2] + "e", gloss))
        elif f.endswith("es") and len(f) > 4 and f.isascii():
            stems.append(f[:-2])
            out.append((f[:-2], gloss))
        elif f.endswith("s") and len(f) > 4 and f.isascii() and not f.endswith("ss"):
            stems.append(f[:-1])
            out.append((f[:-1], gloss))
        # Greek Unicode common endings (UTF-8)
        for suf, alts in (
            ("ος", ("ου", "ον", "οι", "ους", "ων")),
            ("ης", ("η", "ην", "αι", "ας", "ων")),
            ("ον", ("ου", "α", "ων")),
            ("α", ("ας", "αν", "αι", "ων")),
            ("ον", ("ου", "οι")),
        ):
            if f.endswith(suf) and len(f) > len(suf) + 2:
                st = f[: -len(suf)]
                stems.append(st)
                for a in alts:
                    out.append((st + a, gloss))
                break
        for st in stems:
            if len(st) >= 3:
                out.append((st, gloss))
        return out

    # --- open-set split: majority gold train + densify; ~10% held-out ---
    train_keys: set[str] = set(densify_seen)
    train_path = ADA_DATA / "train_mass.tsv"
    eval_path = ADA_DATA / "eval_sample.tsv"
    train_n = 0
    eval_n = 0
    para_n = 0
    train_pairs: list[tuple[str, str]] = []  # form, gloss for paradigm expand
    eval_cands: list[tuple[str, str, str]] = []  # lang, word, gloss
    # Phase 1: split gold into train vs held-out candidates
    with train_path.open("w", encoding="utf-8") as wt:
        with dens_path.open(encoding="utf-8") as fd:
            for line in fd:
                wt.write(line)
                train_n += 1
        for lang, word, gloss in gold_rows:
            fl = word.lower()
            bucket = sum(ord(c) for c in fl) % 20
            if bucket == 0 or bucket == 1:
                if fl not in train_keys:
                    eval_cands.append((lang, word, gloss))
                    continue
            if fl not in train_keys:
                train_keys.add(fl)
                wt.write(f"{word}\t{gloss}\n")
                train_n += 1
                if lang in ("la", "grc", "ang", "egy", "en", "got", "non"):
                    train_pairs.append((fl, gloss))

        # Phase 2: paradigm densify (train only; never mark as eval)
        for form, gloss in train_pairs[:250_000]:
            for pf, pg in latin_greek_paradigms(form, gloss):
                pl = pf.lower()
                if pl in train_keys or len(pl) < 3:
                    continue
                train_keys.add(pl)
                wt.write(f"{pf}\t{pg}\n")
                train_n += 1
                para_n += 1
                if para_n >= 550_000:
                    break
            if para_n >= 550_000:
                break

    # Phase 3: honest held-out + classical-weighted sample for competitive
    # track (own classical/visual offline bar). Rare langs still included
    # but do not drown la/grc/ang/egy in the first N eval rows.
    from collections import defaultdict
    import random

    by_lang: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for lang, word, gloss in eval_cands:
        fl = word.lower()
        if fl in train_keys:
            continue
        # reject residual meta glosses on eval gold
        if gloss.lower() in {
            "plural", "singular", "infinitive", "participle",
            "imperative", "dative", "genitive", "case",
        }:
            continue
        by_lang[lang].append((lang, word, gloss))

    rng = random.Random(42)
    for L in by_lang:
        rng.shuffle(by_lang[L])

    # Target mix for competitive classical/visual product metric
    weights = {
        "la": 0.55, "grc": 0.15, "ang": 0.08, "egy": 0.05,
        "en": 0.04, "ar": 0.03, "got": 0.02, "he": 0.02,
        "cu": 0.01, "cop": 0.01, "arc": 0.01, "akk": 0.01,
        "san": 0.01, "non": 0.01,
    }
    target_n = min(20_000, sum(len(v) for v in by_lang.values()))
    mixed: list[tuple[str, str, str]] = []
    used = defaultdict(int)
    for L, w in weights.items():
        need = int(target_n * w)
        pool = by_lang.get(L, [])
        take = pool[:need]
        mixed.extend(take)
        used[L] = len(take)
    # fill remainder from largest remaining pools
    if len(mixed) < target_n:
        rest: list[tuple[str, str, str]] = []
        for L, pool in by_lang.items():
            rest.extend(pool[used[L] :])
        rng.shuffle(rest)
        mixed.extend(rest[: target_n - len(mixed)])
    rng.shuffle(mixed)

    with eval_path.open("w", encoding="utf-8") as we:
        for lang, word, gloss in mixed:
            we.write(f"{lang}\t{word}\t{gloss}\n")
            eval_n += 1

    print("train_mass_rows", train_n, "unique_train_keys", len(train_keys))
    print("paradigm_expand", para_n)
    print("eval_sample_rows", eval_n, "eval_absorbed", len(eval_cands) - eval_n)
    print("eval_langs", {L: len(v) for L, v in by_lang.items()})
    print("ADA export complete ->", ADA_DATA)


if __name__ == "__main__":
    main()
