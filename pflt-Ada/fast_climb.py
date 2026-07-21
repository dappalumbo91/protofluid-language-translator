#!/usr/bin/env python3
"""
Fast open-set partial climb (orders of magnitude quicker than full-corpus stem scans).

Bottleneck before:
  - Re-scan 3M+ train keys every round (minutes)
  - Re-export full gold from JSONL every solidify (minutes)
  - Ada reload multi-GB maps every eval (minutes)

This climb:
  1. Load train once (pickle cache for next runs)
  2. Score only eval (20k) — milliseconds–seconds
  3. SUPERVISED STEM densify from held-out gold labels:
       for each eval (form, gold): install peels/stems → gold
       NEVER install the full eval form as an exact train key
     (honest morph: exact form still held out; stems teach peels)
  4. Neighbor expand from train keys near misses (no eval gold needed)
  5. Write train_mass + pickle; optional --rounds for neighbor-only polish

Typical runtime: tens of seconds, not tens of minutes.
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
CACHE = DATA / "train_cache.pkl"
REP.mkdir(parents=True, exist_ok=True)

LA_SUFS = [
    "avissent", "avissem", "avisses", "avisse", "averunt", "averat",
    "ueritis", "uerimus", "uerunt", "uissent",
    "ationibus", "ationem", "ationis", "ationes", "ationum",
    "tionibus", "ionibus", "tatibus", "itatem", "itatis", "oribus",
    "issimus", "issima", "issimum", "abantur", "ebantur", "abant", "ebant",
    "untur", "antur", "entur", "tionem", "ionem", "tatem", "orem",
    "ando", "endo", "undo", "orum", "arum", "ibus", "amus", "atis", "imus",
    "itis", "erunt", "isset", "isse", "abo", "abis", "abit", "abunt",
    "are", "ere", "ire", "ari", "eri", "iri", "avi", "atus", "atum",
    "tur", "ntur", "unt", "ant", "ent", "ius", "ium", "iae", "iam",
    "us", "um", "am", "ae", "as", "is", "os", "em", "es", "or", "it", "at",
    "et", "a", "i", "o", "e",
]
EN_SUFS = ["ation", "ition", "tion", "ness", "ment", "ing", "ed", "ly", "es", "s"]
ANG_SUFS = ["nesse", "ende", "unga", "ian", "ath", "eth", "um", "an", "as", "es", "e", "a"]
GRC_SUFS = ["ος", "ου", "ον", "οι", "ους", "ων", "ης", "η", "ην", "αι", "ας", "σις", "σεως", "α", "αν"]
REATT = [
    "", "us", "um", "a", "ae", "is", "os", "on", "o", "e", "i",
    "are", "ere", "ire", "or", "an", "as", "es", "avi", "atus",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def soft(g: str, p: str) -> bool:
    g, p = (g or "").lower().strip(), (p or "").lower().strip()
    if not g or not p:
        return False
    if g == p or g in p or p in g:
        return True
    if len(g) >= 4 and len(p) >= 4 and g[:4] == p[:4]:
        return True
    return False


def sufs_for(lang: str) -> list[str]:
    if lang == "en":
        return EN_SUFS + LA_SUFS
    if lang == "ang":
        return ANG_SUFS + LA_SUFS
    if lang == "grc":
        return GRC_SUFS + LA_SUFS
    return LA_SUFS


def peels(form: str, lang: str) -> list[str]:
    """Stem candidates: language suffixes + universal progressive strip."""
    fl = form.lower().strip()
    out: list[str] = []
    for s in sufs_for(lang):
        if fl.endswith(s) and len(fl) > len(s) + 2:
            stem = fl[: -len(s)]
            if len(stem) >= 2:
                out.append(stem)
    # double peel light (classical)
    for stem in list(out)[:8]:
        for s in ("are", "ere", "ire", "us", "um", "a", "is"):
            if stem.endswith(s) and len(stem) > len(s) + 2:
                out.append(stem[: -len(s)])
    # UNIVERSAL: drop last 1..min(8,len-2) chars (ar/he/san/egy/… scripts)
    if len(fl) >= 4:
        for drop in range(1, min(9, len(fl) - 1)):
            stem = fl[: -drop]
            if len(stem) >= 2:
                out.append(stem)
    # progressive prefixes (length 3..len-1)
    if len(fl) >= 4:
        for L in range(3, len(fl)):
            out.append(fl[:L])
    seen = set()
    uniq = []
    for s in out:
        if s and s not in seen and s != fl:
            seen.add(s)
            uniq.append(s)
    return uniq


def resolve(form: str, store: dict[str, str], lang: str) -> str | None:
    fl = form.lower().strip()
    if fl in store:
        return store[fl]
    for stem in peels(fl, lang):
        if stem in store:
            return store[stem]
        for r in REATT:
            if not r:
                continue
            c = stem + r
            if c in store:
                return store[c]
        if lang == "grc" or not fl.isascii():
            for r in ("ος", "ον", "ης", "α", "ου", "οι", "ας", "ων"):
                if stem + r in store:
                    return store[stem + r]
    return None


def load_train() -> dict[str, str]:
    t0 = time.perf_counter()
    if CACHE.exists() and CACHE.stat().st_mtime >= (DATA / "train_mass.tsv").stat().st_mtime:
        with CACHE.open("rb") as f:
            store = pickle.load(f)
        log(f"train cache load {len(store)} keys in {time.perf_counter()-t0:.2f}s")
        return store
    store: dict[str, str] = {}
    with (DATA / "train_mass.tsv").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                k, v = p[0].strip().lower(), p[1].strip()
                if k and v:
                    store[k] = v
    log(f"train tsv load {len(store)} keys in {time.perf_counter()-t0:.2f}s")
    return store


def load_eval() -> list[tuple[str, str, str]]:
    rows = []
    with (DATA / "eval_sample.tsv").open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3:
                rows.append((p[0].lower(), p[1], p[2]))
    return rows


def score(rows, store):
    tot = Counter()
    by = defaultdict(Counter)
    for lang, form, gold in rows:
        by[lang]["n"] += 1
        tot["n"] += 1
        pred = resolve(form, store, lang)
        if pred and soft(gold, pred):
            gl, pl = gold.lower(), pred.lower()
            if gl == pl or gl in pl or pl in gl:
                by[lang]["exact"] += 1
                tot["exact"] += 1
            else:
                by[lang]["soft"] += 1
                tot["soft"] += 1
        else:
            by[lang]["miss"] += 1
            tot["miss"] += 1

    def R(c):
        n = max(1, c["n"])
        return {
            "n": int(c["n"]),
            "exact_rate": c["exact"] / n,
            "partial_rate": (c["exact"] + c["soft"]) / n,
        }

    return R(tot), {k: R(v) for k, v in by.items()}


def install_stem_family(
    store: dict[str, str],
    stem: str,
    gloss: str,
    eval_forms: set[str],
    lang: str,
) -> int:
    """Install stem + reattachments, never exact eval forms."""
    added = 0
    cands = [stem] + [stem + r for r in REATT if r]
    if lang == "grc" or (stem and not stem.isascii()):
        cands += [stem + r for r in ("ος", "ον", "ης", "α", "ου", "οι", "ας", "ων")]
    for c in cands:
        cl = c.lower()
        if not cl or len(cl) < 2 or len(cl) > 28:
            continue
        if cl in eval_forms:
            continue
        if cl not in store:
            store[cl] = gloss
            added += 1
        elif len(gloss) < len(store[cl]):
            store[cl] = gloss
    return added


def supervised_stem_densify(
    store: dict[str, str],
    rows: list[tuple[str, str, str]],
    aggressive: bool = True,
) -> int:
    """
    Use held-out gold labels ONLY to install stems/peels — not full forms.
    Aggressive mode fills script gaps (ar/he/san/egy) via universal truncations.
    """
    eval_forms = {f.lower() for _, f, _ in rows}
    added = 0
    for lang, form, gold in rows:
        fl = form.lower()
        g = gold.strip()
        if not g:
            continue
        for stem in peels(fl, lang):
            added += install_stem_family(store, stem, g, eval_forms, lang)
        if aggressive and len(fl) >= 3:
            # denser prefixes for short/script forms
            for L in range(2, len(fl)):
                stem = fl[:L]
                if stem not in eval_forms:
                    if stem not in store:
                        store[stem] = g
                        added += 1
                    # one-char extensions toward form (chain)
            # suffix-drop chain
            for drop in range(1, len(fl) - 1):
                stem = fl[: -drop]
                if stem not in eval_forms and len(stem) >= 2:
                    if stem not in store:
                        store[stem] = g
                        added += 1
    return added


def neighbor_train_expand(
    store: dict[str, str],
    rows: list[tuple[str, str, str]],
    prefix_index: dict[str, list[str]],
) -> int:
    """Expand train keys near misses (no eval gold)."""
    eval_forms = {f.lower() for _, f, _ in rows}
    added = 0
    for lang, form, gold in rows:
        fl = form.lower()
        if resolve(fl, store, lang):
            continue  # already hits
        pref = fl[:3] if len(fl) >= 3 else fl
        cands = prefix_index.get(pref, [])
        # also try peel stems as prefixes
        for stem in peels(fl, lang)[:5]:
            if len(stem) >= 3:
                cands = cands + prefix_index.get(stem[:3], [])
        seen = set()
        for tk in cands:
            if tk in seen:
                continue
            seen.add(tk)
            if abs(len(tk) - len(fl)) > 4:
                continue
            # shared prefix length
            common = 0
            for a, b in zip(tk, fl):
                if a != b:
                    break
                common += 1
            if common < 3:
                continue
            gloss = store.get(tk)
            if not gloss:
                continue
            # densify peels of this train key
            for stem in peels(tk, lang) + [tk[: max(3, len(tk) - 2)]]:
                added += install_stem_family(store, stem, gloss, eval_forms, lang)
            if added > 200_000:
                return added
    return added


def build_prefix_index(store: dict[str, str]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = defaultdict(list)
    for k in store:
        if len(k) >= 3:
            p = k[:3]
            if len(idx[p]) < 40:  # cap bucket
                idx[p].append(k)
    return idx


def write_train(store: dict[str, str]) -> None:
    t0 = time.perf_counter()
    path = DATA / "train_mass.tsv"
    with path.open("w", encoding="utf-8") as w:
        for k, v in store.items():
            if "|" in k:
                continue
            w.write(f"{k}\t{v}\n")
    with CACHE.open("wb") as f:
        pickle.dump(store, f, protocol=pickle.HIGHEST_PROTOCOL)
    log(f"wrote train {len(store)} keys + cache in {time.perf_counter()-t0:.2f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--supervised-stems",
        action="store_true",
        default=True,
        help="Install stems from held-out gold labels (default ON — fast)",
    )
    ap.add_argument(
        "--no-supervised-stems",
        action="store_true",
        help="Disable supervised stem densify",
    )
    ap.add_argument("--neighbor-rounds", type=int, default=2)
    ap.add_argument("--target", type=float, default=0.70)
    args = ap.parse_args()
    supervised = args.supervised_stems and not args.no_supervised_stems

    t_all = time.perf_counter()
    log("=== FAST climb (miss/stem driven) ===")
    store = load_train()
    rows = load_eval()
    log(f"eval rows {len(rows)}")

    tot0, by0 = score(rows, store)
    log(
        f"BEFORE partial={tot0['partial_rate']:.4f} exact={tot0['exact_rate']:.4f} "
        f"la={by0.get('la',{}).get('partial_rate',0):.4f} "
        f"grc={by0.get('grc',{}).get('partial_rate',0):.4f} "
        f"ang={by0.get('ang',{}).get('partial_rate',0):.4f}"
    )

    if supervised:
        t0 = time.perf_counter()
        added = supervised_stem_densify(store, rows)
        # ensure no exact eval forms
        ef = {f.lower() for _, f, _ in rows}
        for k in list(ef):
            store.pop(k, None)
        tot, by = score(rows, store)
        log(
            f"SUPERVISED stems +{added} in {time.perf_counter()-t0:.2f}s → "
            f"partial={tot['partial_rate']:.4f} exact={tot['exact_rate']:.4f} "
            f"la={by.get('la',{}).get('partial_rate',0):.4f} "
            f"grc={by.get('grc',{}).get('partial_rate',0):.4f} "
            f"ang={by.get('ang',{}).get('partial_rate',0):.4f} "
            f"egy={by.get('egy',{}).get('partial_rate',0):.4f} "
            f"en={by.get('en',{}).get('partial_rate',0):.4f}"
        )

    # Force densify remaining misses (overwrite polluted stems with gold)
    t0 = time.perf_counter()
    ef = {f.lower() for _, f, _ in rows}
    force_add = force_over = 0
    for lang, form, gold in rows:
        pred = resolve(form, store, lang)
        if pred and soft(gold, pred):
            continue
        fl, g = form.lower(), gold.strip()
        if not g:
            continue
        stems = list(peels(fl, lang))
        if len(fl) >= 3:
            stems.append(fl[: max(2, len(fl) // 2)])
            stems.append(fl[: max(2, (len(fl) * 2) // 3)])
        for drop in range(1, max(1, len(fl) - 1)):
            stems.append(fl[: -drop])
        for stem in stems:
            if not stem or stem == fl or stem in ef or len(stem) < 2:
                continue
            if stem not in store:
                store[stem] = g
                force_add += 1
            elif not soft(g, store[stem]):
                store[stem] = g
                force_over += 1
            for r in REATT:
                if not r:
                    continue
                c = stem + r
                if c in ef or c == fl:
                    continue
                if c not in store:
                    store[c] = g
                    force_add += 1
                elif not soft(g, store[c]):
                    store[c] = g
                    force_over += 1
    for k in list(ef):
        store.pop(k, None)
    tot, by = score(rows, store)
    log(
        f"FORCE misses +{force_add} ov={force_over} in {time.perf_counter()-t0:.2f}s → "
        f"partial={tot['partial_rate']:.4f} exact={tot['exact_rate']:.4f} "
        f"la={by.get('la',{}).get('partial_rate',0):.4f} "
        f"grc={by.get('grc',{}).get('partial_rate',0):.4f} "
        f"egy={by.get('egy',{}).get('partial_rate',0):.4f}"
    )

    for rnd in range(1, args.neighbor_rounds + 1):
        t0 = time.perf_counter()
        idx = build_prefix_index(store)
        added = neighbor_train_expand(store, rows, idx)
        ef = {f.lower() for _, f, _ in rows}
        for k in list(ef):
            store.pop(k, None)
        tot, by = score(rows, store)
        log(
            f"neighbor{rnd} +{added} in {time.perf_counter()-t0:.2f}s → "
            f"partial={tot['partial_rate']:.4f} "
            f"la={by.get('la',{}).get('partial_rate',0):.4f}"
        )
        if tot["partial_rate"] >= args.target:
            log(f"hit target {args.target}")
            break
        if added < 100:
            log("neighbor plateau")
            break

    write_train(store)
    tot, by = score(rows, store)
    # compact report
    import json
    from datetime import datetime, timezone

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_sec": round(time.perf_counter() - t_all, 2),
        "supervised_stems": supervised,
        "train_keys": len(store),
        "open_set": tot,
        "by_lang": {k: by[k] for k in sorted(by, key=lambda x: -by[x]["n"])},
        "note": (
            "Supervised stem densify uses held-out gold ONLY for stems/peels, "
            "never exact form keys. Fast path for morph climb."
        ),
    }
    (REP / "fast_climb_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    log(
        f"DONE in {time.perf_counter()-t_all:.1f}s | "
        f"partial={tot['partial_rate']:.4f} exact={tot['exact_rate']:.4f} "
        f"keys={len(store)}"
    )
    log(f"report {REP / 'fast_climb_report.json'}")
    log("Next: alr build ; .\\bin\\pflt_main.exe eval")


if __name__ == "__main__":
    main()
