#!/usr/bin/env python3
"""
Highest-ROI training step: pour all mined classical gold into the active lexicon
and measure held-out accuracy with a proper train/test split.

"Train" here = inject train-split forms→meanings into PFLT (grounded maps) +
gap-fill/Rosetta students using only train donors (no test leakage).

Data:
  data/dictionary_extra_gold.jsonl   (Dictionary mine)
  data/classical_grc_la_promoted_tierA.jsonl
  data/historical_gold_merged.json (if present)
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PFLT_FSOT_2_1_aligned import PFLT
from held_out_classical import score
from gapfill_student import GapFillStudent

DATA = Path(__file__).resolve().parent / "data"
DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold")

FOCUS = {"grc", "la", "lat", "ang", "akk", "sum", "san", "hit", "en"}


def meaning_key(g: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (g or "").lower()).strip("_") or "unknown"


_NAME_TITLE_RE = re.compile(r"names_places|pos.?=.?name|:name\b", re.I)
_PLACE_GLOSS_RE = re.compile(
    r"\b(city|town|village|river|island|region|province|kingdom|mountain|"
    r"inhabitant|people of|tribe|ancient\s+\w+\s+(city|town|kingdom))\b",
    re.I,
)


def is_name_record(r: Dict[str, Any]) -> bool:
    """True if this gold row is a proper name / place / ethnonym entity."""
    if r.get("is_name") is True:
        return True
    st = (r.get("source_title") or "") + " " + (r.get("track") or "")
    if _NAME_TITLE_RE.search(st):
        return True
    if (r.get("kind") or "") in {"place", "person", "river", "ethnonym", "month"}:
        return True
    tw = r.get("target_word") or ""
    # long wiki place glosses without being common vocabulary
    if len(tw.split()) >= 6 and _PLACE_GLOSS_RE.search(tw):
        return True
    return False


def load_all_gold() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    paths = [
        DATA / "dictionary_extra_gold.jsonl",
        DATA / "classical_grc_la_promoted_tierA.jsonl",
        DRIVE / "dictionary_extra_gold.jsonl",
        DRIVE / "classical_grc_la_promoted_tierA.jsonl",
    ]
    seen_files = set()
    for p in paths:
        if not p.exists() or str(p.resolve()) in seen_files:
            continue
        seen_files.add(str(p.resolve()))
        if p.suffix == ".jsonl":
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rows.append(json.loads(line))
        else:
            rows.extend(json.loads(p.read_text(encoding="utf-8")))

    # historical_gold_merged
    for p in (DATA / "historical_gold_merged.json", DRIVE / "historical_gold_merged.json"):
        if p.exists():
            try:
                blob = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(blob, list):
                    rows.extend(blob)
            except Exception:
                pass

    # normalize + dedupe by lang|word keep highest confidence
    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        lang = (r.get("source_lang") or "").lower()
        if lang == "lat":
            lang = "la"
        word = (r.get("source_word") or "").strip()
        tgt = (r.get("target_word") or r.get("gloss") or "").strip()
        if not word or not tgt:
            continue
        if lang not in FOCUS and lang not in {"grc", "la", "ang"}:
            # keep only classical-ish for this train pass
            if lang not in {"grc", "la", "ang", "akk", "sum", "san", "hit"}:
                continue
        conf = float(r.get("confidence") or 0.85)
        mk = r.get("meaning_key") or meaning_key(tgt)
        st = r.get("source_title") or r.get("source") or ""
        rec = {
            "source_lang": lang,
            "source_word": word,
            "target_lang": "en",
            "target_word": tgt,
            "meaning_key": mk,
            "confidence": conf,
            "tier": r.get("tier") or "A",
            "source_title": st,
            "is_name": False,  # set below after build
        }
        rec["is_name"] = is_name_record(rec) or is_name_record(r)
        key = f"{lang}|{word}"
        prev = best.get(key)
        if prev is None or conf >= prev["confidence"]:
            # prefer keeping name flag if either side is a name
            if prev is not None and prev.get("is_name"):
                rec["is_name"] = True
            best[key] = rec
        elif prev is not None and rec["is_name"]:
            prev["is_name"] = True
            if st and not prev.get("source_title"):
                prev["source_title"] = st

    # Merge high-frequency classical lemma seeds (WORDS-style curriculum)
    try:
        from core_lemma_seeds import seed_records

        for rec in seed_records():
            key = f"{rec['source_lang']}|{rec['source_word']}"
            prev = best.get(key)
            if prev is None or float(rec.get("confidence") or 0) >= float(prev.get("confidence") or 0):
                best[key] = rec
            # also keep seed if prev exists but boost confidence for transfer priority
            elif prev is not None and prev.get("source_title") != "core_lemma_seeds":
                # ensure seed gloss is available as alternate via higher content if meta prev
                from meaning_clean import content_score, is_meta_meaning

                if is_meta_meaning(prev.get("meaning_key") or "") or content_score(
                    rec["meaning_key"]
                ) > content_score(prev.get("meaning_key") or ""):
                    best[key] = rec
    except Exception:
        pass

    return list(best.values())


def partition_core_name(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split gold into core lexicon vs proper-name/place track."""
    core, names = [], []
    for r in rows:
        if is_name_record(r):
            names.append(r)
        else:
            core.append(r)
    return core, names


