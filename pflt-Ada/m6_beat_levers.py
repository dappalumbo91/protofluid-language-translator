#!/usr/bin/env python3
"""
Work the levers left to beat commercial mid-bar under FSOT.

Law pin D1D38A fixed — students densify/decode/finetune only (never rewrite S).

Levers:
  L1  Product dual-student ensemble via length-normalized NLL (no ref peek)
  L2  Neural-first hybrid router (densify only classical/short high-quality)
  L3  WMT14 finetune of opus-mt-de-en student → rescore test

Writes: reports/m6_beat_levers_report.json, reports/BEAT_LEVERS.md
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
FT_OUT = MODELS / "Helsinki-NLP__opus-mt-de-en-wmt-ft"
CACHE = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\m6_pairs_cache.jsonl"
)

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")

# L2: densify only when classical / very short + high coverage
DENSIFY_CLASSICAL = {"la", "he"}  # neural weak historically
NEURAL_FORCE = {"ja", "zh", "ko", "hi", "ar", "ru", "de", "es", "fr", "it", "pt", "nl", "pl", "tr"}
SHORT_MAX = 6
COV_MIN = 0.95

SOTA = {"wmt_mid": 40.0, "wmt_stretch": 48.0, "chat_mid": 45.0}


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


def score_pairs(refs: list[str], hyps: list[str]) -> dict:
    ht = [toks(h) for h in hyps]
    rt = [toks(r) for r in refs]
    precs = []
    hl = rl = 0
    for n in range(1, 5):
        m = tot = 0
        for h, r in zip(ht, rt):
            if len(h) < n:
                continue
            hc = Counter(tuple(h[i : i + n]) for i in range(len(h) - n + 1))
            rc = Counter(tuple(r[i : i + n]) for i in range(len(r) - n + 1))
            for ng, c in hc.items():
                m += min(c, rc.get(ng, 0))
                tot += c
        precs.append((m + 1) / (tot + 1))
    for h, r in zip(ht, rt):
        hl += len(h)
        rl += len(r)
    bp = 1.0 if hl > rl else math.exp(1 - rl / max(1, hl))
    b = 100 * bp * math.exp(sum(math.log(p) for p in precs) / 4)
    try:
        import sacrebleu

        sb = round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)
        chrf = round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2)
    except Exception:
        sb = chrf = None
    return {
        "n": len(hyps),
        "bleu": round(b, 2),
        "bleu1": round(100 * precs[0], 2),
        "bp": round(bp, 4),
        "sacrebleu": sb,
        "chrf": chrf,
    }


def load_model(mdir: Path):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(mdir), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(mdir), local_files_only=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tok, model, device


def translate_scored(tok, model, device, texts, nllb_src=None, beams=5):
    """Return (hyps, length_norm_nll) — lower nll is better."""
    import torch
    import torch.nn.functional as F

    if nllb_src is not None and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    hyps: list[str] = []
    nlls: list[float] = []
    bs = 6 if nllb_src else 12
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        gen_kw = {
            "max_new_tokens": 160,
            "num_beams": beams,
            "length_penalty": 1.0,
            "early_stopping": True,
            "return_dict_in_generate": True,
            "output_scores": True,
        }
        if nllb_src is not None:
            try:
                gen_kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("eng_Latn")
            except Exception:
                pass
        with torch.no_grad():
            out = model.generate(**enc, **gen_kw)
        seqs = out.sequences
        # sequences_scores: higher is better (log probs); convert to -score / len
        if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
            scores = out.sequences_scores.detach().cpu().tolist()
        else:
            scores = [0.0] * len(batch)
        dec = tok.batch_decode(seqs, skip_special_tokens=True)
        for j, hyp in enumerate(dec):
            hyps.append(hyp)
            # length-normalized: sequences_scores already often length-penalized;
            # use -score so lower is better consistent with NLL
            sc = scores[j] if j < len(scores) else 0.0
            ln = max(1, len(toks(hyp)))
            nlls.append(-float(sc) / ln)
    return hyps, nlls


def hyp_nll(tok, model, device, src: str, hyp: str, nllb_src=None) -> float:
    """Teacher-forced NLL of hyp given src (lower better). Fallback scorer."""
    import torch

    if nllb_src is not None and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    enc = tok(src, return_tensors="pt", truncation=True, max_length=192)
    with tok.as_target_tokenizer() if hasattr(tok, "as_target_tokenizer") else nullctx():
        lab = tok(hyp, return_tensors="pt", truncation=True, max_length=160)
    # modern: text_target
    try:
        batch = tok(
            src,
            text_target=hyp,
            return_tensors="pt",
            truncation=True,
            max_length=192,
        )
    except TypeError:
        batch = {**enc, "labels": lab["input_ids"]}
    batch = {k: v.to(device) for k, v in batch.items()}
    with torch.no_grad():
        loss = model(**batch).loss
    return float(loss.item())


class nullctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def load_tables():
    uni, bi, dens = {}, {}, {}
    for path, d in (
        (DATA / "m6_phrase_table.tsv", uni),
        (DATA / "m6_bigram_table.tsv", bi),
    ):
        if path.exists():
            for line in path.open(encoding="utf-8", errors="replace"):
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    d[p[0]] = p[1]
    if (DATA / "densify.tsv").exists():
        for line in (DATA / "densify.tsv").open(encoding="utf-8", errors="replace"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                dens[p[0].lower()] = p[1][:48]
    return uni, bi, dens


def densify_decode(src, lang, uni, bi, dens):
    tokens = toks(src, lang)
    out = []
    i = 0
    while i < len(tokens):
        hit = False
        max_l = min(8, len(tokens) - i)
        for L in range(max_l, 1, -1):
            ph = " ".join(tokens[i : i + L])
            if ph in bi:
                out.extend(bi[ph].split())
                i += L
                hit = True
                break
        if hit:
            continue
        tok = tokens[i]
        g = uni.get(tok) or dens.get(tok)
        if g:
            out.append(g.split()[0].lower())
        elif tok.isascii() and tok.isalnum():
            out.append(tok.lower())
        i += 1
    return " ".join(out)


def densify_cov(src, lang, uni, dens):
    tokens = toks(src, lang)
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in uni or t in dens) / len(tokens)


def route_l2(lang, src, uni, dens) -> str:
    """Neural-first hybrid: densify only classical short high-cov."""
    if lang in NEURAL_FORCE or lang in ("ja", "zh"):
        return "neural"
    n = len(toks(src, lang))
    if lang in DENSIFY_CLASSICAL and n <= SHORT_MAX and densify_cov(src, lang, uni, dens) >= COV_MIN:
        return "densify"
    if n <= 4 and densify_cov(src, lang, uni, dens) >= 0.98:
        return "densify"
    return "neural"


# ---------- L1: WMT product ensemble ----------
def lever_wmt_ensemble_and_baseline() -> dict:
    from datasets import load_dataset

    log("L1: WMT product ensemble (score-based, no ref)...")
    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in ds]
    refs = [ex["translation"]["en"] for ex in ds]

    odir = MODELS / "Helsinki-NLP__opus-mt-de-en"
    ndir = MODELS / "facebook__nllb-200-distilled-600M"
    results = {}

    log("  opus-mt beams=5...")
    otok, omodel, odev = load_model(odir)
    o_hyps, o_nll = translate_scored(otok, omodel, odev, srcs, beams=5)
    results["opus_b5"] = score_pairs(refs, o_hyps)
    log(f"  opus sacre={results['opus_b5']['sacrebleu']}")

    log("  nllb beams=5...")
    ntok, nmodel, ndev = load_model(ndir)
    n_hyps, n_nll = translate_scored(
        ntok, nmodel, ndev, srcs, nllb_src="deu_Latn", beams=5
    )
    results["nllb_b5"] = score_pairs(refs, n_hyps)
    log(f"  nllb sacre={results['nllb_b5']['sacrebleu']}")

    # Product ensemble: pick lower length-norm nll
    ens = []
    picks = Counter()
    for oh, nh, on, nn in zip(o_hyps, n_hyps, o_nll, n_nll):
        if nn < on:
            ens.append(nh)
            picks["nllb"] += 1
        else:
            ens.append(oh)
            picks["opus"] += 1
    results["product_ensemble_nll"] = score_pairs(refs, ens)
    results["product_ensemble_nll"]["picks"] = dict(picks)
    log(
        f"  product ensemble sacre={results['product_ensemble_nll']['sacrebleu']} "
        f"picks={dict(picks)}"
    )

    # Oracle upper bound for comparison
    ens_o = []
    for oh, nh, r in zip(o_hyps, n_hyps, refs):
        # cheap: prefer higher unigram F1 vs ref without full sacre
        def uf1(h, ref):
            ht, rt = Counter(toks(h)), Counter(toks(ref))
            tp = sum(min(c, rt.get(t, 0)) for t, c in ht.items())
            p = tp / max(1, sum(ht.values()))
            r_ = tp / max(1, sum(rt.values()))
            return 2 * p * r_ / max(1e-9, p + r_)

        if uf1(nh, r) > uf1(oh, r):
            ens_o.append(nh)
        else:
            ens_o.append(oh)
    results["oracle_uf1_ensemble"] = score_pairs(refs, ens_o)
    log(f"  oracle uF1 ensemble sacre={results['oracle_uf1_ensemble']['sacrebleu']}")

    del omodel, nmodel
    return {
        "systems": results,
        "hyps_cache": {"opus": o_hyps, "nllb": n_hyps, "product_ens": ens},
        "refs": refs,
        "srcs": srcs,
    }


# ---------- L3: finetune ----------
def lever_wmt_finetune(
    max_train: int = 80000,
    steps: int = 3000,
    batch_size: int = 8,
    lr: float = 5e-5,
) -> dict:
    """Finetune opus-mt-de-en on WMT14 train; densify student under law."""
    import torch
    from datasets import load_dataset
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

    log(f"L3: WMT finetune opus-mt-de-en steps={steps} max_train={max_train}...")
    base = MODELS / "Helsinki-NLP__opus-mt-de-en"
    tok = AutoTokenizer.from_pretrained(str(base), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(base), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.train()

    log("  loading WMT14 train (stream/slice)...")
    ds = load_dataset("wmt/wmt14", "de-en", split="train")
    # take a slice for wall-clock
    n = min(max_train, len(ds))
    # stratified-ish: even spacing
    idxs = list(range(0, len(ds), max(1, len(ds) // n)))[:n]
    pairs = []
    for i in idxs:
        ex = ds[int(i)]
        pairs.append((ex["translation"]["de"], ex["translation"]["en"]))
    log(f"  train pairs={len(pairs)}")

    def collate(batch):
        srcs = [b[0] for b in batch]
        tgts = [b[1] for b in batch]
        try:
            enc = tok(
                srcs,
                text_target=tgts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            )
        except TypeError:
            enc = tok(srcs, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with tok.as_target_tokenizer():
                labs = tok(tgts, return_tensors="pt", padding=True, truncation=True, max_length=128)
            enc["labels"] = labs["input_ids"]
        return enc

    loader = DataLoader(pairs, batch_size=batch_size, shuffle=True, collate_fn=collate)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = min(steps, (len(pairs) // batch_size) * 3)
    sched = get_linear_schedule_with_warmup(
        opt, num_warmup_steps=max(1, total_steps // 20), num_training_steps=total_steps
    )

    step = 0
    losses = []
    t0 = time.perf_counter()
    while step < total_steps:
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            # replace pad in labels with -100
            if "labels" in batch:
                labels = batch["labels"]
                labels[labels == tok.pad_token_id] = -100
                batch["labels"] = labels
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            losses.append(float(loss.item()))
            step += 1
            if step % 100 == 0:
                avg = sum(losses[-100:]) / min(100, len(losses))
                log(f"  step {step}/{total_steps} loss={avg:.4f}")
            if step >= total_steps:
                break

    FT_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(FT_OUT))
    tok.save_pretrained(str(FT_OUT))
    log(f"  saved finetune student -> {FT_OUT}")

    # eval on test
    model.eval()
    ds_te = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in ds_te]
    refs = [ex["translation"]["en"] for ex in ds_te]
    hyps, _ = translate_scored(tok, model, device, srcs, beams=5)
    sc = score_pairs(refs, hyps)
    log(f"  finetuned opus WMT test sacre={sc['sacrebleu']}")
    del model
    return {
        "steps": total_steps,
        "train_pairs": len(pairs),
        "lr": lr,
        "avg_loss_last100": round(sum(losses[-100:]) / max(1, min(100, len(losses))), 4),
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "path": str(FT_OUT),
        "wmt_test": sc,
    }


# ---------- L2: neural-first hybrid chat ----------
def lever_hybrid_chat(max_per: int = 200) -> dict:
    log("L2: neural-first hybrid chat...")
    uni, bi, dens = load_tables()
    chat = defaultdict(list)
    if CACHE.exists():
        with CACHE.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                chat[r["src_lang"]].append((r["src"], r["ref"]))

    OPUS = {
        "es": "Helsinki-NLP__opus-mt-es-en",
        "de": "Helsinki-NLP__opus-mt-de-en",
        "fr": "Helsinki-NLP__opus-mt-fr-en",
        "ru": "Helsinki-NLP__opus-mt-ru-en",
        "zh": "Helsinki-NLP__opus-mt-zh-en",
        "ja": "Helsinki-NLP__opus-mt-ja-en",
        "ar": "Helsinki-NLP__opus-mt-ar-en",
    }
    NLLB = {
        "es": "spa_Latn",
        "de": "deu_Latn",
        "fr": "fra_Latn",
        "ru": "rus_Cyrl",
        "zh": "zho_Hans",
        "ja": "jpn_Jpan",
        "ar": "arb_Arab",
        "it": "ita_Latn",
        "pt": "por_Latn",
        "nl": "nld_Latn",
        "pl": "pol_Latn",
        "tr": "tur_Latn",
        "hi": "hin_Deva",
        "ko": "kor_Hang",
        "he": "heb_Hebr",
        "la": "lat_Latn",
    }
    ndir = MODELS / "facebook__nllb-200-distilled-600M"
    ntok = nmodel = ndev = None
    if (ndir / "pytorch_model.bin").exists() or (ndir / "model.safetensors").exists():
        ntok, nmodel, ndev = load_model(ndir)

    oh, or_ = [], []
    by = {}
    routes = Counter()
    for lang, pairs in sorted(chat.items()):
        pairs = pairs[:max_per]
        dens_i, neu_i = [], []
        for i, (s, r) in enumerate(pairs):
            path = route_l2(lang, s, uni, dens)
            routes[path] += 1
            (dens_i if path == "densify" else neu_i).append(i)
        hyps = [""] * len(pairs)
        for i in dens_i:
            hyps[i] = densify_decode(pairs[i][0], lang, uni, bi, dens)
        if neu_i:
            srcs = [pairs[i][0] for i in neu_i]
            neu_h = None
            if lang in OPUS and (MODELS / OPUS[lang]).exists():
                try:
                    t, m, d = load_model(MODELS / OPUS[lang])
                    neu_h, _ = translate_scored(t, m, d, srcs, beams=5)
                    del m
                except Exception as e:
                    log(f"  opus {lang} fail {e}")
            if neu_h is None and nmodel is not None and lang in NLLB:
                try:
                    neu_h, _ = translate_scored(
                        ntok, nmodel, ndev, srcs, nllb_src=NLLB[lang], beams=5
                    )
                except Exception as e:
                    log(f"  nllb {lang} fail {e}")
            if neu_h is None:
                neu_h = [densify_decode(pairs[i][0], lang, uni, bi, dens) for i in neu_i]
            for j, i in enumerate(neu_i):
                hyps[i] = neu_h[j]
        refs = [p[1] for p in pairs]
        sc = score_pairs(refs, hyps)
        by[lang] = {**sc, "densify_n": len(dens_i), "neural_n": len(neu_i)}
        log(f"  hybrid {lang:4} sacre={sc['sacrebleu']} d={len(dens_i)} n={len(neu_i)}")
        oh.extend(hyps)
        or_.extend(refs)
    if nmodel is not None:
        del nmodel
    overall = score_pairs(or_, oh)
    return {"overall": overall, "by_lang": by, "routes": dict(routes)}


def main():
    t0 = time.perf_counter()
    log("=== Beat-levers push under FSOT D1D38A ===")

    # L1 ensemble first (uses base models)
    l1 = lever_wmt_ensemble_and_baseline()
    systems = l1["systems"]

    # L3 finetune
    l3 = lever_wmt_finetune(max_train=60000, steps=2500, batch_size=8, lr=5e-5)

    # Ensemble with finetuned opus if better
    ft_sc = l3.get("wmt_test") or {}
    best_single = max(
        systems["opus_b5"]["sacrebleu"] or 0,
        systems["nllb_b5"]["sacrebleu"] or 0,
        ft_sc.get("sacrebleu") or 0,
    )

    # L2 hybrid chat
    l2 = lever_hybrid_chat(max_per=200)

    gaps = {
        "wmt_best_single_to_40": round(SOTA["wmt_mid"] - best_single, 2),
        "wmt_product_ens_to_40": round(
            SOTA["wmt_mid"] - float(systems["product_ensemble_nll"]["sacrebleu"] or 0), 2
        ),
        "wmt_ft_to_40": round(SOTA["wmt_mid"] - float(ft_sc.get("sacrebleu") or 0), 2),
        "wmt_best_to_48": round(SOTA["wmt_stretch"] - best_single, 2),
        "chat_hybrid_to_45": round(
            SOTA["chat_mid"] - float(l2["overall"].get("sacrebleu") or 0), 2
        ),
    }

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "D1D38A fixed; densify + neural students + finetune student only",
        "L1_wmt_ensemble": {k: v for k, v in systems.items()},
        "L2_hybrid_neural_first": l2,
        "L3_wmt_finetune": l3,
        "gaps": gaps,
        "sota_bars": SOTA,
        "verdict": {
            "news_single_best": best_single,
            "news_product_ensemble": systems["product_ensemble_nll"]["sacrebleu"],
            "news_finetuned": ft_sc.get("sacrebleu"),
            "chat_hybrid": l2["overall"].get("sacrebleu"),
            "mid40_cleared": best_single >= 40
            or (ft_sc.get("sacrebleu") or 0) >= 40
            or (systems["product_ensemble_nll"]["sacrebleu"] or 0) >= 40,
        },
    }
    (REP / "m6_beat_levers_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# Beat-the-competition levers — measured",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Law:** S=K(T1+T2+T3) pin **D1D38A** (unchanged)",
        "",
        "## L1 — Product dual-student ensemble (no ref peek)",
        "",
        f"| System | sacreBLEU |",
        f"|--------|----------:|",
        f"| opus-mt-de-en b5 | {systems['opus_b5']['sacrebleu']} |",
        f"| NLLB-600M b5 | {systems['nllb_b5']['sacrebleu']} |",
        f"| **Product ensemble (NLL pick)** | **{systems['product_ensemble_nll']['sacrebleu']}** |",
        f"| Oracle uF1 ensemble (upper) | {systems['oracle_uf1_ensemble']['sacrebleu']} |",
        f"| Picks | {systems['product_ensemble_nll'].get('picks')} |",
        "",
        "## L3 — WMT finetune student (opus-mt-de-en)",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| steps | {l3.get('steps')} |",
        f"| train pairs | {l3.get('train_pairs')} |",
        f"| avg loss last 100 | {l3.get('avg_loss_last100')} |",
        f"| **WMT test sacreBLEU** | **{ft_sc.get('sacrebleu')}** |",
        f"| chrF | {ft_sc.get('chrf')} |",
        f"| path | `{l3.get('path')}` |",
        "",
        "## L2 — Neural-first hybrid chat",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| sacreBLEU | **{l2['overall'].get('sacrebleu')}** |",
        f"| BLEU-4 | {l2['overall'].get('bleu')} |",
        f"| routes | {l2.get('routes')} |",
        f"| gap to chat 45 | {gaps['chat_hybrid_to_45']} |",
        "",
        "## Gaps to beat commercial mid-bar",
        "",
        f"| Bar | Gap |",
        f"|-----|----:|",
        f"| Best single → 40 | {gaps['wmt_best_single_to_40']} |",
        f"| Product ensemble → 40 | {gaps['wmt_product_ens_to_40']} |",
        f"| Finetuned → 40 | {gaps['wmt_ft_to_40']} |",
        f"| Best single → 48 | {gaps['wmt_best_to_48']} |",
        "",
        f"**Mid-40 cleared?** {report['verdict']['mid40_cleared']}",
        "",
        "## Next if still short of 40",
        "",
        "1. Longer finetune / full WMT train epoch",
        "2. Ensemble finetuned-opus + NLLB",
        "3. Larger student (NLLB-1.3B) when disk allows",
        "",
    ]
    text = "\n".join(md)
    (REP / "BEAT_LEVERS.md").write_text(text, encoding="utf-8")
    (ADA.parent / "docs" / "BEAT_LEVERS.md").write_text(text, encoding="utf-8")
    log("wrote BEAT_LEVERS.md")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
