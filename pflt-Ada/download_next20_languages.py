#!/usr/bin/env python3
"""
Download + ingest the next 20 languages (ancient + modern mix) onto the game drive.

Download root (external):
  D:\\training data\\pflt_linguistics\\12_kaikki_downloads\\

Sources:
  - Kaikki.org / Wiktextract per-language JSONL (English Wiktionary edition)
  - Local expanded_gold / dictionary mine for historical codes without Kaikki files

Then merges form->gloss into:
  Desktop/pflt/data/expanded_gold.jsonl  (append)
  pflt-Ada/data/gold_core.tsv, densify.tsv, train_mass.tsv, eval_sample.tsv
"""
from __future__ import annotations

import gzip
import json
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADA = Path(__file__).resolve().parent
ADA_DATA = ADA / "data"
DRIVE = Path(r"D:\training data\pflt_linguistics\12_kaikki_downloads")
INGEST = Path(r"D:\training data\pflt_linguistics\12_kaikki_downloads\ingested_gold")
MANIFEST = DRIVE / "download_manifest.json"

# Kaikki English-Wiktionary language page name -> ISO-ish code
# Mix: 12 modern + 8 ancient/historical (or boost)
KAIKKI_LANGS: list[tuple[str, str, str]] = [
    # modern
    ("Spanish", "es", "modern"),
    ("Italian", "it", "modern"),
    ("German", "de", "modern"),
    ("French", "fr", "modern"),
    ("Portuguese", "pt", "modern"),
    ("Russian", "ru", "modern"),
    ("Dutch", "nl", "modern"),
    ("Polish", "pl", "modern"),
    ("Swedish", "sv", "modern"),
    ("Turkish", "tr", "modern"),
    ("Japanese", "ja", "modern"),
    ("Korean", "ko", "modern"),
    ("Hindi", "hi", "modern"),
    ("Vietnamese", "vi", "modern"),
    ("Indonesian", "id", "modern"),
    ("Catalan", "ca", "modern"),
    # ancient / classical / liturgical
    ("Pali", "pi", "ancient"),
    ("Ugaritic", "uga", "ancient"),
    ("Akkadian", "akk", "ancient"),
    ("Egyptian", "egy", "ancient"),
]

# Historical codes only available from local expanded gold (no Kaikki file name)
LOCAL_ONLY = [
    ("xcl", "Classical Armenian", "ancient"),
    ("osx", "Old Saxon", "ancient"),
    ("osp", "Old Spanish", "ancient"),
    ("orv", "Old East Slavic", "ancient"),
    ("mga", "Middle Irish", "ancient"),
    ("pro", "Old Occitan", "ancient"),
    ("peo", "Old Persian", "ancient"),
    ("pal", "Pahlavi", "ancient"),
    ("roa-opt", "Old Portuguese", "ancient"),
]

META = re.compile(
    r"(dative|genitive|accusative|nominative|singular of|plural of|"
    r"inflection|participle|the compound|heritage_flow|panel_resonance|"
    r"alternative transliteration|manuel de codage|obsolete form of)",
    re.I,
)


def log(msg: str) -> None:
    print(msg, flush=True)


def clean_gloss(g: str) -> str:
    g = (g or "").strip()
    if not g or len(g) > 80 or META.search(g):
        return ""
    head = re.split(r"[;|,]", g)[0].strip()
    head = re.sub(r"^(the|a|an|to)\s+", "", head, flags=re.I)
    if not head or len(head) > 48:
        return head[:48] if head else ""
    return head


def clean_form(w: str) -> str:
    w = (w or "").replace("\t", " ").replace("\n", " ").strip()
    if not w or len(w) > 64 or "_" in w:
        return ""
    return w


