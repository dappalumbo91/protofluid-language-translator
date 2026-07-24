#!/usr/bin/env python3
"""
FSOT automated pipeline — run the intrinsic methodology without manual agent loops.

See: docs/FSOT_INTRINSIC_METHODOLOGY.md

Default:
  python -u scripts/fsot_automate_pipeline.py

Options:
  --with-multi-deff   also run multi-D_eff spectrum (slower)
  --with-associate    also run sound+vision+meaning associate
  --update-metrics    patch release/hf/kaggle metrics_snapshot.json
  --skip-seed-push    skip main arrangement search (use existing report)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "pflt-Ada" / "reports"
LOCK = REP / "FSOT_PRODUCT_LOCK.json"
SEED_JSON = REP / "FSOT_SEED_PUSH.json"
METHOD = ROOT / "docs" / "FSOT_INTRINSIC_METHODOLOGY.md"


def run_script(rel: str, timeout_s: int = 7200) -> int:
    script = ROOT / rel
    if not script.is_file():
        print(f"MISSING {script}", flush=True)
        return 2
    print(f"\n>>> RUN {rel}", flush=True)
    t0 = time.perf_counter()
    r = subprocess.run(
        [sys.executable, "-u", str(script)],
        cwd=str(ROOT),
        timeout=timeout_s,
    )
    print(f"<<< EXIT {r.returncode} in {time.perf_counter()-t0:.1f}s", flush=True)
    return int(r.returncode)


def verify_pin() -> Dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from fsot_law_bridge import verify_authority

    auth = verify_authority()
    print(
        f"pin_ok={auth.get('ok')} path={auth.get('path')} "
        f"sha={str(auth.get('sha256') or '')[:16]}…",
        flush=True,
    )
    if not auth.get("ok"):
        print("FATAL: pin D1D38A failed — refuse to rank without law", flush=True)
    return auth


def load_seed_report() -> Optional[Dict[str, Any]]:
    if not SEED_JSON.is_file():
        return None
    return json.loads(SEED_JSON.read_text(encoding="utf-8"))


def write_product_lock(seed: Dict[str, Any], auth: Dict[str, Any]) -> Dict[str, Any]:
    chosen = seed.get("chosen_product") or seed.get("best_product") or {}
    lock = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": "docs/FSOT_INTRINSIC_METHODOLOGY.md",
        "formula": "S = K*(T1+T2+T3)",
        "pin": "D1D38A",
        "pin_ok": bool(auth.get("ok")),
        "authority_path": auth.get("path"),
        "product_name": chosen.get("name") or "FSOT_unknown",
        "sacrebleu": chosen.get("sacrebleu"),
        "separation": chosen.get("separation"),
        "student_gen_max": seed.get("student_gen_max"),
        "beats_student": seed.get("beats_student"),
        "gap_to_DeepL_mid40": seed.get("gap_to_DeepL_mid40"),
        "gap_to_student_gen": seed.get("gap_to_student_gen"),
        "source_report": str(SEED_JSON.relative_to(ROOT)).replace("\\", "/"),
        "rule": "Students supply candidates; FSOT ranks with seeds only; no free params; no LLM product ranker",
    }
    REP.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    print(f"WROTE {LOCK}", flush=True)
    print(
        f"PRODUCT {lock['product_name']} sacre={lock['sacrebleu']} "
        f"beats_student={lock['beats_student']}",
        flush=True,
    )
    return lock


def update_metrics(lock: Dict[str, Any]) -> None:
    paths = [
        ROOT / "release" / "metrics_snapshot.json",
        ROOT / "huggingface_pflt" / "metrics_snapshot.json",
        ROOT / "kaggle_pflt" / "metrics_snapshot.json",
    ]
    name = lock.get("product_name") or "FSOT_product"
    sacre = lock.get("sacrebleu")
    student = lock.get("student_gen_max")
    for p in paths:
        if not p.is_file():
            print(f"skip metrics (missing) {p}", flush=True)
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        d["version"] = d.get("version", "0.3.0")
        # bump patch-ish version tag
        d["built_utc"] = datetime.now(timezone.utc).isoformat()
        d.setdefault("fsot", {})
        d["fsot"].update(
            {
                "law": "S=K(T1+T2+T3)",
                "pin": "D1D38A",
                "product": name,
                "methodology": "docs/FSOT_INTRINSIC_METHODOLOGY.md",
                "role": "Intrinsic seed ranking; students supply candidates only",
            }
        )
        w = d.setdefault("benchmarks", {}).setdefault("wmt14_deen", {})
        w["FSOT_best_product"] = sacre
        w[name] = sacre
        if student is not None:
            w["NLLB_3.3B_gen_max"] = student
        if sacre is not None:
            w["gap_FSOT_to_DeepL_mid40"] = round(40.0 - float(sacre), 2)
        if sacre is not None and student is not None:
            w["gap_FSOT_to_student_gen"] = round(float(student) - float(sacre), 2)
        w["product_note"] = (
            f"{name} via FSOT seed methodology; pin D1D38A; no free params; no LLM ranker"
        )
        d.setdefault("honesty", {})
        d["honesty"]["intrinsic_math_only"] = True
        d["honesty"]["stage"] = (
            f"{name} sacre={sacre}; student_gen={student}; methodology locked"
        )
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
        print(f"updated metrics {p.relative_to(ROOT)}", flush=True)


def write_run_summary(
    auth: Dict[str, Any],
    lock: Dict[str, Any],
    steps: List[str],
    ok: bool,
) -> Path:
    out = REP / "FSOT_PIPELINE_LAST_RUN.md"
    lines = [
        "# FSOT automated pipeline — last run",
        "",
        f"**UTC:** {datetime.now(timezone.utc).isoformat()}",
        f"**OK:** {ok}",
        f"**Methodology:** [`docs/FSOT_INTRINSIC_METHODOLOGY.md`](../../docs/FSOT_INTRINSIC_METHODOLOGY.md)",
        f"**Pin OK:** {auth.get('ok')}",
        "",
        "## Product lock",
        "",
        f"- **Name:** `{lock.get('product_name')}`",
        f"- **sacreBLEU:** **{lock.get('sacrebleu')}**",
        f"- **Beats student gen:** {lock.get('beats_student')}",
        f"- **Gap → DeepL mid-40:** {lock.get('gap_to_DeepL_mid40')}",
        f"- **Gap → student:** {lock.get('gap_to_student_gen')}",
        "",
        "## Steps",
        "",
    ]
    for s in steps:
        lines.append(f"- {s}")
    lines += [
        "",
        "## Reproduce",
        "",
        "```powershell",
        "cd C:\\Users\\damia\\Desktop\\pflt",
        "python -u scripts\\fsot_automate_pipeline.py --update-metrics",
        "```",
        "",
        "Do **not** git push / HF / Kaggle from this script (public publish is manual).",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {out}", flush=True)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="FSOT intrinsic pipeline automation")
    ap.add_argument("--with-multi-deff", action="store_true")
    ap.add_argument("--with-associate", action="store_true")
    ap.add_argument("--update-metrics", action="store_true")
    ap.add_argument("--skip-seed-push", action="store_true")
    args = ap.parse_args(argv)

    print("=== FSOT AUTOMATE PIPELINE ===", flush=True)
    print(f"methodology={METHOD if METHOD.is_file() else 'MISSING'}", flush=True)
    steps: List[str] = []

    auth = verify_pin()
    steps.append(f"verify_pin ok={auth.get('ok')}")
    if not auth.get("ok"):
        write_run_summary(auth, {}, steps, ok=False)
        return 1

    rc = 0
    if not args.skip_seed_push:
        r = run_script("scripts/fsot_seed_push.py")
        steps.append(f"fsot_seed_push exit={r}")
        rc = max(rc, r)
    else:
        steps.append("fsot_seed_push skipped")

    if args.with_multi_deff:
        r = run_script("scripts/fsot_multi_deff_language.py")
        steps.append(f"fsot_multi_deff_language exit={r}")
        rc = max(rc, r)

    if args.with_associate:
        r = run_script("scripts/fsot_associate_language.py")
        steps.append(f"fsot_associate_language exit={r}")
        rc = max(rc, r)

    seed = load_seed_report()
    if not seed:
        print("FATAL: no FSOT_SEED_PUSH.json — cannot lock product", flush=True)
        write_run_summary(auth, {}, steps, ok=False)
        return 1

    lock = write_product_lock(seed, auth)
    steps.append(f"product_lock {lock.get('product_name')} sacre={lock.get('sacrebleu')}")

    if args.update_metrics:
        update_metrics(lock)
        steps.append("metrics_snapshot updated (release/hf/kaggle packs)")

    write_run_summary(auth, lock, steps, ok=(rc == 0))
    print("=== DONE ===", flush=True)
    print(
        "Next (manual when you want public): git add/commit/push; "
        "hf upload; kaggle datasets version",
        flush=True,
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