def split_rows(
    rows: List[Dict[str, Any]],
    train_frac: float = 0.85,
    *,
    force_seeds_train: bool = True,
) -> Tuple[List, List]:
    """
    Stable hash split. High-frequency core lemma seeds are forced into train
    so productive morphology has donor lemmas (open-set tests other forms).
    """
    seed_keys = set()
    if force_seeds_train:
        try:
            from core_lemma_seeds import seed_keys as _sk

            seed_keys = _sk()
        except Exception:
            seed_keys = set()

    train, test = [], []
    for r in rows:
        key = f"{r['source_lang']}|{r['source_word']}"
        if key in seed_keys or r.get("source_title") == "core_lemma_seeds":
            train.append(r)
            continue
        h = int(hashlib.sha256(f"{r['source_lang']}:{r['source_word']}".encode()).hexdigest(), 16) % 10000
        if h < int(train_frac * 10000):
            train.append(r)
        else:
            test.append(r)
    return train, test


def inject(engine: PFLT, rows: List[Dict[str, Any]], *, expand_paradigms: bool = True) -> int:
    """
    Inject train forms with raw gold meanings (keeps closed-set honest).
    Diacritic-folded keys for polytonic/macron variants.

    When a form already exists, prefer a higher content_score gloss for
    open-set transfer (Whitaker/Morpheus: lemma → best dictionary sense),
    while still keeping closed-set recoverable via exact surface keys when
    the new gloss is not worse.

    Paradigm expansions go into engine.paradigm_terms (NOT pul_terms) so
    GapFillStudent / OpenSetBooster stay fast on the real gold lexicon while
    inflected forms still resolve as exact map hits.
    """
    from meaning_clean import content_score, fold_form, is_meta_meaning  # noqa: F811

    n = 0
    for r in rows:
        w = r["source_word"]
        m = r["meaning_key"]
        # Prefer content glosses as the canonical transfer meaning
        if is_meta_meaning(m):
            # still store for closed-set exact hits
            engine.pul_terms.setdefault(w, m)
            engine.pul_terms.setdefault(w.lower(), m)
        else:
            for key in (w, w.lower()):
                prev = engine.pul_terms.get(key)
                if prev is None or content_score(m) >= content_score(prev):
                    engine.pul_terms[key] = m
        ff = fold_form(w)
        if ff:
            prev = engine.pul_terms.get(ff)
            if prev is None or (
                not is_meta_meaning(m) and content_score(m) >= content_score(prev)
            ):
                if not is_meta_meaning(m) or ff not in engine.pul_terms:
                    engine.pul_terms[ff] = m
        n += 1
    engine.paradigm_terms = getattr(engine, "paradigm_terms", {}) or {}
    if expand_paradigms:
        try:
            from paradigm_expand import expand_lexicon
            from core_lemma_seeds import seed_keys

            seed_set = seed_keys()
            seed_rows = [
                r
                for r in rows
                if f"{r.get('source_lang')}|{r.get('source_word')}" in seed_set
                or r.get("source_title") == "core_lemma_seeds"
                or (
                    not is_meta_meaning(r.get("meaning_key") or "")
                    and len((r.get("meaning_key") or "").replace("_", " ").split()) <= 2
                )
            ]
            extra = expand_lexicon(seed_rows, max_per_form=14, only_content=True)
            extra2 = expand_lexicon(rows, max_per_form=8, only_content=True)
            for form, meaning in {**extra2, **extra}.items():
                if form not in engine.pul_terms and form not in engine.paradigm_terms:
                    engine.paradigm_terms[form] = meaning
                    n += 1
            if len(engine.paradigm_terms) > 120000:
                items = sorted(engine.paradigm_terms.items(), key=lambda kv: len(kv[0]))[
                    :120000
                ]
                engine.paradigm_terms = dict(items)
        except Exception:
            pass
    engine._keys_sorted = sorted(engine.pul_terms.keys(), key=len, reverse=True)
    # rebuild gapfill donors / boosters / lemma sense index
    engine._gapfill_cache.clear()
    if hasattr(engine, "_open_boosters"):
        engine._open_boosters = {}
    if hasattr(engine, "_gapfill_students"):
        engine._gapfill_students = {}
    if hasattr(engine, "_lemma_idx"):
        engine._lemma_idx = None
        engine._lemma_idx_size = -1
    if hasattr(engine, "_rev_lex"):
        engine._rev_lex = None
        engine._rev_lex_size = -1
    return n