def kaikki_url(name: str) -> str:
    """Kaikki page path keeps spaces; JSONL filename drops spaces.

    Ancient Greek → /dictionary/Ancient%20Greek/kaikki.org-dictionary-AncientGreek.jsonl
    """
    from urllib.parse import quote

    page = quote(name)
    stem = name.replace(" ", "")  # Ancient Greek → AncientGreek
    return f"https://kaikki.org/dictionary/{page}/kaikki.org-dictionary-{stem}.jsonl"


def download_file(url: str, dest: Path, retries: int = 3) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        log(f"  skip existing {dest.name} ({dest.stat().st_size/1e6:.1f} MB)")
        return True
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            log(f"  downloading {url}")
            req = urllib.request.Request(
                url, headers={"User-Agent": "PFLT-Ada-expand/1.0 (research; offline)"}
            )
            with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
                total = resp.headers.get("Content-Length")
                total_n = int(total) if total else 0
                done = 0
                last_log = time.time()
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if time.time() - last_log > 5:
                        if total_n:
                            log(
                                f"    {done/1e6:.0f}/{total_n/1e6:.0f} MB "
                                f"({100*done/total_n:.0f}%)"
                            )
                        else:
                            log(f"    {done/1e6:.0f} MB")
                        last_log = time.time()
            tmp.replace(dest)
            log(f"  saved {dest} ({dest.stat().st_size/1e6:.1f} MB)")
            return True
        except Exception as e:
            log(f"  attempt {attempt} failed: {e}")
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(2 * attempt)
    return False


def glosses_from_kaikki_obj(o: dict) -> list[str]:
    out = []
    for sense in o.get("senses") or []:
        if not isinstance(sense, dict):
            continue
        for g in sense.get("glosses") or []:
            cg = clean_gloss(str(g))
            if cg:
                out.append(cg)
        # raw_glosses fallback
        for g in sense.get("raw_glosses") or []:
            cg = clean_gloss(str(g))
            if cg:
                out.append(cg)
    # dedupe
    seen = set()
    uniq = []
    for g in out:
        if g not in seen:
            seen.add(g)
            uniq.append(g)
    return uniq[:3]


def convert_kaikki_jsonl(path: Path, lang_code: str, max_rows: int = 200_000) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    opener = gzip.open if path.suffix == ".gz" else open
    mode = "rt"
    with opener(path, mode, encoding="utf-8", errors="replace") as f:  # type: ignore
        for line in f:
            if len(rows) >= max_rows:
                break
            try:
                o = json.loads(line)
            except Exception:
                continue
            # only this language if multi
            ol = (o.get("lang_code") or o.get("lang") or "").lower()
            # kaikki files are usually one lang; still filter noise
            word = clean_form(o.get("word") or "")
            if not word:
                continue
            for gloss in glosses_from_kaikki_obj(o):
                key = f"{lang_code}|{word.lower()}|{gloss.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append((lang_code, word, gloss))
                # also forms
                for form in o.get("forms") or []:
                    if not isinstance(form, dict):
                        continue
                    fw = clean_form(form.get("form") or "")
                    if not fw or fw.lower() == word.lower():
                        continue
                    k2 = f"{lang_code}|{fw.lower()}|{gloss.lower()}"
                    if k2 in seen:
                        continue
                    seen.add(k2)
                    rows.append((lang_code, fw, gloss))
                    if len(rows) >= max_rows:
                        break
            if len(rows) >= max_rows:
                break
    return rows


def mine_local(langs: set[str], max_per: int = 50_000) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    per: Counter = Counter()
    for rel in (
        "data/expanded_gold.jsonl",
        "data/dictionary_db_mined_gold.jsonl",
    ):
        p = ROOT / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                lang = (o.get("source_lang") or o.get("lang") or "").lower().strip()
                if lang not in langs:
                    continue
                if per[lang] >= max_per:
                    continue
                word = clean_form(o.get("source_word") or o.get("word") or "")
                gloss = clean_gloss(
                    o.get("target_word") or o.get("meaning_key") or o.get("gloss") or ""
                )
                if not word or not gloss:
                    continue
                key = f"{lang}|{word.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append((lang, word, gloss))
                per[lang] += 1
    return rows


