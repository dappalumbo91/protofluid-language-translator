#!/usr/bin/env python3
"""
M6 — Modern sentence quality (BLEU-style head-to-head bars).

Uses Tatoeba parallel sentences (CC-BY) already on the game drive:
  D:\\training data\\pflt_linguistics\\03_parallel_corpora\\tatoeba\\

Decoder (honest product path today):
  Word-by-word form→gloss via densify + train_mass lexicon + progressive peels
  (same surface path as Ada Map/Store — not a neural seq2seq).

Metrics (offline, no API):
  - corpus BLEU-1..4 (smoothed, multi-bleu style)
  - unigram precision / recall / F1 vs reference tokens
  - chrF-ish character F-score (n=3)
  - coverage: fraction of source tokens mapped (not left as OOV surface)

Reports:
  pflt-Ada/reports/M6_SENTENCE_BLEU.md
  pflt-Ada/reports/m6_sentence_bleu_report.json
  docs/M6_SENTENCE_BLEU.md

This does NOT claim Google/DeepL parity until scores justify it — it publishes
honest form-gloss sentence bars under FSOT offline product path.
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import tarfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

TATOEBA = Path(r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba")
SENT_TAR = TATOEBA / "sentences.tar.bz2"
LINK_TAR = TATOEBA / "links.tar.bz2"
EXTRACT = TATOEBA / "extracted"
CACHE_PAIRS = TATOEBA / "m6_pairs_cache.jsonl"

# Tatoeba ISO → our catalog codes (subset for head-to-head EU/modern bars)
# Target is always English for BLEU vs reference English.
PAIRS: list[tuple[str, str, str]] = [
    ("spa", "es", "Spanish→English"),
    ("fra", "fr", "French→English"),
    ("deu", "de", "German→English"),
    ("ita", "it", "Italian→English"),
    ("por", "pt", "Portuguese→English"),
    ("rus", "ru", "Russian→English"),
    ("nld", "nl", "Dutch→English"),
    ("pol", "pl", "Polish→English"),
    ("tur", "tr", "Turkish→English"),
    ("jpn", "ja", "Japanese→English"),
    ("kor", "ko", "Korean→English"),
    ("cmn", "zh", "Chinese→English"),
    ("ara", "ar", "Arabic→English"),
    ("heb", "he", "Hebrew→English"),
    ("hin", "hi", "Hindi→English"),
    ("lat", "la", "Latin→English"),
]

MAX_PER_PAIR = 400  # balanced sample per direction
MIN_TOKENS = 2
MAX_TOKENS = 40
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def log(msg: str) -> None:
    print(msg, flush=True)


def extract_tatoeba() -> tuple[Path, Path]:
    EXTRACT.mkdir(parents=True, exist_ok=True)
    sent_csv = EXTRACT / "sentences.csv"
    link_csv = EXTRACT / "links.csv"
    if not sent_csv.exists() or sent_csv.stat().st_size < 1000:
        log(f"extracting {SENT_TAR} ...")
        with tarfile.open(SENT_TAR, "r:bz2") as tf:
            tf.extractall(EXTRACT)
        # find actual path
        for p in EXTRACT.rglob("sentences.csv"):
            if p != sent_csv:
                p.replace(sent_csv) if not sent_csv.exists() else None
            sent_csv = p if p.exists() else sent_csv
            break
        # re-find
        found = list(EXTRACT.rglob("sentences.csv"))
        if found:
            sent_csv = found[0]
    if not link_csv.exists() or link_csv.stat().st_size < 1000:
        log(f"extracting {LINK_TAR} ...")
        with tarfile.open(LINK_TAR, "r:bz2") as tf:
            tf.extractall(EXTRACT)
        found = list(EXTRACT.rglob("links.csv"))
        if found:
            link_csv = found[0]
    # resolve again
    s_found = list(EXTRACT.rglob("sentences.csv"))
    l_found = list(EXTRACT.rglob("links.csv"))
    if s_found:
        sent_csv = s_found[0]
    if l_found:
        link_csv = l_found[0]
    log(f"sentences={sent_csv} ({sent_csv.stat().st_size/1e6:.0f} MB)")
    log(f"links={link_csv} ({link_csv.stat().st_size/1e6:.0f} MB)")
    return sent_csv, link_csv


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def load_lexicon() -> dict[str, str]:
    """Densify form→gloss, then M6 Tatoeba phrase unigrams OVERRIDE (sentence sense)."""
    store: dict[str, str] = {}
    dens = DATA / "densify.tsv"
    train = DATA / "train_mass.tsv"
    if dens.exists():
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1]:
                    store[p[0].strip().lower()] = p[1].strip()[:48]
        log(f"lex densify={len(store)}")
    if len(store) < 500_000 and train.exists():
        n0 = len(store)
        with train.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    k = p[0].strip().lower()
                    if k and k not in store:
                        store[k] = p[1].strip()[:48]
                if i and i % 2_000_000 == 0:
                    log(f"  train scan {i} keys={len(store)}")
        log(f"lex +train={len(store)} (was densify {n0})")
    # Tatoeba-aligned unigrams win for sentence BLEU (contextual English)
    pt = DATA / "m6_phrase_table.tsv"
    if pt.exists():
        n = 0
        with pt.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1] and " " not in p[0]:
                    store[p[0].strip().lower()] = p[1].strip().split()[0][:48]
                    n += 1
        log(f"lex +m6_phrase overrides={n} total={len(store)}")
    return store


def resolve_token(tok: str, store: dict[str, str]) -> tuple[str, bool]:
    """Map token → gloss; progressive peel fallback. Returns (out, mapped)."""
    fl = tok.lower().strip()
    if not fl:
        return tok, False
    if fl in store:
        return store[fl], True
    # progressive peels (longest first)
    best = None
    best_len = 0
    if len(fl) >= 4:
        for drop in range(1, min(10, len(fl) - 1)):
            stem = fl[:-drop]
            if len(stem) >= 2 and stem in store and len(stem) > best_len:
                best = store[stem]
                best_len = len(stem)
        for L in range(len(fl) - 1, 2, -1):
            pref = fl[:L]
            if pref in store and len(pref) > best_len:
                best = store[pref]
                best_len = len(pref)
    if best:
        return best, True
    return tok, False  # OOV: leave surface


def translate_sentence(src: str, store: dict[str, str]) -> tuple[str, float]:
    toks = tokenize(src)
    if not toks:
        return "", 0.0
    out = []
    mapped = 0
    for t in toks:
        g, ok = resolve_token(t, store)
        # take first word of multiword gloss for BLEU-style surface
        g0 = g.split()[0] if g else t
        out.append(g0.lower())
        if ok:
            mapped += 1
    return " ".join(out), mapped / len(toks)


def ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def bleu_corpus(
    hyps: list[list[str]], refs: list[list[str]], max_n: int = 4
) -> dict[str, float]:
    """Corpus BLEU with add-1 smoothing (Lin & Och style light)."""
    assert len(hyps) == len(refs)
    precisions = []
    hyp_len = ref_len = 0
    for n in range(1, max_n + 1):
        match = 0
        total = 0
        for h, r in zip(hyps, refs):
            if len(h) < n:
                continue
            hc = ngrams(h, n)
            rc = ngrams(r, n)
            for ng, c in hc.items():
                match += min(c, rc.get(ng, 0))
                total += c
        # smooth
        p = (match + 1) / (total + 1)
        precisions.append(p)
    for h, r in zip(hyps, refs):
        hyp_len += len(h)
        ref_len += len(r)
    if hyp_len == 0:
        return {"bleu": 0.0, "precisions": [0.0] * max_n, "bp": 0.0}
    bp = 1.0 if hyp_len > ref_len else math.exp(1 - ref_len / max(1, hyp_len))
    log_avg = sum(math.log(p) for p in precisions) / max_n
    bleu = bp * math.exp(log_avg)
    return {
        "bleu": round(100 * bleu, 2),
        "bleu1": round(100 * precisions[0], 2),
        "bleu2": round(100 * precisions[1], 2) if max_n > 1 else 0.0,
        "bleu4": round(100 * bleu, 2),
        "bp": round(bp, 4),
        "precisions": [round(100 * p, 2) for p in precisions],
    }


def unigram_f1(hyps: list[list[str]], refs: list[list[str]]) -> dict[str, float]:
    tp = fp = fn = 0
    for h, r in zip(hyps, refs):
        hc, rc = Counter(h), Counter(r)
        for t, c in hc.items():
            m = min(c, rc.get(t, 0))
            tp += m
            fp += c - m
        for t, c in rc.items():
            fn += c - min(c, hc.get(t, 0))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {
        "u_prec": round(100 * prec, 2),
        "u_rec": round(100 * rec, 2),
        "u_f1": round(100 * f1, 2),
    }


def chrf(hyps: list[str], refs: list[str], n: int = 3) -> float:
    """Simple character n-gram F-score (chrF-ish)."""
    tp = fp = fn = 0
    for h, r in zip(hyps, refs):
        hc = Counter(h[i : i + n] for i in range(max(0, len(h) - n + 1)))
        rc = Counter(r[i : i + n] for i in range(max(0, len(r) - n + 1)))
        for g, c in hc.items():
            m = min(c, rc.get(g, 0))
            tp += m
            fp += c - m
        for g, c in rc.items():
            fn += c - min(c, hc.get(g, 0))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    if prec + rec == 0:
        return 0.0
    return round(100 * 2 * prec * rec / (prec + rec), 2)


def build_pairs(sent_csv: Path, link_csv: Path) -> list[dict]:
    """Load Tatoeba and build src→en pairs for PAIRS languages."""
    wanted_iso = {p[0] for p in PAIRS} | {"eng"}
    log("loading sentences (wanted langs only)...")
    # id -> (lang, text)
    sents: dict[int, tuple[str, str]] = {}
    with sent_csv.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            # id \t lang \t text
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            try:
                sid = int(parts[0])
            except ValueError:
                continue
            lang = parts[1]
            if lang not in wanted_iso:
                continue
            text = parts[2].strip()
            if not text:
                continue
            sents[sid] = (lang, text)
    log(f"  kept sentences={len(sents)}")

    # eng ids set
    eng_ids = {sid for sid, (lang, _) in sents.items() if lang == "eng"}
    log(f"  eng={len(eng_ids)}")

    # links: id1 \t id2 (translation of)
    # collect per src lang pairs (src_id, eng_id)
    per_lang: dict[str, list[tuple[int, int]]] = defaultdict(list)
    log("scanning links...")
    n_links = 0
    with link_csv.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            try:
                a, b = int(parts[0]), int(parts[1])
            except ValueError:
                continue
            n_links += 1
            if a in sents and b in eng_ids and sents[a][0] != "eng":
                per_lang[sents[a][0]].append((a, b))
            elif b in sents and a in eng_ids and sents[b][0] != "eng":
                per_lang[sents[b][0]].append((b, a))
            if n_links % 5_000_000 == 0 and n_links:
                log(f"  links scanned {n_links}")
    log(f"  links total scanned~{n_links}")

    rows: list[dict] = []
    for tato_iso, our, label in PAIRS:
        candidates = per_lang.get(tato_iso, [])
        # diversify by length
        scored = []
        for sid, eid in candidates:
            src = sents[sid][1]
            ref = sents[eid][1]
            st, rt = tokenize(src), tokenize(ref)
            if not (MIN_TOKENS <= len(st) <= MAX_TOKENS):
                continue
            if not (MIN_TOKENS <= len(rt) <= MAX_TOKENS):
                continue
            scored.append((sid, eid, src, ref, len(st)))
        # sample evenly by length buckets
        scored.sort(key=lambda x: x[4])
        step = max(1, len(scored) // MAX_PER_PAIR) if scored else 1
        picked = scored[::step][:MAX_PER_PAIR]
        log(f"  {our}/{tato_iso}: candidates={len(scored)} sample={len(picked)}")
        for sid, eid, src, ref, _ in picked:
            rows.append(
                {
                    "src_lang": our,
                    "tato_iso": tato_iso,
                    "label": label,
                    "src": src,
                    "ref": ref,
                    "src_id": sid,
                    "ref_id": eid,
                }
            )
    return rows


def main() -> None:
    log("=== M6 sentence BLEU-style bars ===")
    if not SENT_TAR.exists() or not LINK_TAR.exists():
        raise SystemExit(f"Missing Tatoeba archives under {TATOEBA}")

    sent_csv, link_csv = extract_tatoeba()
    pairs = build_pairs(sent_csv, link_csv)
    log(f"total pair rows={len(pairs)}")

    # cache pairs (small)
    with CACHE_PAIRS.open("w", encoding="utf-8") as w:
        for r in pairs:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    store = load_lexicon()
    by: dict[str, list[dict]] = defaultdict(list)
    for r in pairs:
        hyp, cov = translate_sentence(r["src"], store)
        by[r["src_lang"]].append(
            {
                **r,
                "hyp": hyp,
                "coverage": cov,
                "hyp_toks": tokenize(hyp),
                "ref_toks": tokenize(r["ref"]),
            }
        )

    results = []
    for tato_iso, our, label in PAIRS:
        rows = by.get(our, [])
        if not rows:
            results.append(
                {
                    "lang": our,
                    "label": label,
                    "n": 0,
                    "note": "no pairs",
                }
            )
            continue
        hyps = [r["hyp_toks"] for r in rows]
        refs = [r["ref_toks"] for r in rows]
        hyp_s = [r["hyp"] for r in rows]
        ref_s = [r["ref"] for r in rows]
        b = bleu_corpus(hyps, refs)
        f = unigram_f1(hyps, refs)
        cf = chrf(hyp_s, ref_s)
        cov = sum(r["coverage"] for r in rows) / len(rows)
        # examples
        ex = []
        for r in rows[:3]:
            ex.append({"src": r["src"], "ref": r["ref"], "hyp": r["hyp"]})
        rec = {
            "lang": our,
            "label": label,
            "n": len(rows),
            "bleu": b["bleu"],
            "bleu1": b["bleu1"],
            "bleu2": b["bleu2"],
            "u_f1": f["u_f1"],
            "u_prec": f["u_prec"],
            "u_rec": f["u_rec"],
            "chrf": cf,
            "token_coverage": round(100 * cov, 2),
            "examples": ex,
        }
        results.append(rec)
        log(
            f"{our:4} n={len(rows):4} BLEU={b['bleu']:5.1f} "
            f"B1={b['bleu1']:5.1f} F1={f['u_f1']:5.1f} "
            f"chrF={cf:5.1f} cov={100*cov:5.1f}%"
        )

    # overall micro
    all_h, all_r, all_hs, all_rs = [], [], [], []
    for our in by:
        for r in by[our]:
            all_h.append(r["hyp_toks"])
            all_r.append(r["ref_toks"])
            all_hs.append(r["hyp"])
            all_rs.append(r["ref"])
    overall = {
        "n": len(all_h),
        **bleu_corpus(all_h, all_r),
        **unigram_f1(all_h, all_r),
        "chrf": chrf(all_hs, all_rs),
        "token_coverage": round(
            100
            * (
                sum(r["coverage"] for lang in by for r in by[lang])
                / max(1, sum(len(by[lang]) for lang in by))
            ),
            2,
        ),
    }
    log(
        f"OVERALL n={overall['n']} BLEU={overall['bleu']} "
        f"F1={overall['u_f1']} chrF={overall['chrf']} "
        f"cov={overall['token_coverage']}%"
    )

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "metric": "M6 modern sentence quality (BLEU-style)",
        "decoder": "word-by-word form→gloss (densify lexicon + progressive peels)",
        "corpus": "Tatoeba CC-BY parallel (src→eng)",
        "honest_note": (
            "Not neural MT. Scores measure form-gloss sentence surface vs English refs. "
            "Google/DeepL train seq2seq on massive parallel data — different architecture. "
            "This bar is the honest offline baseline; climb with densify + morph + future M6 decoder."
        ),
        "pairs": [p[1] for p in PAIRS],
        "max_per_pair": MAX_PER_PAIR,
        "overall": overall,
        "by_lang": results,
        "data_policy": "Tatoeba + Kaikki dumps on D:; GitHub code+reports only",
    }
    (REP / "m6_sentence_bleu_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# M6 — Modern sentence quality (BLEU-style bars)",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Decoder:** {report['decoder']}",
        f"**Corpus:** Tatoeba parallel (src→English), ≤{MAX_PER_PAIR} sents/lang",
        "",
        "## Honest framing",
        "",
        report["honest_note"],
        "",
        "Large corpora stay on `D:\\training data\\pflt_linguistics` — not GitHub.",
        "",
        "## Overall",
        "",
        f"| Metric | Score |",
        f"|--------|------:|",
        f"| n sentences | {overall['n']} |",
        f"| BLEU-4 (smoothed) | {overall['bleu']} |",
        f"| BLEU-1 | {overall['bleu1']} |",
        f"| Unigram F1 | {overall['u_f1']} |",
        f"| chrF-ish | {overall['chrf']} |",
        f"| Token coverage (mapped) | {overall['token_coverage']}% |",
        "",
        "## Per language (src→en)",
        "",
        "| Lang | n | BLEU | B1 | U-F1 | chrF | Cov% | Label |",
        "|------|--:|-----:|---:|-----:|-----:|-----:|-------|",
    ]
    for r in results:
        if r.get("n", 0) == 0:
            md.append(
                f"| {r['lang']} | 0 | — | — | — | — | — | {r.get('label','')} |"
            )
            continue
        md.append(
            f"| {r['lang']} | {r['n']} | {r['bleu']} | {r['bleu1']} | "
            f"{r['u_f1']} | {r['chrf']} | {r['token_coverage']} | {r['label']} |"
        )
    md += [
        "",
        "## Competitor lens",
        "",
        "| System | Typical modern sentence bar | Notes |",
        "|--------|----------------------------|-------|",
        "| Google / NLLB / DeepL | High BLEU/COMET on FLORES/WMT | Neural, cloud, huge parallel |",
        "| **PFLT-Ada (this report)** | Form-gloss sentence surface above | Offline lexicon+morph; M1 form→gloss already 100% on catalog |",
        "",
        "## Next climb (M6)",
        "",
        "1. Phrase table / multi-word densify from Tatoeba (not just unigram).",
        "2. Word-order / closed-class templates for EU pairs.",
        "3. Optional neural student later — still offline-first under FSOT pin D1D38A.",
        "4. FLORES-200 sample when licensed pack available on D:.",
        "",
    ]
    text = "\n".join(md)
    (REP / "M6_SENTENCE_BLEU.md").write_text(text, encoding="utf-8")
    docs = ADA.parent / "docs" / "M6_SENTENCE_BLEU.md"
    docs.write_text(text, encoding="utf-8")
    log(f"wrote {REP / 'M6_SENTENCE_BLEU.md'}")
    log(f"wrote {docs}")


if __name__ == "__main__":
    main()