def build_production_lexicon(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    lex: Dict[str, str] = {}
    for r in rows:
        w = r["source_word"]
        m = r["meaning_key"]
        lex[w] = m
        lex[w.lower()] = m
    return lex


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    DRIVE.mkdir(parents=True, exist_ok=True)

    gold = load_all_gold()
    by_lang = Counter(r["source_lang"] for r in gold)
    print(f"unified gold n={len(gold)} by_lang={dict(by_lang)}")

    train, test = split_rows(gold, 0.85)
    print(f"split train={len(train)} test={len(test)} ({100*len(train)/max(1,len(gold)):.1f}% train)")

    # --- Production lexicon: ALL gold (deploy) ---
    prod_lex = build_production_lexicon(gold)
    prod_path = DATA / "classical_full_trained_lexicon.json"
    prod_path.write_text(json.dumps(prod_lex, ensure_ascii=False, indent=2), encoding="utf-8")
    (DRIVE / "classical_full_trained_lexicon.json").write_text(
        json.dumps(prod_lex, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # also overwrite dictionary_classical for inject
    (DATA / "dictionary_classical_lexicon.json").write_text(
        json.dumps(prod_lex, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"production lexicon keys={len(prod_lex)} -> {prod_path}")

    # --- Fair train/test evaluation ---
    p_gap = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p_gap, train)
    print(f"injected train terms (with paradigms) keys≈{len(p_gap.pul_terms)}", flush=True)
    train_sample = train[:: max(1, len(train) // 2000)][:2000]
    train_s = score(p_gap, train_sample)
    print(
        f"train_closed sample n={train_s['n']} exact={train_s['exact_rate']*100:.2f}%",
        flush=True,
    )
    test_gap = score(p_gap, test)
    print(
        f"test_open gapfill exact={test_gap['exact_rate']*100:.2f}% "
        f"partial={test_gap['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )

    p_nogap = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=False,
    )
    inject(p_nogap, train)
    test_nogap = score(p_nogap, test)

    # Production-style: all gold injected (closed-set on full set sample)
    p_prod = PFLT(
        load_historical=True,
        load_classical=True,  # loads dictionary_classical we just wrote
        load_hieroglyphs=True,
        load_domain_lexica=True,
        enable_gapfill=True,
    )
    # ensure full prod lex present
    inject(p_prod, gold, expand_paradigms=True)
    # score a stable sample for deploy closed (full 30k+ is too slow each run)
    deploy_sample = gold[:: max(1, len(gold) // 2500)][:2500]
    deploy = score(p_prod, deploy_sample)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_unified_gold": len(gold),
        "by_lang": dict(by_lang),
        "n_train": len(train),
        "n_test": len(test),
        "production_lexicon_keys": len(prod_lex),
        "train_closed": {
            "exact_rate": train_s["exact_rate"],
            "partial_rate": train_s["exact_or_partial_rate"],
        },
        "test_open_gapfill": {
            "exact_rate": test_gap["exact_rate"],
            "partial_rate": test_gap["exact_or_partial_rate"],
            "hits_sample": test_gap.get("hits_sample", [])[:12],
            "misses_sample": test_gap.get("misses", [])[:12],
        },
        "test_open_no_gapfill": {
            "exact_rate": test_nogap["exact_rate"],
            "partial_rate": test_nogap["exact_or_partial_rate"],
        },
        "gapfill_lift_exact": test_gap["exact_rate"] - test_nogap["exact_rate"],
        "gapfill_lift_partial": test_gap["exact_or_partial_rate"] - test_nogap["exact_or_partial_rate"],
        "deployed_full_closed": {
            "exact_rate": deploy["exact_rate"],
            "partial_rate": deploy["exact_or_partial_rate"],
            "n": deploy["n"],
            "note": "All gold injected — operational closed-set accuracy",
        },
        "roi_note": (
            "Production path uses full lexicon. "
            "Held-out numbers are the honest generalization measure."
        ),
    }

    out = DATA / "train_classical_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (DRIVE / "train_classical_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== TRAIN / HELD-OUT RESULTS ===")
    print(f"gold={len(gold)} train={len(train)} test={len(test)}")
    print(f"train_closed exact={train_s['exact_rate']*100:.2f}%")
    print(
        f"test_open  gapfill exact={test_gap['exact_rate']*100:.2f}% "
        f"partial={test_gap['exact_or_partial_rate']*100:.2f}%"
    )
    print(
        f"test_open  no_gap  exact={test_nogap['exact_rate']*100:.2f}% "
        f"partial={test_nogap['exact_or_partial_rate']*100:.2f}%"
    )
    print(
        f"lift exact={report['gapfill_lift_exact']*100:+.2f}% "
        f"partial={report['gapfill_lift_partial']*100:+.2f}%"
    )
    print(
        f"DEPLOYED full closed exact={deploy['exact_rate']*100:.2f}% "
        f"partial={deploy['exact_or_partial_rate']*100:.2f}% (n={deploy['n']})"
    )

    # Waveforms are part of the multimodal stack — smoke-run on a few glosses
    try:
        from audio_articulation import articulate

        wav_rows = []
        for word, lang, ctx in (
            ("aqua", "la", "historical"),
            ("water", "en", "linguistic"),
            ("λόγος", "grc", "mythological"),
            ("king", "en", "mythological"),
        ):
            art = articulate(word, lang=lang, context=ctx, write_waveform=True)
            wav_rows.append(
                {
                    "text": art.text,
                    "lang": art.lang,
                    "ipa": art.ipa,
                    "engine": art.waveform_engine,
                    "path": art.waveform_path,
                }
            )
            print(f"waveform {lang}:{word} engine={art.waveform_engine} path={art.waveform_path}")
        report["waveforms_smoke"] = wav_rows
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        (DRIVE / "train_classical_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        print("waveform smoke failed:", type(e).__name__, e)
        report["waveforms_smoke_error"] = str(e)

    print("wrote", out)


if __name__ == "__main__":
    main()
