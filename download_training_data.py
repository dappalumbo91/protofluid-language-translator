#!/usr/bin/env python3
"""
Download PFLT / FSOT linguistics training data to Game Hard Drive.

Target root: D:\\training data\\pflt_linguistics
Every download writes a provenance JSON next to the file.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"D:\training data\pflt_linguistics")
LOG_DIR = ROOT / "logs"
DESKTOP_PFLT = Path(r"C:\Users\damia\Desktop\pflt")
DESKTOP_DICT = Path(r"C:\Users\damia\Desktop\Dictionary")
DESKTOP_LING = Path(r"C:\Users\damia\Desktop\FSOT linguistics")

# (url, relative_dest, notes)
REMOTE_TARGETS: List[Tuple[str, str, str]] = [
    # Cognate / lineage — ASJP word lists (cross-linguistic, inheritance signal)
    (
        "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/forms.csv",
        "02_cognate_lineage/asjp/forms.csv",
        "ASJP CLDF forms (cognate/lineage substrate)",
    ),
    (
        "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/languages.csv",
        "02_cognate_lineage/asjp/languages.csv",
        "ASJP languages",
    ),
    (
        "https://raw.githubusercontent.com/lexibank/asjp/master/cldf/parameters.csv",
        "02_cognate_lineage/asjp/parameters.csv",
        "ASJP meaning parameters (Swadesh-like)",
    ),
    # Concepticon concept sets (meaning IDs across languages)
    (
        "https://raw.githubusercontent.com/concepticon/concepticon-data/master/concepticondata/conceptlists/Swadesh-1955-100.tsv",
        "02_cognate_lineage/concepticon/Swadesh-1955-100.tsv",
        "Swadesh 100 concept list",
    ),
    (
        "https://raw.githubusercontent.com/concepticon/concepticon-data/master/concepticondata/conceptlists/Swadesh-1952-200.tsv",
        "02_cognate_lineage/concepticon/Swadesh-1952-200.tsv",
        "Swadesh 200 concept list",
    ),
    # Parallel / multi — small high-signal OPUS sample via tatoeba (CC-BY)
    (
        "https://downloads.tatoeba.org/exports/sentences.tar.bz2",
        "03_parallel_corpora/tatoeba/sentences.tar.bz2",
        "Tatoeba sentences export (multilingual parallel seed)",
    ),
    (
        "https://downloads.tatoeba.org/exports/links.tar.bz2",
        "03_parallel_corpora/tatoeba/links.tar.bz2",
        "Tatoeba translation links",
    ),
    # Phoible phoneme inventories (human vocal pattern structure)
    (
        "https://raw.githubusercontent.com/phoible/dev/master/data/phoible.csv",
        "05_phonology_vocal/phoible/phoible.csv",
        "PHOIBLE phoneme inventory database",
    ),
    # UD documentation sample list (full treebanks are large; get docs + sample index)
    (
        "https://raw.githubusercontent.com/UniversalDependencies/docs/pages-source/_config.yml",
        "04_treebanks_ud/docs_config.yml",
        "UD docs config (index of treebanks)",
    ),
]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def write_provenance(dest: Path, meta: Dict[str, Any]) -> None:
    prov = dest.with_suffix(dest.suffix + ".provenance.json")
    prov.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def download(url: str, dest: Path, notes: str, timeout: int = 600) -> Dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "url": url,
        "dest": str(dest),
        "notes": notes,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "ok": False,
    }
    if dest.exists() and dest.stat().st_size > 0:
        result["ok"] = True
        result["skipped"] = True
        result["bytes"] = dest.stat().st_size
        result["sha256"] = sha256_file(dest)
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_provenance(dest, result)
        return result

    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PFLT-FSOT-training-downloader/1.0 (research; local archive)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out)
        tmp.replace(dest)
        result["ok"] = True
        result["bytes"] = dest.stat().st_size
        result["sha256"] = sha256_file(dest)
        result["http_status"] = getattr(resp, "status", None)
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_provenance(dest, result)
    return result


def copy_local(src: Path, dest: Path, notes: str) -> Dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta: Dict[str, Any] = {
        "source": str(src),
        "dest": str(dest),
        "notes": notes,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "ok": False,
        "kind": "local_copy",
    }
    try:
        if not src.exists():
            meta["error"] = "source missing"
        else:
            if src.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
            meta["ok"] = True
            if dest.is_file():
                meta["bytes"] = dest.stat().st_size
                meta["sha256"] = sha256_file(dest)
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    if dest.exists():
        write_provenance(dest if dest.is_file() else dest / "_DIR.provenance.json", meta)
    return meta


def stage_local_gold() -> List[Dict[str, Any]]:
    results = []
    pairs = [
        (
            DESKTOP_PFLT / "data" / "historical_gold_merged.json",
            ROOT / "01_historical_gold" / "historical_gold_merged.json",
            "Merged Tier A/B historical gold from pflt",
        ),
        (
            DESKTOP_DICT / "historical_linguistics_seed.json",
            ROOT / "01_historical_gold" / "historical_linguistics_seed.json",
            "Dictionary Tier A historical seed",
        ),
        (
            DESKTOP_DICT / "data" / "bridge_patterns" / "historical_validation_candidates_grc_la.json",
            ROOT / "01_historical_gold" / "historical_validation_candidates_grc_la.json",
            "Greek/Latin validation candidates",
        ),
        (
            DESKTOP_PFLT / "data" / "historical_eval_tier_a_only.json",
            ROOT / "01_historical_gold" / "historical_eval_tier_a_only.json",
            "Tier A closed-set accuracy report",
        ),
    ]
    # Optional: small Rosetta report if present
    for name in (
        "fsot_rosetta_canonical_report.txt",
        "fsot_language_rules.json",
    ):
        src = DESKTOP_LING / "data" / name
        if not src.exists():
            src = DESKTOP_LING / "fsot_rosetta_rs" / "resources" / name
        if src.exists():
            pairs.append(
                (
                    src,
                    ROOT / "08_rosetta_fsot" / src.name,
                    f"FSOT linguistics resource: {src.name}",
                )
            )
    for src, dest, notes in pairs:
        results.append(copy_local(src, dest, notes))
    return results


def export_dictionary_historical_slice() -> Dict[str, Any]:
    """Export historical_translation_pairs from Dictionary DB to Game Drive."""
    import sqlite3

    db = DESKTOP_DICT / "data" / "dictionary.db"
    dest = ROOT / "07_dictionary_exports" / "historical_translation_pairs.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta: Dict[str, Any] = {
        "source": str(db),
        "dest": str(dest),
        "notes": "SQLite historical_translation_pairs export",
        "ok": False,
    }
    if not db.exists():
        meta["error"] = "dictionary.db missing"
        return meta
    try:
        c = sqlite3.connect(str(db))
        cur = c.cursor()
        rows = cur.execute(
            """
            SELECT source_lang_code, source_word, target_lang_code, target_word,
                   gloss, confidence, page_ref
            FROM historical_translation_pairs
            """
        ).fetchall()
        c.close()
        with dest.open("w", encoding="utf-8") as f:
            for r in rows:
                rec = {
                    "source_lang": r[0],
                    "source_word": r[1],
                    "target_lang": r[2],
                    "target_word": r[3],
                    "gloss": r[4],
                    "confidence": r[5],
                    "page_ref": r[6],
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        meta["ok"] = True
        meta["n_rows"] = len(rows)
        meta["bytes"] = dest.stat().st_size
        meta["sha256"] = sha256_file(dest)
        write_provenance(dest, meta)
    except Exception as e:
        meta["error"] = f"{type(e).__name__}: {e}"
    return meta


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"download_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report: Dict[str, Any] = {
        "root": str(ROOT),
        "drive": "D: (game drive)",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "local_stage": [],
        "remote": [],
        "exports": [],
    }

    print(f"Root: {ROOT}")
    print("--- Staging local gold ---")
    report["local_stage"] = stage_local_gold()
    for r in report["local_stage"]:
        status = "OK" if r.get("ok") else "FAIL"
        print(f"  [{status}] {r.get('dest')} {r.get('error','')}")

    print("--- Dictionary historical export ---")
    exp = export_dictionary_historical_slice()
    report["exports"].append(exp)
    print(f"  [{'OK' if exp.get('ok') else 'FAIL'}] rows={exp.get('n_rows')} {exp.get('error','')}")

    print("--- Remote downloads ---")
    for url, rel, notes in REMOTE_TARGETS:
        dest = ROOT / rel
        print(f"  GET {url}")
        print(f"   -> {dest}")
        # Tatoeba full exports can be large; allow long timeout
        timeout = 1800 if "tatoeba" in url else 600
        r = download(url, dest, notes, timeout=timeout)
        report["remote"].append(r)
        if r.get("ok"):
            skip = " (cached)" if r.get("skipped") else ""
            print(f"   OK{skip} bytes={r.get('bytes')}")
        else:
            print(f"   FAIL {r.get('error')}")

    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    ok_r = sum(1 for x in report["remote"] if x.get("ok"))
    ok_l = sum(1 for x in report["local_stage"] if x.get("ok"))
    report["summary"] = {
        "remote_ok": ok_r,
        "remote_total": len(report["remote"]),
        "local_ok": ok_l,
        "local_total": len(report["local_stage"]),
    }
    log_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote log {log_path}")
    print(json.dumps(report["summary"], indent=2))
    return 0 if ok_r + ok_l > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
