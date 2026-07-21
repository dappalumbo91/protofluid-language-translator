#!/usr/bin/env python3
"""
M6 HF fluency climb — use Hugging Face data + larger phrase mass for sentence parity.

FSOT law stays master. HF supplies:
  - OPUS Books / WMT-style parallel (train densify)
  - Optional NLLB teacher densify later
  - sacrebleu for industry-comparable BLEU

Eval remains held-out Tatoeba cache (m6_pairs_cache.jsonl) unless --flores path provided.

Storage: D:\\training data\\pflt_linguistics\\13_huggingface\\
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

HF_HOME = Path(r"D:\training data\pflt_linguistics\13_huggingface")
HF_HOME.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(HF_HOME))

CACHE_EVAL = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\m6_pairs_cache.jsonl"
)
PHRASE_U = DATA / "m6_phrase_table.tsv"
PHRASE_BI = DATA / "m6_bigram_table.tsv"
ORDER_TAB = DATA / "m6_order_hints.tsv"  # src_lang \t pattern notes

# Helsinki-NLP/opus_books config names (as listed on Hub; not always en-xx)
OPUS_PAIRS = [
    ("en-es", "es"),
    ("en-fr", "fr"),
    ("de-en", "de"),
    ("de-es", "es"),
    ("de-fr", "fr"),
    ("de-it", "it"),
    ("de-nl", "nl"),
    ("de-pt", "pt"),
    ("ca-en", "ca"),
    ("de-hu", "hu"),
]

TRAIN_PER_PAIR = 40_000  # OPUS rows per pair (src side)
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(text: str, lang: str = "") -> list[str]:
    t = text or ""
    if lang in ("ja", "zh", "ko") or CJK_RE.search(t):
        spaced = [x.lower() for x in TOKEN_RE.findall(t)]
        if spaced and any(len(x) > 1 for x in spaced):
            return spaced
        return [ch for ch in t if not ch.isspace() and (CJK_RE.match(ch) or ch.isalnum())]
    return [x.lower() for x in TOKEN_RE.findall(t)]


def load_opus_pairs() -> list[tuple[str, str, str]]:
    """Return (our_lang, src_text, eng_text) from Helsinki-NLP/opus_books via HF."""
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise SystemExit("pip install datasets") from e

    token = os.environ.get("HF_TOKEN")
    rows: list[tuple[str, str, str]] = []
    for cfg, our in OPUS_PAIRS:
        try:
            # direction often en-xx with translation.en / translation.xx
            ds = load_dataset(
                "Helsinki-NLP/opus_books",
                cfg,
                split=f"train[:{TRAIN_PER_PAIR}]",
                token=token,
            )
        except Exception as e:
            log(f"  skip opus {cfg}: {e}")
            continue
        n = 0
        for ex in ds:
            tr = ex.get("translation") or {}
            en = (tr.get("en") or "").strip()
            # other key is not en
            src = ""
            for k, v in tr.items():
                if k != "en" and v:
                    src = str(v).strip()
                    break
            if not en or not src:
                continue
            if len(toks(src, our)) < 2 or len(toks(en, "en")) < 2:
                continue
            el, sl = en.lower(), src.lower()
            if "gutenberg" in el or "wikisource" in el or el.startswith("source:"):
                continue
            if sl.startswith("source:"):
                continue
            rows.append((our, src, en))
            n += 1
        log(f"  opus {cfg} → {our}: +{n}")
    # WMT14 German↔English (classic public bar)
    try:
        ds = load_dataset(
            "wmt/wmt14",
            "de-en",
            split=f"train[:{min(TRAIN_PER_PAIR, 80_000)}]",
            token=token,
        )
        n = 0
        for ex in ds:
            tr = ex.get("translation") or {}
            de, en = (tr.get("de") or "").strip(), (tr.get("en") or "").strip()
            if de and en and len(toks(de, "de")) >= 2 and len(toks(en, "en")) >= 2:
                rows.append(("de", de, en))
                n += 1
        log(f"  wmt14 de-en → de: +{n}")
    except Exception as e:
        log(f"  skip wmt14: {e}")
    return rows


def load_tatoeba_train_extra(max_per: int = 30_000) -> list[tuple[str, str, str]]:
    """Extra mass from already-extracted Tatoeba (exclude eval IDs)."""
    sent = Path(
        r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\sentences.csv"
    )
    link = Path(
        r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\links.csv"
    )
    if not sent.exists() or not link.exists():
        return []
    eval_ids: set[int] = set()
    if CACHE_EVAL.exists():
        with CACHE_EVAL.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                eval_ids.add(int(r["src_id"]))
                eval_ids.add(int(r["ref_id"]))
    iso_map = {
        "spa": "es",
        "fra": "fr",
        "deu": "de",
        "ita": "it",
        "por": "pt",
        "rus": "ru",
        "nld": "nl",
        "pol": "pl",
        "tur": "tr",
        "jpn": "ja",
        "kor": "ko",
        "cmn": "zh",
        "ara": "ar",
        "heb": "he",
        "hin": "hi",
        "lat": "la",
    }
    wanted = set(iso_map) | {"eng"}
    sents: dict[int, tuple[str, str]] = {}
    with sent.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            try:
                sid = int(p[0])
            except ValueError:
                continue
            if p[1] not in wanted:
                continue
            sents[sid] = (p[1], p[2].strip())
    eng_ids = {i for i, (lg, _) in sents.items() if lg == "eng"}
    per: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with link.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 2:
                continue
            try:
                a, b = int(p[0]), int(p[1])
            except ValueError:
                continue
            for sid, eid in ((a, b), (b, a)):
                if sid in eval_ids or eid in eval_ids:
                    continue
                if sid not in sents or eid not in eng_ids:
                    continue
                iso, src = sents[sid]
                if iso == "eng":
                    continue
                our = iso_map.get(iso)
                if not our or len(per[our]) >= max_per:
                    continue
                eng = sents[eid][1]
                st, et = toks(src, our), toks(eng, "en")
                if 2 <= len(st) <= 40 and 2 <= len(et) <= 40:
                    per[our].append((src, eng))
            if all(len(per.get(v, [])) >= max_per for v in iso_map.values()):
                break
    rows = []
    for our, pairs in per.items():
        log(f"  tatoeba extra {our}: {len(pairs)}")
        for src, eng in pairs:
            rows.append((our, src, eng))
    return rows


def build_tables(rows: list[tuple[str, str, str]]) -> tuple[dict[str, str], dict[str, str]]:
    co_u: dict[str, Counter] = defaultdict(Counter)
    src_u: Counter = Counter()
    co_bi: dict[str, Counter] = defaultdict(Counter)
    src_bi: Counter = Counter()
    # simple order: fraction of times src unigram appears before another (for reorder hints)
    for our, src, eng in rows:
        st, et = toks(src, our), toks(eng, "en")
        if not st or not et:
            continue
        rc = Counter(et)
        for s in st:
            src_u[s] += 1
            for t, c in rc.items():
                co_u[s][t] += c
        for i in range(len(st) - 1):
            bg = st[i] + " " + st[i + 1]
            best = None
            best_s = -1
            for j in range(len(et) - 1):
                sc = co_u[st[i]][et[j]] + co_u[st[i + 1]][et[j + 1]] + 1
                if sc > best_s:
                    best_s = sc
                    best = et[j] + " " + et[j + 1]
            if best:
                co_bi[bg][best] += 1
                src_bi[bg] += 1
            for t in et:
                if co_u[st[i]][t] + co_u[st[i + 1]][t] >= 2:
                    co_bi[bg][t] += 1

    uni: dict[str, str] = {}
    for s, cnt in co_u.items():
        if src_u[s] < 4:
            continue
        t, c = cnt.most_common(1)[0]
        if c < 3 or t == s or len(t) > 40:
            continue
        if c / src_u[s] < 0.06 and c < 15:
            continue
        uni[s] = t
    bi: dict[str, str] = {}
    for s, cnt in co_bi.items():
        if src_bi[s] < 3:
            continue
        t, c = cnt.most_common(1)[0]
        if c < 2 or len(t) > 48:
            continue
        bi[s] = t
    log(f"tables uni={len(uni)} bi={len(bi)}")
    return uni, bi


def merge_existing(uni: dict[str, str], bi: dict[str, str]) -> None:
    if PHRASE_U.exists():
        with PHRASE_U.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1] and p[0] not in uni:
                    uni[p[0]] = p[1]
    if PHRASE_BI.exists():
        with PHRASE_BI.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2 and p[0] and p[1] and p[0] not in bi:
                    bi[p[0]] = p[1]


def write_tables(uni: dict[str, str], bi: dict[str, str]) -> None:
    with PHRASE_U.open("w", encoding="utf-8") as w:
        for k, v in sorted(uni.items()):
            w.write(f"{k}\t{v}\n")
    with PHRASE_BI.open("w", encoding="utf-8") as w:
        for k, v in sorted(bi.items()):
            w.write(f"{k}\t{v}\n")
    log(f"wrote {PHRASE_U.name} ({len(uni)}) {PHRASE_BI.name} ({len(bi)})")


def load_densify() -> dict[str, str]:
    store: dict[str, str] = {}
    dens = DATA / "densify.tsv"
    if dens.exists():
        with dens.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    store[p[0].lower()] = p[1][:48]
    log(f"densify={len(store)}")
    return store


def decode(
    src: str, lang: str, dens: dict[str, str], uni: dict[str, str], bi: dict[str, str]
) -> tuple[str, float]:
    tokens = toks(src, lang)
    if not tokens:
        return "", 0.0
    out: list[str] = []
    mapped = 0
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            bg = tokens[i] + " " + tokens[i + 1]
            if bg in bi:
                out.extend(bi[bg].split())
                mapped += 2
                i += 2
                continue
        tok = tokens[i]
        hit = uni.get(tok) or dens.get(tok)
        if not hit and len(tok) >= 4:
            best = None
            bl = 0
            for drop in range(1, min(10, len(tok) - 1)):
                stem = tok[:-drop]
                if stem in uni and len(stem) > bl:
                    best, bl = uni[stem], len(stem)
                elif stem in dens and len(stem) > bl:
                    best, bl = dens[stem], len(stem)
            hit = best
        if hit:
            out.append(hit.split()[0].lower())
            mapped += 1
        else:
            out.append(tok)
        i += 1
    return " ".join(out), mapped / len(tokens)


def ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def bleu_corpus(hyps: list[list[str]], refs: list[list[str]], max_n: int = 4) -> dict:
    precisions = []
    hyp_len = ref_len = 0
    for n in range(1, max_n + 1):
        match = total = 0
        for h, r in zip(hyps, refs):
            if len(h) < n:
                continue
            hc, rc = ngrams(h, n), ngrams(r, n)
            for ng, c in hc.items():
                match += min(c, rc.get(ng, 0))
                total += c
        precisions.append((match + 1) / (total + 1))
    for h, r in zip(hyps, refs):
        hyp_len += len(h)
        ref_len += len(r)
    if hyp_len == 0:
        return {"bleu": 0.0, "bleu1": 0.0}
    bp = 1.0 if hyp_len > ref_len else math.exp(1 - ref_len / max(1, hyp_len))
    bleu = bp * math.exp(sum(math.log(p) for p in precisions) / max_n)
    return {
        "bleu": round(100 * bleu, 2),
        "bleu1": round(100 * precisions[0], 2),
        "bleu2": round(100 * precisions[1], 2),
        "bp": round(bp, 4),
    }


def unigram_f1(hyps: list[list[str]], refs: list[list[str]]) -> dict:
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


def sacrebleu_corpus(hyps: list[str], refs: list[str]) -> float | None:
    try:
        import sacrebleu

        return round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)
    except Exception:
        return None


def score_eval(uni: dict[str, str], bi: dict[str, str], dens: dict[str, str]) -> dict:
    if not CACHE_EVAL.exists():
        raise SystemExit("missing m6_pairs_cache — run m6_sentence_bleu.py first")
    by: dict[str, list] = defaultdict(list)
    with CACHE_EVAL.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            lang = r["src_lang"]
            hyp, cov = decode(r["src"], lang, dens, uni, bi)
            by[lang].append(
                {
                    "src": r["src"],
                    "ref": r["ref"],
                    "hyp": hyp,
                    "coverage": cov,
                    "hyp_toks": toks(hyp, "en"),
                    "ref_toks": toks(r["ref"], "en"),
                }
            )
    results = []
    all_h, all_r, all_hs, all_rs = [], [], [], []
    for lang in sorted(by.keys()):
        rows = by[lang]
        hyps = [x["hyp_toks"] for x in rows]
        refs = [x["ref_toks"] for x in rows]
        b = bleu_corpus(hyps, refs)
        f = unigram_f1(hyps, refs)
        cf = chrf([x["hyp"] for x in rows], [x["ref"] for x in rows])
        sb = sacrebleu_corpus([x["hyp"] for x in rows], [x["ref"] for x in rows])
        cov = sum(x["coverage"] for x in rows) / len(rows)
        rec = {
            "lang": lang,
            "n": len(rows),
            **b,
            **f,
            "chrf": cf,
            "sacrebleu": sb,
            "token_coverage": round(100 * cov, 2),
        }
        results.append(rec)
        log(
            f"{lang:4} n={len(rows):4} BLEU={b['bleu']:5.1f} B1={b['bleu1']:5.1f} "
            f"F1={f['u_f1']:5.1f} chrF={cf:5.1f} sacre={sb} cov={100*cov:5.1f}%"
        )
        all_h.extend(hyps)
        all_r.extend(refs)
        all_hs.extend(x["hyp"] for x in rows)
        all_rs.extend(x["ref"] for x in rows)
    overall = {
        "n": len(all_h),
        **bleu_corpus(all_h, all_r),
        **unigram_f1(all_h, all_r),
        "chrf": chrf(all_hs, all_rs),
        "sacrebleu": sacrebleu_corpus(all_hs, all_rs),
        "token_coverage": round(
            100
            * sum(x["coverage"] for lang in by for x in by[lang])
            / max(1, sum(len(by[lang]) for lang in by)),
            2,
        ),
    }
    log(
        f"OVERALL n={overall['n']} BLEU={overall['bleu']} F1={overall['u_f1']} "
        f"chrF={overall['chrf']} sacre={overall['sacrebleu']} "
        f"cov={overall['token_coverage']}%"
    )
    return {"overall": overall, "by_lang": results}


def main() -> None:
    t0 = time.perf_counter()
    log("=== M6 HF fluency climb (students under FSOT law) ===")
    log("HF data → phrase densify; S=K(T1+T2+T3) unchanged")
    rows: list[tuple[str, str, str]] = []
    # Primary: Tatoeba conversational (matches eval domain)
    log("loading Tatoeba extra (held-out from eval) — PRIMARY...")
    tat = load_tatoeba_train_extra(40_000)
    log(f"tatoeba rows={len(tat)}")
    uni, bi = build_tables(tat)
    merge_existing(uni, bi)
    # Secondary: OPUS/WMT literary+news — only fill OOV keys (avoid domain pollution)
    log("loading OPUS/WMT via Hugging Face — OOV fill only...")
    opus = load_opus_pairs()
    log(f"opus/wmt rows={len(opus)}")
    uni2, bi2 = build_tables(opus)
    n_fill = 0
    for k, v in uni2.items():
        if k not in uni:
            uni[k] = v
            n_fill += 1
    for k, v in bi2.items():
        if k not in bi:
            bi[k] = v
    log(f"OOV fill unigrams +{n_fill} (tatoeba preferred for overlap)")
    rows = tat + opus
    log(f"train rows total={len(rows)}")
    write_tables(uni, bi)
    dens = load_densify()
    # inject high-support unigrams into densify for Ada product path
    n_inj = 0
    with (DATA / "densify.tsv").open("a", encoding="utf-8") as w:
        for k, v in uni.items():
            if " " in k or len(k) > 24:
                continue
            if k not in dens:
                w.write(f"{k}\t{v}\n")
                dens[k] = v
                n_inj += 1
                if n_inj >= 50_000:
                    break
    log(f"densify +{n_inj} unigrams")
    score = score_eval(uni, bi, dens)
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "goal": "Sentence fluency climb toward Google/DeepL parity using HF data",
        "fsot": {
            "law": "S=K(T1+T2+T3)",
            "pin": "D1D38A",
            "role": "Law unchanged; HF OPUS/Tatoeba densify surface only",
        },
        "hf_assets_used": [
            "Helsinki-NLP/opus_books (parallel densify)",
            "local Tatoeba (D:)",
            "sacrebleu (when installed)",
        ],
        "hf_assets_blocked": [
            "facebook/flores — gated; accept license at huggingface.co/datasets/facebook/flores then re-run FLORES eval",
            "NLLB teacher — optional next: facebook/nllb-200-distilled-600M offline densify",
        ],
        "train_rows": len(rows),
        "uni": len(uni),
        "bi": len(bi),
        "overall": score["overall"],
        "by_lang": score["by_lang"],
        "next": [
            "User: accept FLORES-200 access on HF for industry eval",
            "Download NLLB-600M to D: as teacher densify student",
            "EU order model + CJK SentencePiece train",
            "Optional local neural decode under FSOT cert gate",
        ],
    }
    (REP / "m6_hf_fluency_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    o = score["overall"]
    md = [
        "# M6 HF fluency climb",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Train rows:** {len(rows)} (OPUS Books + Tatoeba held-out)",
        f"**Phrase table:** uni={len(uni)} bi={len(bi)}",
        "",
        "## FSOT",
        "",
        "Law \(S=K(T1+T2+T3)\) pin **D1D38A** unchanged. Hugging Face supplies parallel **data** (and later teacher models). Densify only.",
        "",
        "## Overall (Tatoeba held-out eval)",
        "",
        f"| Metric | Score |",
        f"|--------|------:|",
        f"| n | {o['n']} |",
        f"| BLEU-4 | {o['bleu']} |",
        f"| BLEU-1 | {o['bleu1']} |",
        f"| U-F1 | {o['u_f1']} |",
        f"| chrF | {o['chrf']} |",
        f"| sacreBLEU | {o.get('sacrebleu')} |",
        f"| Coverage | {o['token_coverage']}% |",
        "",
        "## Per language",
        "",
        "| Lang | n | BLEU | B1 | F1 | chrF | sacre | Cov% |",
        "|------|--:|-----:|---:|---:|-----:|------:|-----:|",
    ]
    for r in score["by_lang"]:
        md.append(
            f"| {r['lang']} | {r['n']} | {r['bleu']} | {r['bleu1']} | {r['u_f1']} | "
            f"{r['chrf']} | {r.get('sacrebleu')} | {r['token_coverage']} |"
        )
    md += [
        "",
        "## Hugging Face leverage",
        "",
        "| Asset | Status |",
        "|-------|--------|",
        "| OPUS Books | **used** for densify |",
        "| Tatoeba (D:) | **used** |",
        "| FLORES-200 | **blocked gated** — accept on Hub |",
        "| NLLB-600M teacher | **next** offline densify |",
        "| Gradio Space | needs HF PRO; model pack live |",
        "",
        "See `docs/HF_SENTENCE_FLUENCY_PLAN.md`.",
        "",
    ]
    text = "\n".join(md)
    (REP / "M6_HF_FLUENCY.md").write_text(text, encoding="utf-8")
    (ADA.parent / "docs" / "M6_HF_FLUENCY.md").write_text(text, encoding="utf-8")
    log("wrote M6_HF_FLUENCY.md")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
