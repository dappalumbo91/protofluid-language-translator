#!/usr/bin/env python3
"""
PFLT / FSOT stage test — run everything we can score with current data.

No fake leaderboards. Reports closed-set grounding, open-set honesty,
hieroglyph contract, vision multi-layer, lineage Tier-B rates, scalar health.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

DRIVE_OUT = Path(r"D:\training data\pflt_linguistics\00_manifests\stage_test_report.json")
LOCAL_OUT = ROOT / "data" / "stage_test_report.json"


def section(name: str) -> None:
    print("\n" + "=" * 72)
    print(name)
    print("=" * 72)


def main() -> int:
    t0 = time.time()
    report: Dict[str, Any] = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "PFLT FSOT communicator — runnable tests with current data",
        "results": {},
        "errors": [],
    }

    # --- 1. Scalar health ---
    section("1) FSOT scalar domain health")
    try:
        from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, compute_S_D_chaotic, PFLT

        rows = []
        for name, p in DOMAIN_PARAMS.items():
            panel = compute_S_D_chaotic(
                D_eff=float(p["D_eff"]),
                observed=bool(p["observed"]),
                delta_psi=float(p["delta_psi"]),
                delta_theta=float(p["delta_theta"]),
            )
            ok = panel.S == panel.S and abs(panel.S) < 1e6
            rows.append({"domain": name, "S": panel.S, "ok": ok, "qm": panel.quirk_mod})
            print(f"  {name:18s} S={panel.S:+.4f} qm={panel.quirk_mod:.3f} {'OK' if ok else 'FAIL'}")
        report["results"]["scalar_health"] = {
            "ok": all(r["ok"] for r in rows),
            "n_domains": len(rows),
            "domains": rows,
        }
    except Exception as e:
        report["errors"].append({"scalar_health": str(e), "tb": traceback.format_exc()})
        print("FAIL", e)

    # --- 2. Load PFLT and lexicon sizes ---
    section("2) PFLT load + lexicon inventory")
    try:
        pflt = PFLT(load_historical=True, load_classical=True, load_hieroglyphs=True)
        report["results"]["lexicon"] = {
            "ok": True,
            "size": len(pflt.pul_terms),
        }
        print(f"  lexicon_size = {len(pflt.pul_terms)}")
    except Exception as e:
        pflt = None
        report["errors"].append({"pflt_load": str(e)})
        print("FAIL", e)
        report["results"]["lexicon"] = {"ok": False}

    # --- 3. Real multi-domain gold (from REAL_GOLD in aligned module) ---
    section("3) Multi-domain REAL_GOLD fixtures")
    try:
        from PFLT_FSOT_2_1_aligned import REAL_GOLD

        cases = []
        for gold in REAL_GOLD:
            r = pflt.translate(gold["input"], context=gold["context"], target_lang="english")
            blob = (" ".join(r["meanings"]) + " " + r["translation"]).lower()
            group_hits = 0
            for group in gold["must_include_any"]:
                if any(term.lower() in blob for term in group):
                    group_hits += 1
            cov = group_hits / max(1, len(gold["must_include_any"]))
            cases.append(
                {
                    "id": gold["id"],
                    "exact_map_rate": r["exact_map_rate"],
                    "semantic_coverage": cov,
                    "S": r["fsot_coherence_S"],
                    "tokens": r["tokens"],
                    "meanings": r["meanings"],
                }
            )
            print(
                f"  [{gold['id']}] map={r['exact_map_rate']*100:5.1f}% "
                f"sem={cov*100:5.1f}% S={r['fsot_coherence_S']:+.3f}"
            )
        report["results"]["real_gold"] = {
            "ok": True,
            "n": len(cases),
            "mean_map": sum(c["exact_map_rate"] for c in cases) / len(cases),
            "mean_semantic": sum(c["semantic_coverage"] for c in cases) / len(cases),
            "cases": cases,
        }
    except Exception as e:
        report["errors"].append({"real_gold": str(e), "tb": traceback.format_exc()})
        print("FAIL", e)

    # --- 4. Hieroglyph Unikemet closed-set ---
    section("4) Hieroglyph Gardiner / Unicode closed-set")
    try:
        codes = ["A1", "D21", "G17", "N5", "S34", "D4", "G5", "I9", "N35", "X1", "A2", "D36"]
        uni = ["\U00013000", "\U0001308b", "\U00013153", "\U00013216", "\U000132F9"]
        hits = 0
        details = []
        for c in codes + uni:
            r = pflt.translate(c, context="hieroglyphic")
            ok = r["exact_map_rate"] >= 1.0 and r["meanings"] and "generic" not in r["meanings"][0]
            hits += int(ok)
            details.append({"code": c, "ok": ok, "meaning": r["meanings"], "S": r["fsot_coherence_S"]})
            print(f"  {c!r:12s} -> {r['meanings'][0] if r['meanings'] else '?'}  {'OK' if ok else 'MISS'}")
        n = len(codes) + len(uni)
        report["results"]["hieroglyph"] = {
            "ok": hits == n,
            "n": n,
            "accuracy": hits / n,
            "details": details,
        }
        print(f"  accuracy = {hits}/{n} = {hits/n*100:.1f}%")
    except Exception as e:
        report["errors"].append({"hieroglyph": str(e)})
        print("FAIL", e)

    # --- 5. Classical closed-set sample ---
    section("5) Classical Latin/Greek closed-set (promoted gold sample)")
    try:
        path = ROOT / "data" / "classical_grc_la_promoted_tierA.jsonl"
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        sample = rows[:: max(1, len(rows) // 100)][:100]  # ~100 spread samples
        exact = 0
        for r in sample:
            out = pflt.translate(r["source_word"], context="historical")
            blob = (" ".join(out["meanings"]) + " " + out["translation"]).lower()
            gold = r["target_word"].lower()
            mk = (r.get("meaning_key") or "").lower().replace("_", " ")
            if gold in blob or mk in blob or (r.get("meaning_key") or "").lower() in blob:
                exact += 1
        acc = exact / max(1, len(sample))
        report["results"]["classical_closed"] = {
            "ok": acc >= 0.95,
            "n": len(sample),
            "exact_rate": acc,
        }
        print(f"  sample n={len(sample)} exact_rate={acc*100:.1f}%")
    except Exception as e:
        report["errors"].append({"classical_closed": str(e)})
        print("FAIL", e)

    # --- 6. Classical held-out (prefer full train report if present) ---
    section("6) Classical held-out open-set + gap-fill student")
    try:
        full_rep = ROOT / "data" / "train_classical_report.json"
        if full_rep.exists():
            tr = json.loads(full_rep.read_text(encoding="utf-8"))
            lift = float(tr.get("gapfill_lift_partial") or 0)
            report["results"]["classical_held_out"] = {
                "ok": tr["train_closed"]["exact_rate"] >= 0.95 and lift >= 0.0,
                "source": "train_classical_report.json",
                "n_gold": tr.get("n_unified_gold"),
                "n_train": tr.get("n_train"),
                "n_test": tr.get("n_test"),
                "train_closed_exact": tr["train_closed"]["exact_rate"],
                "test_open_exact_gapfill": tr["test_open_gapfill"]["exact_rate"],
                "test_open_partial_gapfill": tr["test_open_gapfill"]["partial_rate"],
                "test_open_exact_no_gapfill": tr["test_open_no_gapfill"]["exact_rate"],
                "test_open_partial_no_gapfill": tr["test_open_no_gapfill"]["partial_rate"],
                "gapfill_lift_partial": lift,
                "deployed_full_closed_exact": tr["deployed_full_closed"]["exact_rate"],
                "note": "Full Dictionary+mine gold train/test (highest ROI pour).",
            }
            print(
                f"  gold={tr.get('n_unified_gold')} train={tr.get('n_train')} test={tr.get('n_test')}"
            )
            print(f"  train_closed={tr['train_closed']['exact_rate']*100:.2f}%")
            print(
                f"  test_open gapfill exact={tr['test_open_gapfill']['exact_rate']*100:.2f}% "
                f"partial={tr['test_open_gapfill']['partial_rate']*100:.2f}% "
                f"(no_gap partial={tr['test_open_no_gapfill']['partial_rate']*100:.2f}%, "
                f"lift={lift*100:+.2f}%)"
            )
            print(
                f"  DEPLOYED full closed exact={tr['deployed_full_closed']['exact_rate']*100:.2f}%"
            )
        else:
            from held_out_classical import load_rows, split_rows, score

            rows = load_rows(ROOT / "data" / "classical_grc_la_promoted_tierA.jsonl")
            train, test = split_rows(rows, 0.8)
            eng = PFLT(
                load_historical=True,
                load_classical=False,
                load_hieroglyphs=False,
                load_domain_lexica=False,
                enable_gapfill=True,
            )
            for r in train:
                w = r["source_word"]
                m = r.get("meaning_key") or r["target_word"].lower().replace(" ", "_")
                eng.pul_terms[w] = m
                eng.pul_terms[w.lower()] = m
            eng._keys_sorted = sorted(eng.pul_terms.keys(), key=len, reverse=True)
            train_s = score(eng, train)
            test_s = score(eng, test)
            report["results"]["classical_held_out"] = {
                "ok": train_s["exact_rate"] >= 0.95,
                "train_closed_exact": train_s["exact_rate"],
                "test_open_partial_gapfill": test_s["exact_or_partial_rate"],
            }
            print(f"  train_closed={train_s['exact_rate']*100:.1f}% open_partial={test_s['exact_or_partial_rate']*100:.1f}%")
    except Exception as e:
        report["errors"].append({"held_out": str(e), "tb": traceback.format_exc()})
        print("FAIL", e)

    # --- 7. Vision stub contract ---
    section("7) Vision stub (labels → meaning)")
    try:
        from vision_stub import vision_translate

        r = vision_translate(gardiner=["A1", "D21", "G17", "N5", "S34"])
        ok = bool(r.hypotheses) and r.pflt.get("exact_map_rate", 0) >= 1.0
        report["results"]["vision_stub"] = {
            "ok": ok,
            "map_rate": r.pflt.get("exact_map_rate"),
            "meanings": r.pflt.get("meanings"),
            "translation": r.pflt.get("translation"),
            "S": r.pflt.get("fsot_coherence_S"),
        }
        print(f"  map_rate={r.pflt.get('exact_map_rate')} ok={ok}")
        print(f"  {r.pflt.get('translation','')[:120]}...")
    except Exception as e:
        report["errors"].append({"vision_stub": str(e)})
        print("FAIL", e)

    # --- 8. Multi-layer vision field ---
    section("8) Multi-layer FSOT vision (gray+VIS+UV+NIR)")
    try:
        from fsot_multilayer_vision import (
            circle_mask,
            render_scene,
            underdrawing_mask,
        )

        visible = render_scene(
            material="ink_on_stone",
            mask=circle_mask(64, 64, 0.5, 0.5, 0.28),
            hidden=None,
        )
        hidden = render_scene(
            material="ink_on_stone",
            mask=circle_mask(64, 64, 0.5, 0.5, 0.28),
            hidden=underdrawing_mask(64, 64),
        )
        machine = render_scene(
            material="underdrawing",
            mask=[0.05] * (64 * 64),
            hidden=underdrawing_mask(64, 64),
        )
        # center pixels
        def cstats(pack, label):
            px = pack["pixels"][32 * 64 + 32]
            return {
                "label": label,
                "gray": px.gray,
                "uv": px.uv,
                "nir": px.nir,
                "rgb": px.rgb,
                "S": px.S,
                "tensor_dim": pack["tensor_dim"],
            }

        stats = [
            cstats(visible, "ink_visible"),
            cstats(hidden, "ink_plus_hidden"),
            cstats(machine, "machine_only_underdrawing"),
        ]
        # Test: hidden should raise UV/NIR vs visible-only
        uv_boost = stats[1]["uv"] > stats[0]["uv"]
        nir_boost = stats[1]["nir"] > stats[0]["nir"]
        machine_uv = stats[2]["uv"] > 0.1
        report["results"]["multilayer_vision"] = {
            "ok": uv_boost and nir_boost and machine_uv and stats[0]["tensor_dim"] == 24,
            "uv_boost_with_hidden": uv_boost,
            "nir_boost_with_hidden": nir_boost,
            "machine_only_has_uv": machine_uv,
            "tensor_dim": stats[0]["tensor_dim"],
            "centers": stats,
        }
        for s in stats:
            print(
                f"  {s['label']:28s} gray={s['gray']:.3f} uv={s['uv']:.3f} "
                f"nir={s['nir']:.3f} S={s['S']:+.3f}"
            )
        print(
            f"  checks: uv_boost={uv_boost} nir_boost={nir_boost} "
            f"machine_uv={machine_uv} dim={stats[0]['tensor_dim']}"
        )
    except Exception as e:
        report["errors"].append({"multilayer": str(e), "tb": traceback.format_exc()})
        print("FAIL", e)

    # --- 9. Lineage gap-fill report (already computed) ---
    section("9) ASJP lineage gap-fill (Tier B proposals)")
    try:
        path = ROOT / "data" / "asjp_lineage_gapfill_report.json"
        if not path.exists():
            path = Path(
                r"D:\training data\pflt_linguistics\09_ml_checkpoints\lineage"
                r"\asjp_lineage_gapfill_report.json"
            )
        if path.exists():
            lin = json.loads(path.read_text(encoding="utf-8"))
            report["results"]["lineage_gapfill"] = {
                "ok": True,
                "n_proposals": lin.get("n_proposals"),
                "n_accepted_tier_B": lin.get("n_accepted_tier_B"),
                "accept_rate": lin.get("accept_rate"),
                "sample": lin.get("accepted_sample", [])[:5],
            }
            print(
                f"  proposals={lin.get('n_proposals')} accepted_B={lin.get('n_accepted_tier_B')} "
                f"rate={float(lin.get('accept_rate') or 0)*100:.1f}%"
            )
            for s in (lin.get("accepted_sample") or [])[:4]:
                print(
                    f"    {s.get('target_lang')} missing {s.get('concept_name')}: "
                    f"'{s.get('proposed_form')}' sim={s.get('form_similarity')}"
                )
        else:
            report["results"]["lineage_gapfill"] = {"ok": False, "error": "report missing"}
            print("  report missing — run lineage_gapfill.py")
    except Exception as e:
        report["errors"].append({"lineage": str(e)})
        print("FAIL", e)

    # --- 9b. Domain lexica + vision student + audio policy ---
    section("9b) Domain lexica, vision student, audio+waveform")
    try:
        dlex_path = ROOT / "data" / "domain_lexica.json"
        dlex_ok = dlex_path.exists()
        n_dom = 0
        if dlex_ok:
            dlex = json.loads(dlex_path.read_text(encoding="utf-8"))
            n_dom = dlex.get("n_domains", 0)
        from vision_field_student import readout_from_pack
        from fsot_multilayer_vision import render_scene, circle_mask, underdrawing_mask

        pack = render_scene(
            material="ink_on_stone",
            mask=circle_mask(64, 64, 0.5, 0.5, 0.26),
            hidden=underdrawing_mask(64, 64),
        )
        vis = readout_from_pack(pack, pflt=pflt)
        from audio_articulation import articulate

        art = articulate("water", lang="en", context="linguistic")
        report["results"]["domain_lexica"] = {"ok": dlex_ok and n_dom >= 300, "n_domains": n_dom}
        report["results"]["vision_field_student"] = {
            "ok": vis.has_hidden_machine_band or "hidden" in vis.scene_class or "machine" in vis.scene_class,
            "scene_class": vis.scene_class,
            "confidence": vis.confidence,
            "peak_uv": vis.mean_uv,
            "peak_nir": vis.mean_nir,
        }
        wav_ok = bool(art.waveform_path) and Path(art.waveform_path).exists()
        report["results"]["audio_ipa"] = {
            "ok": art.ipa is not None and wav_ok,
            "ipa": art.ipa,
            "features": art.features,
            "waveform_path": art.waveform_path,
            "waveform_engine": art.waveform_engine,
            "policy": "ipa_plus_waveform",
        }
        print(f"  domain_lexica domains={n_dom} ok={dlex_ok}")
        print(f"  vision_student class={vis.scene_class} conf={vis.confidence}")
        print(
            f"  audio ipa={art.ipa} wav={art.waveform_engine} "
            f"path={art.waveform_path} features={list(art.features.keys())}"
        )
    except Exception as e:
        report["errors"].append({"extras": str(e), "tb": traceback.format_exc()})
        print("FAIL", e)

    # --- 10. Live narrative demos ---
    section("10) Live narrative demos")
    demos = [
        ("mythological", "ud-bi-a an ki-ta ba-dim-ma", "english"),
        ("genomic", "ATG-GTG-CAC-CTG-ACT", "english"),
        ("hieroglyphic", "A1 N5 S34", "fluid_tongue"),
        ("historical", "aqua lingua ius", "english"),
        ("cosmological", "hubbk s8", "english"),
    ]
    demo_out = []
    try:
        for ctx, text, lang in demos:
            r = pflt.translate(text, context=ctx, target_lang=lang)
            demo_out.append(
                {
                    "context": ctx,
                    "input": text,
                    "target": lang,
                    "meanings": r["meanings"],
                    "translation": r["translation"],
                    "S": r["fsot_coherence_S"],
                    "map": r["exact_map_rate"],
                }
            )
            print(f"  [{ctx}] {text}")
            print(f"    map={r['exact_map_rate']*100:.0f}% S={r['fsot_coherence_S']:+.3f}")
            print(f"    {r['translation'][:140]}")
        report["results"]["live_demos"] = {"ok": True, "demos": demo_out}
    except Exception as e:
        report["errors"].append({"demos": str(e)})
        print("FAIL", e)

    # --- Scoreboard ---
    section("SCOREBOARD")
    checks = []
    for key, val in report["results"].items():
        if isinstance(val, dict) and "ok" in val:
            checks.append((key, bool(val["ok"])))
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    report["scoreboard"] = {
        "passed": passed,
        "total": total,
        "pass_rate": passed / max(1, total),
        "checks": {k: v for k, v in checks},
        "elapsed_s": round(time.time() - t0, 2),
        "n_errors": len(report["errors"]),
    }
    for k, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}")
    print(f"\n  {passed}/{total} stage checks passed  ({report['scoreboard']['pass_rate']*100:.0f}%)")
    print(f"  elapsed {report['scoreboard']['elapsed_s']}s  errors={len(report['errors'])}")

    # highlights
    rg = report["results"].get("real_gold", {})
    hg = report["results"].get("hieroglyph", {})
    ho = report["results"].get("classical_held_out", {})
    print("\n  Highlights:")
    if rg:
        print(f"    real_gold mean_map={rg.get('mean_map',0)*100:.1f}% mean_sem={rg.get('mean_semantic',0)*100:.1f}%")
    if hg:
        print(f"    hieroglyph accuracy={hg.get('accuracy',0)*100:.1f}%")
    if ho:
        print(
            f"    classical train_closed={float(ho.get('train_closed_exact') or 0)*100:.1f}% "
            f"test_open_partial={float(ho.get('test_open_partial_gapfill') or ho.get('test_open_exact') or 0)*100:.1f}% "
            f"deployed={float(ho.get('deployed_full_closed_exact') or 0)*100:.1f}%"
        )

    LOCAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    DRIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    DRIVE_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  wrote {LOCAL_OUT}")
    print(f"  wrote {DRIVE_OUT}")
    return 0 if passed == total and not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
