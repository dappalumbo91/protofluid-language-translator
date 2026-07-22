#!/usr/bin/env python3
"""
Learned ensemble picker for WMT de→en — close accuracy gap under FSOT.

Train on WMT validation with oracle labels (which of opus/nllb is better vs ref).
Apply to test with NO ref peek. Features are ref-free.

Law D1D38A unchanged.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ADA = Path(__file__).resolve().parent
REP = ADA / "reports"
REP.mkdir(exist_ok=True)
MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
BASE = MODELS / "Helsinki-NLP__opus-mt-de-en"
NLLB = MODELS / "facebook__nllb-200-distilled-600M"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sacre(hyps, refs) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)


def score_full(hyps, refs) -> dict:
    import sacrebleu

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
    return {
        "bleu": round(b, 2),
        "sacrebleu": sacre(hyps, refs),
        "chrf": round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2),
        "n": len(hyps),
    }


def sent_bleu(h: str, r: str) -> float:
    ht, rt = toks(h), toks(r)
    if not ht or not rt:
        return 0.0
    precs = []
    for n in range(1, 5):
        if len(ht) < n:
            precs.append(1e-9)
            continue
        hc = Counter(tuple(ht[i : i + n]) for i in range(len(ht) - n + 1))
        rc = Counter(tuple(rt[i : i + n]) for i in range(len(rt) - n + 1))
        m = sum(min(c, rc.get(ng, 0)) for ng, c in hc.items())
        tot = sum(hc.values())
        precs.append((m + 1) / (tot + 1))
    bp = 1.0 if len(ht) > len(rt) else math.exp(1 - len(rt) / max(1, len(ht)))
    return bp * math.exp(sum(math.log(p) for p in precs) / 4)


def load_model(path):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(path), local_files_only=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tok, model, device


def translate(tok, model, device, texts, nllb_src=None, beams=5):
    import torch

    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    outs = []
    scores = []
    bs = 8 if nllb_src else 16
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        kw = {
            "max_new_tokens": 160,
            "num_beams": beams,
            "early_stopping": True,
            "return_dict_in_generate": True,
            "output_scores": True,
        }
        if nllb_src:
            try:
                kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("eng_Latn")
            except Exception:
                pass
        with torch.no_grad():
            out = model.generate(**enc, **kw)
        dec = tok.batch_decode(out.sequences, skip_special_tokens=True)
        outs.extend(dec)
        if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
            scores.extend(out.sequences_scores.detach().cpu().tolist())
        else:
            scores.extend([0.0] * len(batch))
    return outs, scores


def features(src: str, ho: str, hn: str, so: float, sn: float) -> list[float]:
    """Ref-free features for picker."""
    ts, to, tn = toks(src), toks(ho), toks(hn)
    ls, lo, ln = max(1, len(ts)), max(1, len(to)), max(1, len(tn))
    # overlap between hyps
    co, cn = Counter(to), Counter(tn)
    inter = sum(min(c, cn.get(t, 0)) for t, c in co.items())
    union = sum(co.values()) + sum(cn.values()) - inter
    jacc = inter / max(1, union)
    # char lens
    return [
        lo / ls,
        ln / ls,
        lo / ln if ln else 1.0,
        len(ho) / max(1, len(src)),
        len(hn) / max(1, len(src)),
        float(so),
        float(sn),
        float(so) - float(sn),
        jacc,
        abs(lo - ln) / max(lo, ln),
        ho.count(",") + ho.count("."),
        hn.count(",") + hn.count("."),
        1.0 if lo < ls * 0.5 else 0.0,  # short hyp flag opus
        1.0 if ln < ls * 0.5 else 0.0,
        1.0 if lo > ls * 2.0 else 0.0,
        1.0 if ln > ls * 2.0 else 0.0,
    ]


def fit_logistic(X: np.ndarray, y: np.ndarray, steps: int = 800, lr: float = 0.3):
    """Simple L2 logistic regression in numpy (label 1 = prefer nllb)."""
    n, d = X.shape
    # standardize
    mu = X.mean(axis=0)
    sd = X.std(axis=0) + 1e-6
    Xs = (X - mu) / sd
    w = np.zeros(d)
    b = 0.0
    for _ in range(steps):
        z = Xs @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        err = p - y
        w -= lr * (Xs.T @ err / n + 0.01 * w)
        b -= lr * err.mean()
    return {"w": w.tolist(), "b": float(b), "mu": mu.tolist(), "sd": sd.tolist()}


def predict_proba(model, X: np.ndarray) -> np.ndarray:
    mu = np.array(model["mu"])
    sd = np.array(model["sd"])
    w = np.array(model["w"])
    Xs = (X - mu) / sd
    z = Xs @ w + model["b"]
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def load_split(name: str):
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split=name)
    srcs = [ex["translation"]["de"] for ex in ds]
    refs = [ex["translation"]["en"] for ex in ds]
    return srcs, refs


def main():
    t0 = time.perf_counter()
    log("=== Learned ensemble picker (close accuracy gap) ===")

    log("load models...")
    otok, omodel, odev = load_model(BASE)
    ntok, nmodel, ndev = load_model(NLLB)

    # validation for training picker
    try:
        v_src, v_ref = load_split("validation")
    except Exception:
        # fallback: first 1500 of train as pseudo-val (worse)
        log("no validation; using train head as picker train (suboptimal)")
        tr_s, tr_r = load_split("train")
        v_src, v_ref = tr_s[:2000], tr_r[:2000]
    # cap val for speed
    if len(v_src) > 2000:
        v_src, v_ref = v_src[:2000], v_ref[:2000]
    log(f"picker train n={len(v_src)}")

    log("translate val opus...")
    vo, vso = translate(otok, omodel, odev, v_src, beams=5)
    log("translate val nllb...")
    vn, vsn = translate(ntok, nmodel, ndev, v_src, nllb_src="deu_Latn", beams=5)

    X_tr, y_tr = [], []
    for i in range(len(v_src)):
        # label: 1 if nllb better by sentence BLEU vs ref
        bo, bn = sent_bleu(vo[i], v_ref[i]), sent_bleu(vn[i], v_ref[i])
        if abs(bo - bn) < 1e-9:
            continue  # skip ties
        y_tr.append(1.0 if bn > bo else 0.0)
        X_tr.append(features(v_src[i], vo[i], vn[i], vso[i], vsn[i]))
    X_tr = np.array(X_tr, dtype=np.float64)
    y_tr = np.array(y_tr, dtype=np.float64)
    log(f"train rows={len(y_tr)} nllb_preferred={int(y_tr.sum())} opus_preferred={int((1-y_tr).sum())}")

    picker = fit_logistic(X_tr, y_tr)
    # train accuracy
    p = predict_proba(picker, X_tr)
    pred = (p >= 0.5).astype(float)
    acc = float((pred == y_tr).mean())
    log(f"picker train acc={acc:.3f}")

    # test
    log("translate test...")
    t_src, t_ref = load_split("test")
    to, tso = translate(otok, omodel, odev, t_src, beams=5)
    tn, tsn = translate(ntok, nmodel, ndev, t_src, nllb_src="deu_Latn", beams=5)

    X_te = np.array(
        [features(t_src[i], to[i], tn[i], tso[i], tsn[i]) for i in range(len(t_src))],
        dtype=np.float64,
    )
    prob = predict_proba(picker, X_te)
    ens = []
    picks = Counter()
    for i in range(len(t_src)):
        if prob[i] >= 0.5:
            ens.append(tn[i])
            picks["nllb"] += 1
        else:
            ens.append(to[i])
            picks["opus"] += 1

    # baselines
    results = {
        "opus": score_full(to, t_ref),
        "nllb": score_full(tn, t_ref),
        "always_opus": score_full(to, t_ref),
        "learned_ensemble": score_full(ens, t_ref),
    }
    # oracle
    orc = []
    for i in range(len(t_src)):
        if sent_bleu(tn[i], t_ref[i]) > sent_bleu(to[i], t_ref[i]):
            orc.append(tn[i])
        else:
            orc.append(to[i])
    results["oracle"] = score_full(orc, t_ref)
    # simple gen-score pick (higher sequences_scores better)
    gen_ens = []
    gp = Counter()
    for i in range(len(t_src)):
        if tsn[i] >= tso[i]:
            gen_ens.append(tn[i])
            gp["nllb"] += 1
        else:
            gen_ens.append(to[i])
            gp["opus"] += 1
    results["gen_score_ensemble"] = score_full(gen_ens, t_ref)

    results["learned_ensemble"]["picks"] = dict(picks)
    results["gen_score_ensemble"]["picks"] = dict(gp)
    results["learned_ensemble"]["picker_train_acc"] = round(acc, 4)

    for k, v in results.items():
        log(f"  {k}: sacre={v['sacrebleu']}")

    best = max(
        (k for k in results if k != "oracle"),
        key=lambda k: results[k]["sacrebleu"],
    )
    best_s = results[best]["sacrebleu"]
    gaps = {
        "best_to_40": round(40 - best_s, 2),
        "best_to_48": round(48 - best_s, 2),
        "oracle_to_40": round(40 - results["oracle"]["sacrebleu"], 2),
        "learned_vs_opus": round(results["learned_ensemble"]["sacrebleu"] - results["opus"]["sacrebleu"], 2),
    }

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "D1D38A",
        "picker_train_n": len(y_tr),
        "picker_train_acc": round(acc, 4),
        "results": results,
        "best_product": {"name": best, "sacrebleu": best_s},
        "gaps": gaps,
        "mid40_cleared": best_s >= 40,
        "distance": {
            "chat_hybrid": 48.74,
            "chat_mid_bar": 45,
            "news_best": best_s,
            "news_mid_bar": 40,
            "news_stretch": 48,
            "pct_of_news_mid": round(100 * best_s / 40, 1),
        },
    }
    (REP / "m6_learned_ensemble_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = f"""# Accuracy distance + learned ensemble

