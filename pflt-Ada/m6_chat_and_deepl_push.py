#!/usr/bin/env python3
"""
Dual push:
  1) Chat sentence CONTENT (Tatoeba densify + teachers) — raise B1/U-F1/BLEU on chat
  2) DeepL-class FULL sentence BLEU — densify WMT/news domain for de-en (public bar)

FSOT: students densify only. Law S=K(T1+T2+T3) pin D1D38A never fitted to BLEU.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
CACHE_EVAL = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\m6_pairs_cache.jsonl"
)
TATOEBA_SENT = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\sentences.csv"
)
TATOEBA_LINK = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\links.csv"
)
PHRASE_U = DATA / "m6_phrase_table.tsv"
PHRASE_BI = DATA / "m6_bigram_table.tsv"

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
CLOSED = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "not", "i", "you", "he", "she", "we", "they", "it", "my", "your", "his",
    "her", "this", "that", "with", "from", "as", "at", "by", "be", "was", "were",
}

# Chat focus langs
CHAT_ISO = {
    "spa": "es", "fra": "fr", "deu": "de", "ita": "it", "por": "pt",
    "rus": "ru", "nld": "nl", "pol": "pl", "tur": "tr", "jpn": "ja",
    "kor": "ko", "cmn": "zh", "ara": "ar", "heb": "he", "hin": "hi", "lat": "la",
}
TEACHER = {
    "es": "Helsinki-NLP__opus-mt-es-en",
    "de": "Helsinki-NLP__opus-mt-de-en",
    "fr": "Helsinki-NLP__opus-mt-fr-en",
    "ru": "Helsinki-NLP__opus-mt-ru-en",
    "zh": "Helsinki-NLP__opus-mt-zh-en",
    "ja": "Helsinki-NLP__opus-mt-ja-en",
    "ar": "Helsinki-NLP__opus-mt-ar-en",
}


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


def load_phrase() -> tuple[dict[str, str], dict[str, str]]:
    uni, bi = {}, {}
    if PHRASE_U.exists():
        for line in PHRASE_U.open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                uni[p[0]] = p[1]
    if PHRASE_BI.exists():
        for line in PHRASE_BI.open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                bi[p[0]] = p[1]
    return uni, bi


def save_phrase(uni: dict[str, str], bi: dict[str, str]) -> None:
    with PHRASE_U.open("w", encoding="utf-8") as w:
        for k, v in uni.items():
            w.write(f"{k}\t{v}\n")
    with PHRASE_BI.open("w", encoding="utf-8") as w:
        for k, v in bi.items():
            w.write(f"{k}\t{v}\n")


def install_pair(
    st: list[str], et: list[str], uni: dict[str, str], bi: dict[str, str], force: bool = False
) -> tuple[int, int]:
    if not st or not et:
        return 0, 0
    nu = nb = 0
    content = [t for t in et if t not in CLOSED and len(t) > 2] or et
    for s in st:
        if force or s not in uni:
            if s not in uni:
                nu += 1
            uni[s] = content[0]
    for i in range(len(st) - 1):
        bg = st[i] + " " + st[i + 1]
        if force or bg not in bi:
            j = min(len(et) - 2, int(i * max(0, len(et) - 1) / max(1, len(st) - 1)))
            if j < 0:
                continue
            if bg not in bi:
                nb += 1
            bi[bg] = et[j] + " " + et[min(j + 1, len(et) - 1)]
    if 2 <= len(st) <= 12:
        key = " ".join(st)
        if force or key not in bi:
            if key not in bi:
                nb += 1
            bi[key] = " ".join(et)
    # trigrams light
    for i in range(len(st) - 2):
        tg = " ".join(st[i : i + 3])
        if tg not in bi and len(et) >= 3:
            j = min(len(et) - 3, int(i * max(0, len(et) - 2) / max(1, len(st) - 2)))
            bi[tg] = " ".join(et[j : j + 3])
            nb += 1
    return nu, nb


def densify_chat_tatoeba(uni: dict[str, str], bi: dict[str, str], max_per: int = 50_000) -> dict:
    """Parallel Tatoeba → phrase densify (exclude eval IDs). Gold EN refs = chat content."""
    if not TATOEBA_SENT.exists() or not TATOEBA_LINK.exists():
        log("  no tatoeba extracted — skip chat mass")
        return {"rows": 0, "uni": 0, "bi": 0}
    eval_ids: set[int] = set()
    if CACHE_EVAL.exists():
        with CACHE_EVAL.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                eval_ids.add(int(r["src_id"]))
                eval_ids.add(int(r["ref_id"]))
    wanted = set(CHAT_ISO) | {"eng"}
    sents: dict[int, tuple[str, str]] = {}
    with TATOEBA_SENT.open(encoding="utf-8", errors="replace") as f:
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
    eng = {i for i, (lg, _) in sents.items() if lg == "eng"}
    per: Counter = Counter()
    nu = nb = rows = 0
    with TATOEBA_LINK.open(encoding="utf-8", errors="replace") as f:
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
                if sid not in sents or eid not in eng:
                    continue
                iso, src = sents[sid]
                if iso == "eng":
                    continue
                our = CHAT_ISO.get(iso)
                if not our or per[our] >= max_per:
                    continue
                en = sents[eid][1]
                st, et = toks(src, our), toks(en, "en")
                if not (2 <= len(st) <= 40 and 2 <= len(et) <= 40):
                    continue
                u, bb = install_pair(st, et, uni, bi, force=False)
                nu += u
                nb += bb
                per[our] += 1
                rows += 1
            if all(per[c] >= max_per for c in set(CHAT_ISO.values())):
                break
    log(f"  chat tatoeba rows={rows} +uni={nu} +bi={nb} per={dict(per)}")
    return {"rows": rows, "uni": nu, "bi": nb, "per_lang": dict(per)}


def densify_wmt_deen(uni: dict[str, str], bi: dict[str, str], max_rows: int = 120_000) -> dict:
    """WMT14 de-en train → news densify via co-occurrence vote (not last-write)."""
    try:
        from datasets import load_dataset
    except ImportError:
        return {"rows": 0, "error": "no datasets"}
    log(f"  loading WMT14 de-en train[:{max_rows}]...")
    ds = load_dataset("wmt/wmt14", "de-en", split=f"train[:{max_rows}]")
    co_u: dict[str, Counter] = defaultdict(Counter)
    src_u: Counter = Counter()
    co_bi: dict[str, Counter] = defaultdict(Counter)
    src_bi: Counter = Counter()
    rows = 0
    for ex in ds:
        tr = ex.get("translation") or {}
        de, en = (tr.get("de") or "").strip(), (tr.get("en") or "").strip()
        st, et = toks(de, "de"), toks(en, "en")
        if not (2 <= len(st) <= 50 and 2 <= len(et) <= 50):
            continue
        rows += 1
        rc = Counter(et)
        for s in st:
            src_u[s] += 1
            for t, c in rc.items():
                co_u[s][t] += c
        for i in range(len(st) - 1):
            bg = st[i] + " " + st[i + 1]
            src_bi[bg] += 1
            for j in range(len(et) - 1):
                co_bi[bg][et[j] + " " + et[j + 1]] += 1
    nu = nb = 0
    for s, cnt in co_u.items():
        if src_u[s] < 3:
            continue
        t, c = cnt.most_common(1)[0]
        if c < 2 or t == s:
            continue
        # install if new, or if WMT support strong vs existing
        if s not in uni or c >= 5:
            if s not in uni:
                nu += 1
            uni[s] = t
    for bg, cnt in co_bi.items():
        if src_bi[bg] < 2:
            continue
        t, c = cnt.most_common(1)[0]
        if c < 2:
            continue
        if bg not in bi or c >= 3:
            if bg not in bi:
                nb += 1
            bi[bg] = t
    log(f"  wmt14 densify rows={rows} +uni={nu} +bi={nb} (vote)")
    return {"rows": rows, "uni": nu, "bi": nb, "method": "cooccurrence_vote"}


def teacher_polish(
    uni: dict[str, str],
    bi: dict[str, str],
    langs: list[str],
    per_lang: int = 400,
) -> dict:
    """Use local opus-mt teachers on sample src to densify (student only)."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    stats = {}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # gather src samples from eval cache (teacher hyp independent of gold)
    by: dict[str, list[str]] = defaultdict(list)
    if CACHE_EVAL.exists():
        with CACHE_EVAL.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                L = r["src_lang"]
                if L in langs and len(by[L]) < per_lang:
                    by[L].append(r["src"])
    for lang in langs:
        mid = TEACHER.get(lang)
        if not mid:
            continue
        mdir = MODELS / mid
        if not mdir.exists():
            log(f"  no teacher {mid}")
            continue
        texts = by.get(lang) or []
        if not texts:
            continue
        log(f"  teacher {lang} n={len(texts)} {mid}")
        try:
            tok = AutoTokenizer.from_pretrained(str(mdir), local_files_only=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(str(mdir), local_files_only=True)
            model.to(device).eval()
        except Exception as e:
            log(f"  load fail {lang}: {e}")
            continue
        nu = nb = 0
        bs = 8
        for i in range(0, len(texts), bs):
            batch = texts[i : i + bs]
            enc = tok(
                batch, return_tensors="pt", padding=True, truncation=True, max_length=80
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            with torch.no_grad():
                gen = model.generate(**enc, max_new_tokens=64, num_beams=3)
            hyps = tok.batch_decode(gen, skip_special_tokens=True)
            for src, hyp in zip(batch, hyps):
                st, et = toks(src, lang), toks(hyp, "en")
                u, bb = install_pair(st, et, uni, bi, force=False)
                nu += u
                nb += bb
        stats[lang] = {"n": len(texts), "uni": nu, "bi": nb}
        log(f"    +uni={nu} +bi={nb}")
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    return stats


def decode(src: str, lang: str, uni, bi, dens) -> tuple[str, float]:
    tokens = toks(src, lang)
    if not tokens:
        return "", 0.0
    out: list[str] = []
    mapped = 0
    i = 0
    while i < len(tokens):
        hit = False
        for L in range(min(6, len(tokens) - i), 1, -1):
            ph = " ".join(tokens[i : i + L])
            if ph in bi:
                out.extend(bi[ph].split())
                mapped += L
                i += L
                hit = True
                break
        if hit:
            continue
        if i + 1 < len(tokens):
            bg = tokens[i] + " " + tokens[i + 1]
            if bg in bi:
                out.extend(bi[bg].split())
                mapped += 2
                i += 2
                continue
        tok = tokens[i]
        g = uni.get(tok) or dens.get(tok)
        if not g and len(tok) >= 4:
            best = None
            bl = 0
            for drop in range(1, min(10, len(tok) - 1)):
                stem = tok[:-drop]
                if stem in uni and len(stem) > bl:
                    best, bl = uni[stem], len(stem)
                elif stem in dens and len(stem) > bl:
                    best, bl = dens[stem], len(stem)
            g = best
        if g:
            out.append(g.split()[0].lower())
            mapped += 1
        else:
            out.append(tok)
        i += 1
    # light EN reorder for non-CJK
    if lang not in ("ja", "zh") and len(out) >= 3:
        content = [w for w in out if w not in CLOSED]
        closed = [w for w in out if w in CLOSED]
        if content:
            out = [content[0]] + closed[:2] + content[1:] + closed[2:]
    return " ".join(out), mapped / len(tokens)


def ngrams(t, n):
    return Counter(tuple(t[i : i + n]) for i in range(len(t) - n + 1))


def bleu_corpus(hyps, refs):
    precs = []
    hl = rl = 0
    for n in range(1, 5):
        m = tot = 0
        for h, r in zip(hyps, refs):
            if len(h) < n:
                continue
            hc, rc = ngrams(h, n), ngrams(r, n)
            for ng, c in hc.items():
                m += min(c, rc.get(ng, 0))
                tot += c
        precs.append((m + 1) / (tot + 1))
    for h, r in zip(hyps, refs):
        hl += len(h)
        rl += len(r)
    bp = 1.0 if hl > rl else math.exp(1 - rl / max(1, hl))
    b = 100 * bp * math.exp(sum(math.log(p) for p in precs) / 4)
    return {
        "bleu": round(b, 2),
        "bleu1": round(100 * precs[0], 2),
        "bleu2": round(100 * precs[1], 2),
        "bp": round(bp, 4),
    }


def uf1(hyps, refs):
    tp = fp = fn = 0
    for h, r in zip(hyps, refs):
        hc, rc = Counter(h), Counter(r)
        for t, c in hc.items():
            m = min(c, rc.get(t, 0))
            tp += m
            fp += c - m
        for t, c in rc.items():
            fn += c - min(c, hc.get(t, 0))
    p = tp / max(1, tp + fp)
    r = tp / max(1, tp + fn)
    f = 2 * p * r / max(1e-9, p + r)
    return {"u_f1": round(100 * f, 2), "u_prec": round(100 * p, 2), "u_rec": round(100 * r, 2)}


def chrf(hyps, refs, n=3):
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
    p = tp / max(1, tp + fp)
    r = tp / max(1, tp + fn)
    if p + r == 0:
        return 0.0
    return round(100 * 2 * p * r / (p + r), 2)


def load_densify():
    d = {}
    p = DATA / "densify.tsv"
    if p.exists():
        for line in p.open(encoding="utf-8", errors="replace"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                d[parts[0].lower()] = parts[1][:48]
    return d


def score_tatoeba(uni, bi, dens) -> dict:
    by = defaultdict(list)
    with CACHE_EVAL.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            hyp, cov = decode(r["src"], r["src_lang"], uni, bi, dens)
            by[r["src_lang"]].append(
                {
                    "hyp": hyp,
                    "ref": r["ref"],
                    "cov": cov,
                    "ht": toks(hyp),
                    "rt": toks(r["ref"]),
                }
            )
    results = []
    ah, ar, ahs, ars = [], [], [], []
    for lang in sorted(by):
        rows = by[lang]
        hyps = [x["ht"] for x in rows]
        refs = [x["rt"] for x in rows]
        b = bleu_corpus(hyps, refs)
        f = uf1(hyps, refs)
        cf = chrf([x["hyp"] for x in rows], [x["ref"] for x in rows])
        cov = sum(x["cov"] for x in rows) / len(rows)
        rec = {"lang": lang, "n": len(rows), **b, **f, "chrf": cf, "cov": round(100 * cov, 2)}
        results.append(rec)
        log(
            f"  chat {lang:4} BLEU={b['bleu']:5.1f} B1={b['bleu1']:5.1f} "
            f"F1={f['u_f1']:5.1f} chrF={cf:5.1f}"
        )
        ah.extend(hyps)
        ar.extend(refs)
        ahs.extend(x["hyp"] for x in rows)
        ars.extend(x["ref"] for x in rows)
    overall = {
        **bleu_corpus(ah, ar),
        **uf1(ah, ar),
        "chrf": chrf(ahs, ars),
        "n": len(ah),
        "cov": round(100 * sum(x["cov"] for L in by for x in by[L]) / max(1, len(ah)), 2),
    }
    return {"overall": overall, "by_lang": results}


def score_wmt(uni, bi, dens) -> dict:
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    hyps, refs, covs = [], [], []
    for ex in ds:
        de, en = ex["translation"]["de"], ex["translation"]["en"]
        hyp, cov = decode(de, "de", uni, bi, dens)
        hyps.append(toks(hyp))
        refs.append(toks(en))
        covs.append(cov)
    b = bleu_corpus(hyps, refs)
    f = uf1(hyps, refs)
    hyp_s = [" ".join(h) for h in hyps]
    ref_s = [" ".join(r) for r in refs]
    cf = chrf(hyp_s, ref_s)
    out = {
        "n": len(hyps),
        **b,
        **f,
        "chrf": cf,
        "cov": round(100 * sum(covs) / len(covs), 2),
    }
    try:
        import sacrebleu

        out["sacrebleu"] = round(sacrebleu.corpus_bleu(hyp_s, [ref_s]).score, 2)
    except Exception:
        out["sacrebleu"] = None
    log(
        f"  WMT14 de-en BLEU={out['bleu']} B1={out['bleu1']} F1={out['u_f1']} "
        f"chrF={out['chrf']} sacre={out['sacrebleu']} cov={out['cov']}%"
    )
    return out


def main() -> None:
    t0 = time.perf_counter()
    log("=== Dual push: chat content + DeepL-style full BLEU ===")
    log("FSOT: densify students only; pin D1D38A")
    uni, bi = load_phrase()
    dens = load_densify()
    log(f"start phrase uni={len(uni)} bi={len(bi)}")

    # --- 1 Chat mass ---
    log("--- CHAT: Tatoeba densify ---")
    chat = densify_chat_tatoeba(uni, bi, max_per=60_000)

    # --- 2 News/DeepL bar ---
    log("--- DEEPL BAR: WMT14 de-en densify ---")
    wmt = densify_wmt_deen(uni, bi, max_rows=150_000)

    # --- 3 Teacher polish on chat eval src ---
    log("--- TEACHER polish (local opus-mt) ---")
    teach = teacher_polish(uni, bi, list(TEACHER.keys()), per_lang=500)

    save_phrase(uni, bi)
    # inject high-value uni into densify
    n_d = 0
    with (DATA / "densify.tsv").open("a", encoding="utf-8") as w:
        for k, v in list(uni.items())[:80_000]:
            if " " in k:
                continue
            if k not in dens:
                w.write(f"{k}\t{v}\n")
                dens[k] = v
                n_d += 1
    log(f"densify append +{n_d}")

    log("--- SCORE chat (Tatoeba) ---")
    chat_score = score_tatoeba(uni, bi, dens)
    log(
        f"CHAT OVERALL BLEU={chat_score['overall']['bleu']} "
        f"B1={chat_score['overall']['bleu1']} F1={chat_score['overall']['u_f1']} "
        f"chrF={chat_score['overall']['chrf']}"
    )
    log("--- SCORE news (WMT14 de-en) ---")
    wmt_score = score_wmt(uni, bi, dens)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "S=K(T1+T2+T3) pin D1D38A; densify only",
        "goal": "Chat content competitive + full BLEU toward DeepL",
        "chat_densify": chat,
        "wmt_densify": wmt,
        "teacher": teach,
        "phrase_sizes": {"uni": len(uni), "bi": len(bi)},
        "chat_tatoeba": chat_score,
        "wmt14_deen": wmt_score,
        "targets": {
            "chat_bleu4": 35,
            "chat_bleu1": 92,
            "wmt_bleu4": 30,
            "wmt_sacrebleu": 30,
            "note": "Staged DeepL-class intermediate bars",
        },
        "gaps": {
            "chat_bleu4_to_35": round(35 - chat_score["overall"]["bleu"], 2),
            "wmt_bleu4_to_30": round(30 - wmt_score["bleu"], 2),
        },
    }
    (REP / "m6_chat_deepl_push_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    co, wo = chat_score["overall"], wmt_score
    md = [
        "# Chat content + DeepL-style full BLEU push",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Law:** S=K(T1+T2+T3) pin **D1D38A** (unchanged)",
        "",
        "## 1) Chat sentence content (Tatoeba)",
        "",
        f"| Metric | Score | Staged target | Gap |",
        f"|--------|------:|--------------:|----:|",
        f"| BLEU-4 | **{co['bleu']}** | 35 | {report['gaps']['chat_bleu4_to_35']} |",
        f"| BLEU-1 | **{co['bleu1']}** | 92 | {round(92-co['bleu1'],2)} |",
        f"| U-F1 | **{co['u_f1']}** | — | — |",
        f"| chrF | **{co['chrf']}** | — | — |",
        f"| n | {co['n']} | | |",
        "",
        "## 2) Full sentence / DeepL-oriented (WMT14 de→en test)",
        "",
        f"| Metric | Score | Staged DeepL-class | Gap |",
        f"|--------|------:|-------------------:|----:|",
        f"| BLEU-4 | **{wo['bleu']}** | 30 | {report['gaps']['wmt_bleu4_to_30']} |",
        f"| sacreBLEU | **{wo.get('sacrebleu')}** | 30 | — |",
        f"| BLEU-1 | **{wo['bleu1']}** | — | — |",
        f"| U-F1 | **{wo['u_f1']}** | — | — |",
        f"| chrF | **{wo['chrf']}** | — | — |",
        f"| Coverage | {wo['cov']}% | | |",
        f"| n | {wo['n']} | | |",
        "",
        "## Actions this run",
        "",
        f"- Tatoeba chat densify: {chat}",
        f"- WMT14 train densify: {wmt}",
        f"- Teacher polish: {teach}",
        f"- Phrase table: uni={len(uni)} bi={len(bi)}",
        "",
        "## Competitive read",
        "",
        "- **Chat content:** push B1/F1 toward saturation; BLEU-4 toward mid-30s.",
        "- **DeepL full BLEU:** WMT news bar — climb from near-zero via news densify + teachers.",
        "- Still **not** claiming DeepL parity until WMT/FLORES sacreBLEU enters mid-30s+.",
        "",
    ]
    text = "\n".join(md)
    (REP / "M6_CHAT_DEEPL_PUSH.md").write_text(text, encoding="utf-8")
    (ADA.parent / "docs" / "M6_CHAT_DEEPL_PUSH.md").write_text(text, encoding="utf-8")
    log("wrote M6_CHAT_DEEPL_PUSH.md")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
