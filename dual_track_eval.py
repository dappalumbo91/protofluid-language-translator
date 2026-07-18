#!/usr/bin/env python3
"""
Dual-track honest eval:
  CORE  — common vocabulary (morphology / gap-fill / paradigms)
  NAME  — proper names / places (gazetteer + historical contacts)

Train inject uses FULL gold (both tracks) so name contacts help name test
and core keeps full donor mass. Test metrics are reported separately.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from promote_and_train_classical import (
    inject,
    is_name_record,
    load_all_gold,
    partition_core_name,
    split_rows,
)
from held_out_classical import score, _soft_overlap
from PFLT_FSOT_2_1_aligned import PFLT

DATA = Path(__file__).resolve().parent / "data"
OUT = DATA / "dual_track_report.json"
DRIVE = Path(r"D:\training data\pflt_linguistics\01_historical_gold\dual_track_report.json")


def split_90_10(rows: List[Dict[str, Any]]) -> Tuple[List, List]:
    train, test = [], []
    for r in rows:
        h = int(
            hashlib.sha256(f"{r['source_lang']}:{r['source_word']}".encode()).hexdigest(),
            16,
        ) % 10000
        (train if h < 9000 else test).append(r)
    return train, test


def score_name_track(pflt: PFLT, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Name-aware scoring: prefer short cleaned titles from name_gazetteer.clean_name_gloss
    so wiki parentheticals don't force false misses.
    """
    try:
        from name_gazetteer import clean_name_gloss
    except Exception:
        clean_name_gloss = None

    exact = partial = 0
    details = []
    for r in rows:
        lang = (r.get("source_lang") or "la").lower()
        ctx = "mythological" if lang in {"grc", "el"} else (
            "english" if lang == "en" else "historical"
        )
        out = pflt.translate(r["source_word"], context=ctx, target_lang="english")
        pred = " ".join(out.get("meanings") or []).lower()
        gold = (r.get("target_word") or "").lower()
        gold_mk = (r.get("meaning_key") or "").lower()
        # short title from gloss cleaner
        title_mk = gold_mk
        if clean_name_gloss is not None:
            t, _k = clean_name_gloss(r.get("target_word") or "")
            if t:
                title_mk = t

        pred_flat = pred.replace("_", " ")
        hit = (
            gold in pred
            or gold_mk in pred
            or title_mk in pred
            or title_mk.replace("_", " ") in pred_flat
            or re.sub(r"^(a|an|the)\s+", "", gold) in pred
        )
        soft = _soft_overlap(gold, pred, pred) or _soft_overlap(
            title_mk.replace("_", " "), pred, pred
        )
        if hit:
            exact += 1
            kind = "exact"
        elif soft:
            partial += 1
            kind = "partial"
        else:
            kind = "miss"
        details.append(
            {
                "lang": lang,
                "word": r["source_word"],
                "gold": r.get("target_word"),
                "title": title_mk,
                "meanings": out.get("meanings"),
                "kind": kind,
            }
        )
    n = max(1, len(rows))
    return {
        "n": len(rows),
        "exact": exact,
        "partial": partial,
        "exact_rate": exact / n,
        "exact_or_partial_rate": (exact + partial) / n,
        "hits_sample": [d for d in details if d["kind"] == "exact"][:10],
        "misses_sample": [d for d in details if d["kind"] == "miss"][:12],
    }


def by_lang_scores(pflt: PFLT, rows: List[Dict[str, Any]], name_mode: bool) -> Dict[str, Any]:
    by = defaultdict(list)
    for r in rows:
        by[r["source_lang"]].append(r)
    out = {}
    for lang, rs in sorted(by.items(), key=lambda x: -len(x[1])):
        if len(rs) < 30:
            continue
        s = score_name_track(pflt, rs) if name_mode else score(pflt, rs)
        out[lang] = {
            "n": s["n"],
            "exact": s["exact_rate"],
            "partial": s["exact_or_partial_rate"],
        }
        print(
            f"  {lang:5s} n={s['n']:4d} exact={s['exact_rate']*100:5.2f}% "
            f"partial={s['exact_or_partial_rate']*100:5.2f}%",
            flush=True,
        )
    return out