**Built:** {report['built_utc']}  
**Law:** D1D38A

## How far (accuracy)

| Game | Us | Bar | Gap | Status |
|------|---:|----:|----:|--------|
| Catalog form→gloss | ~99.99% | product | — | **Competitive** |
| Chat hybrid | 48.74 | 45 mid | done | **Competitive** |
| News best product | **{best_s}** | 40 mid | **{gaps['best_to_40']}** | Climbing |
| News oracle | {results['oracle']['sacrebleu']} | 40 | {gaps['oracle_to_40']} | Headroom |
| News stretch | {best_s} | 48 | {gaps['best_to_48']} | Farther |

**~{report['distance']['pct_of_news_mid']}% of mid DeepL-class news bar.**

## Learned ensemble (this run)

| System | sacreBLEU |
|--------|----------:|
| opus-mt-de-en | {results['opus']['sacrebleu']} |
| NLLB-600M | {results['nllb']['sacrebleu']} |
| Gen-score ensemble | {results['gen_score_ensemble']['sacrebleu']} |
| **Learned ensemble** | **{results['learned_ensemble']['sacrebleu']}** |
| Oracle | {results['oracle']['sacrebleu']} |

Picker train acc: {acc:.3f} · picks: {dict(picks)} · Δ vs opus: {gaps['learned_vs_opus']}

elapsed {time.perf_counter()-t0:.0f}s
"""
    (REP / "LEARNED_ENSEMBLE.md").write_text(md, encoding="utf-8")
    dist_path = ADA.parent / "docs" / "ACCURACY_DISTANCE.md"
    prior = dist_path.read_text(encoding="utf-8") if dist_path.exists() else ""
    if "## Learned ensemble (this run)" in prior:
        prior = prior.split("## Learned ensemble (this run)")[0].rstrip()
    dist_path.write_text(prior + "\n\n---\n\n" + md, encoding="utf-8")
    log(f"BEST product {best} sacre={best_s} gap40={gaps['best_to_40']}")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