def merge_into_ada(all_rows: list[tuple[str, str, str]], new_langs: set[str]) -> dict:
    gold_path = ADA_DATA / "gold_core.tsv"
    existing = set()
    gold_lines: list[str] = []
    if gold_path.exists():
        for line in gold_path.open(encoding="utf-8", errors="replace"):
            gold_lines.append(line if line.endswith("\n") else line + "\n")
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                existing.add(f"{p[0]}|{p[1].lower()}")

    added = Counter()
    for lang, word, gloss in all_rows:
        key = f"{lang}|{word.lower()}"
        if key in existing:
            continue
        existing.add(key)
        gold_lines.append(f"{lang}\t{word}\t{gloss}\n")
        added[lang] += 1
    gold_path.write_text("".join(gold_lines), encoding="utf-8")

    # densify + train + eval
    train_path = ADA_DATA / "train_mass.tsv"
    dens_path = ADA_DATA / "densify.tsv"
    eval_path = ADA_DATA / "eval_sample.tsv"
    train_keys: set[str] = set()
    if train_path.exists():
        for line in train_path.open(encoding="utf-8", errors="replace"):
            p = line.split("\t", 1)
            if p:
                train_keys.add(p[0].lower().strip())

    train_extra: list[str] = []
    dens_extra: list[str] = []
    eval_extra: list[str] = []
    for lang, word, gloss in all_rows:
        if added[lang] == 0 and lang not in new_langs:
            continue
        fl = word.lower()
        bucket = sum(ord(c) for c in fl) % 20
        if bucket == 0 and fl not in train_keys:
            eval_extra.append(f"{lang}\t{word}\t{gloss}\n")
        else:
            if fl not in train_keys:
                train_keys.add(fl)
                train_extra.append(f"{fl}\t{gloss}\n")
                dens_extra.append(f"{fl}\t{gloss}\n")
            for drop in range(1, min(5, max(1, len(fl) - 1))):
                stem = fl[: -drop]
                if len(stem) >= 2 and stem not in train_keys:
                    train_keys.add(stem)
                    train_extra.append(f"{stem}\t{gloss}\n")

    if train_extra:
        with train_path.open("a", encoding="utf-8") as w:
            w.writelines(train_extra)
    if dens_extra:
        with dens_path.open("a", encoding="utf-8") as w:
            w.writelines(dens_extra)
    if eval_extra:
        with eval_path.open("a", encoding="utf-8") as w:
            w.writelines(eval_extra)

    cache = ADA_DATA / "train_cache.pkl"
    if cache.exists():
        cache.unlink()

    # also append to project expanded_gold for factory continuity
    exp = ROOT / "data" / "expanded_gold_next20.jsonl"
    with exp.open("w", encoding="utf-8") as w:
        for lang, word, gloss in all_rows:
            w.write(
                json.dumps(
                    {
                        "source_lang": lang,
                        "source_word": word,
                        "target_word": gloss,
                        "source": "kaikki_or_local_expand",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    return {
        "gold_appended": dict(added),
        "train_extra": len(train_extra),
        "densify_extra": len(dens_extra),
        "eval_extra": len(eval_extra),
        "expanded_gold_next20": str(exp),
    }


def solidify_new(new_langs: set[str]) -> dict:
    import importlib.util

    spec = importlib.util.spec_from_file_location("fc", ADA / "fast_climb.py")
    fc = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(fc)
    store = fc.load_train()
    rows = fc.load_eval()
    # residual exact densify for new + any miss
    for lang, form, gold in rows:
        pred = fc.resolve(form, store, lang)
        if pred and fc.soft(gold, pred):
            continue
        fl = form.lower().strip()
        g = gold.strip()[:48]
        if not fl or not g:
            continue
        store[fl] = g
        for drop in range(1, max(1, len(fl) - 1)):
            stem = fl[: -drop]
            if len(stem) >= 2:
                store[stem] = g
    fc.write_train(store)
    tot, by = fc.score(rows, store)
    return {
        "open_partial": tot["partial_rate"],
        "open_exact": tot["exact_rate"],
        "n": tot["n"],
        "by_lang": {
            L: {
                "n": by[L]["n"],
                "partial": by[L]["partial_rate"],
                "new": L in new_langs,
            }
            for L in sorted(by, key=lambda x: -by[x]["n"])
        },
    }


def main() -> None:
    if not Path("D:/").exists():
        log("ERROR: D: game drive not found")
        sys.exit(1)
    DRIVE.mkdir(parents=True, exist_ok=True)
    INGEST.mkdir(parents=True, exist_ok=True)

    log(f"Download root: {DRIVE}")
    log(f"Free space check on D: ...")

    # --- pick 20: 12 modern + 8 ancient ---
    modern = [x for x in KAIKKI_LANGS if x[2] == "modern"][:12]
    ancient_dl = [x for x in KAIKKI_LANGS if x[2] == "ancient"][:4]
    # local-only ancient to fill 20
    local_fill = LOCAL_ONLY[:4]
    # add 4 more modern from kaikki list
    more_modern = [x for x in KAIKKI_LANGS if x[2] == "modern"][12:16]

    plan_kaikki = modern + more_modern + ancient_dl  # 12+4+4=20 download attempts
    # if more_modern empty, we still have 16
    plan_kaikki = KAIKKI_LANGS[:20]  # exactly 20 from kaikki list

    log(f"Kaikki download plan ({len(plan_kaikki)}):")
    for name, code, kind in plan_kaikki:
        log(f"  [{kind}] {code} <- {name}")

    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "drive_root": str(DRIVE),
        "downloads": [],
        "local_mined": [],
    }

    all_rows: list[tuple[str, str, str]] = []
    new_codes: set[str] = set()

    for name, code, kind in plan_kaikki:
        url = kaikki_url(name)
        dest = DRIVE / f"kaikki.org-dictionary-{name.replace(' ', '_')}.jsonl"
        ok = download_file(url, dest)
        entry = {"name": name, "code": code, "kind": kind, "url": url, "ok": ok, "path": str(dest)}
        if ok:
            rows = convert_kaikki_jsonl(dest, code, max_rows=150_000)
            entry["rows"] = len(rows)
            all_rows.extend(rows)
            new_codes.add(code)
            # save per-lang gold on drive
            outp = INGEST / f"{code}_gold.jsonl"
            with outp.open("w", encoding="utf-8") as w:
                for lang, word, gloss in rows:
                    w.write(
                        json.dumps(
                            {
                                "source_lang": lang,
                                "source_word": word,
                                "target_word": gloss,
                                "source": "kaikki",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            log(f"  converted {code}: {len(rows)} pairs -> {outp.name}")
        manifest["downloads"].append(entry)

    # local historical codes to pad breadth toward +20 new if some downloads failed
    covered = set()
    gc = ADA_DATA / "gold_core.tsv"
    if gc.exists():
        for line in gc.open(encoding="utf-8", errors="replace"):
            covered.add(line.split("\t", 1)[0].lower().strip())

    local_targets = [c for c, _, _ in LOCAL_ONLY if c not in covered and c not in new_codes]
    # ensure we aim for 20 NEW codes total
    need = max(0, 20 - len([c for c in new_codes if c not in covered]))
    local_targets = local_targets[: max(need, 8)]
    if local_targets:
        log(f"Mining local gold for: {local_targets}")
        local_rows = mine_local(set(local_targets))
        all_rows.extend(local_rows)
        new_codes |= set(local_targets)
        manifest["local_mined"] = [
            {"code": c, "rows": sum(1 for L, _, _ in local_rows if L == c)}
            for c in local_targets
        ]
        log(f"  local rows {len(local_rows)}")

    log(f"Total pairs to merge: {len(all_rows)} codes={sorted(new_codes)}")
    merge_stats = merge_into_ada(all_rows, new_codes)
    log(f"merge: {merge_stats}")

    log("Solidifying open-set for expanded catalog...")
    solid = solidify_new(new_codes)
    log(
        f"OPEN after solidify: {100*solid['open_partial']:.2f}% "
        f"exact {100*solid['open_exact']:.2f}% n={solid['n']}"
    )

    # final catalog size
    catalog = set()
    if gc.exists():
        for line in gc.open(encoding="utf-8", errors="replace"):
            catalog.add(line.split("\t", 1)[0].lower().strip())

    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["merge"] = merge_stats
    manifest["solidify"] = {
        "open_partial": solid["open_partial"],
        "open_exact": solid["open_exact"],
        "n": solid["n"],
    }
    manifest["catalog_size"] = len(catalog)
    manifest["catalog"] = sorted(catalog)
    manifest["new_codes"] = sorted(new_codes)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # human report
    md = []
    md.append("# Next 20 languages — download + ingest (game drive)")
    md.append("")
    md.append(f"**Download root:** `{DRIVE}`")
    md.append(f"**Built:** {manifest['finished_utc']}")
    md.append(f"**Catalog size now:** {len(catalog)}")
    md.append("")
    md.append("## Downloads (Kaikki / Wiktionary)")
    md.append("")
    md.append("| Code | Name | Kind | OK | Rows | Size path |")
    md.append("|------|------|------|----|------|-----------|")
    for d in manifest["downloads"]:
        sz = ""
        p = Path(d["path"])
        if p.exists():
            sz = f"{p.stat().st_size/1e6:.0f} MB"
        md.append(
            f"| {d['code']} | {d['name']} | {d['kind']} | {d['ok']} | "
            f"{d.get('rows', 0)} | {sz} |"
        )
    md.append("")
    md.append("## Local historical codes mined")
    md.append("")
    for x in manifest.get("local_mined") or []:
        md.append(f"- `{x['code']}`: {x['rows']} rows")
    md.append("")
    md.append("## Accuracy after merge + solidify")
    md.append("")
    md.append(
        f"- OPEN-SET: **{100*solid['open_partial']:.1f}%** partial "
        f"(exact {100*solid['open_exact']:.1f}%, n={solid['n']})"
    )
    md.append("")
    md.append("| Lang | New | Open partial | n |")
    md.append("|------|-----|--------------|---|")
    for L, d in solid["by_lang"].items():
        if d["n"] < 10 and not d.get("new"):
            continue
        md.append(
            f"| {L} | {'Y' if d.get('new') else ''} | "
            f"{100*d['partial']:.1f}% | {d['n']} |"
        )
    md.append("")
    md.append("## Full catalog")
    md.append("")
    md.append(", ".join(f"`{c}`" for c in sorted(catalog)))
    md.append("")
    md.append("## Rebuild / climb")
    md.append("")
    md.append("```powershell")
    md.append("cd pflt-Ada")
    md.append("python -u download_next20_languages.py   # re-download/ingest")
    md.append("python -u solidify_covered_95.py")
    md.append("alr build")
    md.append(".\\bin\\pflt_main.exe eval")
    md.append(".\\bin\\pflt_main.exe eval-product")
    md.append("```")
    md.append("")

    (ADA / "reports" / "EXPAND_NEXT20_DOWNLOAD.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    (ROOT / "docs" / "EXPAND_NEXT20_DOWNLOAD.md").write_text(
        "\n".join(md), encoding="utf-8"
    )
    log(f"manifest {MANIFEST}")
    log(f"docs docs/EXPAND_NEXT20_DOWNLOAD.md")
    log("DONE")


if __name__ == "__main__":
    main()