def main() -> None:
    # Ensure gazetteer exists
    gaz_path = DATA / "name_gazetteer.json"
    if not gaz_path.exists():
        from name_gazetteer import build_from_dictionary

        print("building name gazetteer...", flush=True)
        build_from_dictionary()

    gold = load_all_gold()
    core_all, name_all = partition_core_name(gold)
    print(
        f"gold={len(gold)} core={len(core_all)} name={len(name_all)} "
        f"name_pct={100*len(name_all)/max(1,len(gold)):.1f}%",
        flush=True,
    )

    # 90/10 on full gold for train inject
    train, test = split_90_10(gold)
    core_test = [r for r in test if not is_name_record(r)]
    name_test = [r for r in test if is_name_record(r)]
    print(
        f"90/10 train={len(train)} test={len(test)} "
        f"core_test={len(core_test)} name_test={len(name_test)}",
        flush=True,
    )

    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=True)
    print(f"pul={len(p.pul_terms)} para={len(getattr(p, 'paradigm_terms', {}))}", flush=True)

    from name_gazetteer import NameGazetteer

    name_train = [r for r in train if is_name_record(r)]

    print("=== CORE track (lexicon / morph; empty name gaz) ===", flush=True)
    p._name_gaz = NameGazetteer(load=False)
    core_s = score(p, core_test)
    print(
        f"CORE ALL n={core_s['n']} exact={core_s['exact_rate']*100:.2f}% "
        f"partial={core_s['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )
    core_lang = by_lang_scores(p, core_test, name_mode=False)

    print("=== NAME OPEN A: train gold + seeds (no Pleiades) ===", flush=True)
    p._name_gaz = NameGazetteer.from_gold_rows(
        name_train, include_seeds=True, names_only=False, include_pleiades=False
    )
    print(
        f"  gaz forms={len(p._name_gaz.by_form)} name_train={len(name_train)}",
        flush=True,
    )
    name_s = score_name_track(p, name_test)
    print(
        f"NAME OPEN-A n={name_s['n']} exact={name_s['exact_rate']*100:.2f}% "
        f"partial={name_s['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )
    name_lang = by_lang_scores(p, name_test, name_mode=True)

    print("=== NAME OPEN B: train + seeds + Pleiades ===", flush=True)
    p._name_gaz = NameGazetteer.from_gold_rows(
        name_train, include_seeds=True, names_only=False, include_pleiades=True
    )
    print(f"  gaz forms={len(p._name_gaz.by_form)}", flush=True)
    name_ple = score_name_track(p, name_test)
    print(
        f"NAME OPEN-B n={name_ple['n']} exact={name_ple['exact_rate']*100:.2f}% "
        f"partial={name_ple['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )

    print("=== FULL bag (train gaz A — honest mixed) ===", flush=True)
    p._name_gaz = NameGazetteer.from_gold_rows(
        name_train, include_seeds=True, names_only=False, include_pleiades=False
    )
    full_s = score(p, test)
    print(
        f"FULL ALL n={full_s['n']} exact={full_s['exact_rate']*100:.2f}% "
        f"partial={full_s['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )

    print("=== NAME DEPLOYED (full Dictionary + Pleiades gaz) ===", flush=True)
    p._name_gaz = NameGazetteer()  # production JSON on disk
    name_dep = score_name_track(p, name_test)
    print(
        f"NAME DEPLOY n={name_dep['n']} exact={name_dep['exact_rate']*100:.2f}% "
        f"partial={name_dep['exact_or_partial_rate']*100:.2f}%",
        flush=True,
    )

    # train closed sample
    tr = score(p, train[:: max(1, len(train) // 1200)][:1200])
    print(f"train_closed sample exact={tr['exact_rate']*100:.2f}%", flush=True)

    # waveforms smoke
    wavs = []
    try:
        from audio_articulation import articulate

        for w, l, c in (
            ("aqua", "la", "historical"),
            ("Roma", "la", "historical"),
            ("Κύπρος", "grc", "mythological"),
        ):
            a = articulate(w, lang=l, context=c, write_waveform=True)
            wavs.append(
                {"text": a.text, "engine": a.waveform_engine, "path": a.waveform_path}
            )
            print(f"wav {w} {a.waveform_engine}", flush=True)
    except Exception as e:
        wavs = [{"error": str(e)}]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_gold": len(gold),
        "n_core": len(core_all),
        "n_name": len(name_all),
        "n_train": len(train),
        "n_test": len(test),
        "core_90_10": {
            "exact": core_s["exact_rate"],
            "partial": core_s["exact_or_partial_rate"],
            "n": core_s["n"],
            "by_lang": core_lang,
            "hits_sample": core_s.get("hits_sample", [])[:8],
            "misses_sample": core_s.get("misses", [])[:8],
        },
        "name_open_train_seeds": {
            "exact": name_s["exact_rate"],
            "partial": name_s["exact_or_partial_rate"],
            "n": name_s["n"],
            "by_lang": name_lang,
            "hits_sample": name_s.get("hits_sample", [])[:8],
            "misses_sample": name_s.get("misses_sample", [])[:8],
            "note": "Train-only name gold + classical seeds; no test leakage; no Pleiades",
        },
        "name_open_train_seeds_pleiades": {
            "exact": name_ple["exact_rate"],
            "partial": name_ple["exact_or_partial_rate"],
            "n": name_ple["n"],
            "note": "Train names + seeds + Pleiades external curriculum contacts",
        },
        "name_deployed_full_gaz": {
            "exact": name_dep["exact_rate"],
            "partial": name_dep["exact_or_partial_rate"],
            "n": name_dep["n"],
            "note": "Full Dictionary+Pleiades gazetteer (operational coverage, not open-set)",
        },
        "full_mixed_90_10": {
            "exact": full_s["exact_rate"],
            "partial": full_s["exact_or_partial_rate"],
            "n": full_s["n"],
            "note": "Mixed bag dilutes; prefer core + name tracks",
        },
        "train_closed_sample": {"exact": tr["exact_rate"], "n": tr["n"]},
        "pul_terms": len(p.pul_terms),
        "paradigm_terms": len(getattr(p, "paradigm_terms", {}) or {}),
        "waveforms": wavs,
        "policy": {
            "core": "morphology + reverse_morph + paradigms + gapfill",
            "name": "name_gazetteer + historical contacts + demonym peel (before gapfill)",
            "scoring": "name track uses cleaned short English titles",
        },
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    DRIVE.parent.mkdir(parents=True, exist_ok=True)
    DRIVE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    # also refresh push report summary
    push = DATA / "push_open_report.json"
    summary = {
        "built_utc": report["built_utc"],
        "dual_track": {
            "core_partial": report["core_90_10"]["partial"],
            "name_open_train_seeds": report["name_open_train_seeds"]["partial"],
            "name_open_plus_pleiades": report["name_open_train_seeds_pleiades"]["partial"],
            "name_deployed_partial": report["name_deployed_full_gaz"]["partial"],
            "full_partial": report["full_mixed_90_10"]["partial"],
            "n_core_test": report["core_90_10"]["n"],
            "n_name_test": report["name_open_train_seeds"]["n"],
        },
        "n_gold": report["n_gold"],
    }
    if push.exists():
        try:
            prev = json.loads(push.read_text(encoding="utf-8"))
            prev.update(summary)
            push.write_text(json.dumps(prev, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            push.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        push.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("wrote", OUT, flush=True)
    print(
        f"SUMMARY core={report['core_90_10']['partial']*100:.2f}% "
        f"name_openA={report['name_open_train_seeds']['partial']*100:.2f}% "
        f"name_openB_pleiades={report['name_open_train_seeds_pleiades']['partial']*100:.2f}% "
        f"name_deploy={report['name_deployed_full_gaz']['partial']*100:.2f}% "
        f"full={report['full_mixed_90_10']['partial']*100:.2f}%",
        flush=True,
    )


if __name__ == "__main__":
    main()
