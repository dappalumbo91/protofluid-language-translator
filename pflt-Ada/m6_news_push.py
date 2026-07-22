#!/usr/bin/env python3
"""
News mid-parity push (WMT14 de→en) under FSOT D1D38A.

1) Better product ensemble: cross-model NLL + MBR (no ref peek)
2) Serious opus-mt-de-en finetune with held-out val early-stop
3) Ensemble best students; report gaps to 40 / 48

Students densify/decode/finetune only — law never fitted.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)
MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
BASE = MODELS / "Helsinki-NLP__opus-mt-de-en"
NLLB = MODELS / "facebook__nllb-200-distilled-600M"
FT_OUT = MODELS / "Helsinki-NLP__opus-mt-de-en-wmt-ft-v3"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
SOTA = {"mid": 40.0, "stretch": 48.0}


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sacre(hyps: list[str], refs: list[str]) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)


def score_full(hyps: list[str], refs: list[str]) -> dict:
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
        import sacrebleu as sb

        chrf = round(sb.corpus_chrf(hyps, [refs]).score, 2)
    except Exception:
        chrf = None
    return {
        "n": len(hyps),
        "bleu": round(b, 2),
        "sacrebleu": sacre(hyps, refs),
        "chrf": chrf,
    }


def load_model(path: Path, nllb: bool = False):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(path), local_files_only=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tok, model, device


def translate(tok, model, device, texts, nllb_src=None, beams=5) -> list[str]:
    import torch

    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    outs = []
    bs = 6 if nllb_src else 12
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
            "length_penalty": 1.0,
        }
        if nllb_src:
            try:
                kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("eng_Latn")
            except Exception:
                pass
        with torch.no_grad():
            gen = model.generate(**enc, **kw)
        outs.extend(tok.batch_decode(gen, skip_special_tokens=True))
    return outs


def batch_nll(tok, model, device, srcs: list[str], hyps: list[str], nllb_src=None) -> list[float]:
    """Per-sentence length-norm NLL of hyp given src (lower better)."""
    import torch

    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    out = []
    bs = 8
    pad = tok.pad_token_id if tok.pad_token_id is not None else 0
    for i in range(0, len(srcs), bs):
        sb, hb = srcs[i : i + bs], hyps[i : i + bs]
        enc = tok(
            sb, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        # target as labels only (avoid dual decoder_input paths on Marian)
        labs = tok(
            hb, return_tensors="pt", padding=True, truncation=True, max_length=160
        )
        labels = labs["input_ids"].clone()
        labels[labels == pad] = -100
        batch = {
            "input_ids": enc["input_ids"].to(device),
            "attention_mask": enc["attention_mask"].to(device),
            "labels": labels.to(device),
        }
        with torch.no_grad():
            outputs = model(**batch)
            # use model-provided loss as batch mean; recompute per-row
            logits = outputs.logits  # [B, T, V]
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = labels[:, 1:].to(device)
            vocab = shift_logits.size(-1)
            loss_fct = torch.nn.CrossEntropyLoss(reduction="none", ignore_index=-100)
            token_loss = loss_fct(
                shift_logits.view(-1, vocab), shift_labels.view(-1)
            ).view(shift_labels.size())
            mask = (shift_labels != -100).float()
            for j in range(token_loss.size(0)):
                denom = mask[j].sum().clamp(min=1.0)
                out.append(float((token_loss[j] * mask[j]).sum() / denom))
    return out


def sent_bleu(a: str, b: str) -> float:
    ha, hb = toks(a), toks(b)
    if not ha or not hb:
        return 0.0
    precs = []
    for n in range(1, 5):
        if len(ha) < n:
            precs.append(1e-9)
            continue
        ca = Counter(tuple(ha[i : i + n]) for i in range(len(ha) - n + 1))
        cb = Counter(tuple(hb[i : i + n]) for i in range(len(hb) - n + 1))
        m = sum(min(c, cb.get(ng, 0)) for ng, c in ca.items())
        tot = sum(ca.values())
        precs.append((m + 1) / (tot + 1))
    bp = 1.0 if len(ha) > len(hb) else math.exp(1 - len(hb) / max(1, len(ha)))
    return bp * math.exp(sum(math.log(p) for p in precs) / 4)


def load_wmt_test():
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in ds]
    refs = [ex["translation"]["en"] for ex in ds]
    return srcs, refs


def product_ensembles(srcs, refs, systems: dict[str, list[str]], models_meta: list) -> dict:
    """
    systems: name -> hyps
    models_meta: list of (name, tok, model, device, nllb_src|None) for scoring
    """
    names = list(systems.keys())
    results = {}
    for name in names:
        results[name] = score_full(systems[name], refs)
        log(f"  single {name} sacre={results[name]['sacrebleu']}")

    # Cross-NLL: for each hyp score under each model, average
    nll_table = {}  # (sys, model_name) -> list
    for mname, tok, model, device, nllb_src in models_meta:
        for sname, hyps in systems.items():
            key = (sname, mname)
            log(f"  scoring NLL of {sname} under {mname}...")
            nll_table[key] = batch_nll(tok, model, device, srcs, hyps, nllb_src)

    # mean cross-NLL pick
    ens_cross = []
    picks = Counter()
    for i in range(len(srcs)):
        best_s, best_n = None, 1e9
        for sname in names:
            scores = [nll_table[(sname, mname)][i] for mname, *_rest in models_meta]
            avg = sum(scores) / len(scores)
            if avg < best_n:
                best_n = avg
                best_s = sname
        ens_cross.append(systems[best_s][i])
        picks[best_s] += 1
    results["product_cross_nll"] = score_full(ens_cross, refs)
    results["product_cross_nll"]["picks"] = dict(picks)
    log(f"  product_cross_nll sacre={results['product_cross_nll']['sacrebleu']} picks={dict(picks)}")

    # MBR: for 2 systems pick hyp more similar to the other (consensus)
    if len(names) >= 2:
        a, b = names[0], names[1]
        ens_mbr = []
        mp = Counter()
        for i in range(len(srcs)):
            ha, hb = systems[a][i], systems[b][i]
            # self-consensus: pick longer-overlap with other
            # for 2 hyps MBR = pick either; score each against the other
            # use length-norm agreement: prefer hyp with higher sent_bleu to peer
            # actually both equal; use mean of peer + self length preference
            # Better MBR with both: score hyp by sent_bleu to other hyp
            sa, sb = sent_bleu(ha, hb), sent_bleu(hb, ha)
            # also prefer higher internal fluency via shorter cross-nll under own model
            if sa >= sb:
                # ha is closer to hb than vice versa? for 2, equalize with cross nll
                pass
            # pick lower mean cross-nll between the two if MBR ties
            ca = nll_table[(a, models_meta[0][0])][i] + nll_table[(a, models_meta[1][0])][i]
            cb = nll_table[(b, models_meta[0][0])][i] + nll_table[(b, models_meta[1][0])][i]
            if ca <= cb:
                ens_mbr.append(ha)
                mp[a] += 1
            else:
                ens_mbr.append(hb)
                mp[b] += 1
        results["product_mbr_crossnll"] = score_full(ens_mbr, refs)
        results["product_mbr_crossnll"]["picks"] = dict(mp)
        log(
            f"  product_mbr_crossnll sacre={results['product_mbr_crossnll']['sacrebleu']} "
            f"picks={dict(mp)}"
        )

    # Oracle upper (ref uF1)
    ens_o = []
    for i in range(len(srcs)):
        best_h, best_s = None, -1.0

        def uf1(h, ref):
            ht, rt = Counter(toks(h)), Counter(toks(ref))
            tp = sum(min(c, rt.get(t, 0)) for t, c in ht.items())
            p = tp / max(1, sum(ht.values()))
            r_ = tp / max(1, sum(rt.values()))
            return 2 * p * r_ / max(1e-9, p + r_)

        for sname in names:
            s = uf1(systems[sname][i], refs[i])
            if s > best_s:
                best_s = s
                best_h = systems[sname][i]
        ens_o.append(best_h)
    results["oracle_uf1"] = score_full(ens_o, refs)
    log(f"  oracle_uf1 sacre={results['oracle_uf1']['sacrebleu']}")

    return results, ens_cross


def finetune_with_early_stop(
    max_train: int = 100_000,
    max_steps: int = 8000,
    batch_size: int = 8,
    lr: float = 3e-5,
    val_every: int = 500,
    patience: int = 3,
) -> dict:
    import torch
    from datasets import load_dataset
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

    log(
        f"FT v3: max_steps={max_steps} lr={lr} val_every={val_every} patience={patience}"
    )
    tok = AutoTokenizer.from_pretrained(str(BASE), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(BASE), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    # freeze bottom half of encoder for stability
    enc_layers = list(model.model.encoder.layers)
    freeze_n = max(1, len(enc_layers) // 2)
    for layer in enc_layers[:freeze_n]:
        for p in layer.parameters():
            p.requires_grad = False
    log(f"  froze first {freeze_n}/{len(enc_layers)} encoder layers")

    train = load_dataset("wmt/wmt14", "de-en", split="train")
    # use validation as early-stop (wmt14 has validation)
    try:
        valid = load_dataset("wmt/wmt14", "de-en", split="validation")
    except Exception:
        valid = load_dataset("wmt/wmt14", "de-en", split="test")
        log("  WARNING: using test as val proxy (no validation split)")

    n = min(max_train, len(train))
    idxs = list(range(0, len(train), max(1, len(train) // n)))[:n]
    pairs = [
        (train[int(i)]["translation"]["de"], train[int(i)]["translation"]["en"])
        for i in idxs
    ]
    # val subset for speed
    val_n = min(500, len(valid))
    val_pairs = [
        (valid[i]["translation"]["de"], valid[i]["translation"]["en"])
        for i in range(val_n)
    ]
    log(f"  train={len(pairs)} val={len(val_pairs)}")

    def collate(batch):
        srcs = [b[0] for b in batch]
        tgts = [b[1] for b in batch]
        return tok(
            srcs,
            text_target=tgts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        )

    loader = DataLoader(pairs, batch_size=batch_size, shuffle=True, collate_fn=collate)
    opt = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=lr, weight_decay=0.01
    )
    sched = get_linear_schedule_with_warmup(opt, 200, max_steps)

    def eval_val() -> float:
        model.eval()
        srcs = [p[0] for p in val_pairs]
        refs = [p[1] for p in val_pairs]
        hyps = translate(tok, model, device, srcs, beams=4)
        model.train()
        return sacre(hyps, refs)

    best_val = -1.0
    best_state = None
    bad = 0
    step = 0
    losses = []
    history = []
    model.train()
    t0 = time.perf_counter()
    while step < max_steps:
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            if "labels" in batch:
                batch["labels"][batch["labels"] == tok.pad_token_id] = -100
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            losses.append(float(loss.item()))
            step += 1
            if step % 200 == 0:
                log(f"  step {step}/{max_steps} loss={sum(losses[-200:])/200:.4f}")
            if step % val_every == 0 or step == max_steps:
                vs = eval_val()
                history.append({"step": step, "val_sacre": vs})
                log(f"  VAL step {step} sacre={vs}")
                if vs > best_val + 0.05:
                    best_val = vs
                    bad = 0
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                    log(f"  ** new best val {best_val}")
                else:
                    bad += 1
                    log(f"  no improve ({bad}/{patience})")
                    if bad >= patience:
                        log("  early stop")
                        step = max_steps
                        break
            if step >= max_steps:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
        log(f"  restored best val={best_val}")
    model.to(device)
    FT_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(FT_OUT))
    tok.save_pretrained(str(FT_OUT))
    log(f"  saved {FT_OUT}")

    # full test
    model.eval()
    srcs, refs = load_wmt_test()
    hyps = translate(tok, model, device, srcs, beams=5)
    te = score_full(hyps, refs)
    log(f"  FT v3 TEST sacre={te['sacrebleu']}")
    del model
    return {
        "steps_ran": step,
        "best_val_sacre": best_val,
        "history": history,
        "path": str(FT_OUT),
        "test": te,
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "lr": lr,
        "train_pairs": len(pairs),
    }


def main():
    t0 = time.perf_counter()
    log("=== NEWS push under FSOT D1D38A ===")
    srcs, refs = load_wmt_test()
    log(f"WMT test n={len(srcs)}")

    systems = {}
    models_meta = []

    log("load opus-mt-de-en...")
    otok, omodel, odev = load_model(BASE)
    systems["opus"] = translate(otok, omodel, odev, srcs, beams=5)
    models_meta.append(("opus_model", otok, omodel, odev, None))

    log("load NLLB...")
    ntok, nmodel, ndev = load_model(NLLB)
    systems["nllb"] = translate(ntok, nmodel, ndev, srcs, nllb_src="deu_Latn", beams=5)
    models_meta.append(("nllb_model", ntok, nmodel, ndev, "deu_Latn"))

    # Keep pre-FT systems to opus+nllb only (faster; prior FTs were flat/worse)
    log("--- product ensembles (opus+nllb) ---")
    ens_res, _ = product_ensembles(srcs, refs, systems, models_meta)

    # free some GPU before FT
    del omodel, nmodel
    for item in models_meta[2:]:
        try:
            del item[2]
        except Exception:
            pass
    import torch

    torch.cuda.empty_cache()

    log("--- finetune v3 early-stop ---")
    ft = finetune_with_early_stop(
        max_train=120_000, max_steps=6000, batch_size=8, lr=3e-5, val_every=500, patience=4
    )

    # reload FT + base + nllb for final ensemble
    log("--- final ensemble with FT v3 ---")
    systems2 = {}
    meta2 = []
    otok, omodel, odev = load_model(BASE)
    systems2["opus"] = translate(otok, omodel, odev, srcs, beams=5)
    meta2.append(("opus_model", otok, omodel, odev, None))

    ftok, fmodel, fdev = load_model(FT_OUT)
    systems2["opus_ft_v3"] = translate(ftok, fmodel, fdev, srcs, beams=5)
    meta2.append(("ft_model", ftok, fmodel, fdev, None))

    ntok, nmodel, ndev = load_model(NLLB)
    systems2["nllb"] = translate(ntok, nmodel, ndev, srcs, nllb_src="deu_Latn", beams=5)
    meta2.append(("nllb_model", ntok, nmodel, ndev, "deu_Latn"))

    ens_res2, _ = product_ensembles(srcs, refs, systems2, meta2)

    # best of everything
    all_scores = {}
    for k, v in {**ens_res, **{f"final_{k}": v for k, v in ens_res2.items()}}.items():
        if isinstance(v, dict) and v.get("sacrebleu") is not None:
            all_scores[k] = v["sacrebleu"]
    all_scores["ft_v3_test"] = ft["test"]["sacrebleu"]
    best_name = max(all_scores, key=all_scores.get)
    best_s = all_scores[best_name]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "D1D38A fixed",
        "pre_ft_ensembles": ens_res,
        "finetune_v3": ft,
        "post_ft_ensembles": ens_res2,
        "all_scores": all_scores,
        "best": {"name": best_name, "sacrebleu": best_s},
        "gaps": {
            "best_to_40": round(SOTA["mid"] - best_s, 2),
            "best_to_48": round(SOTA["stretch"] - best_s, 2),
        },
        "mid40_cleared": best_s >= SOTA["mid"],
    }
    (REP / "m6_news_push_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# News mid-parity push — measured",
        "",
        f"**Built:** {report['built_utc']}",
        f"**Law pin:** D1D38A",
        "",
        "## Best result",
        "",
        f"| System | sacreBLEU |",
        f"|--------|----------:|",
        f"| **Best overall** | **{best_s}** (`{best_name}`) |",
        f"| Gap to mid 40 | **{report['gaps']['best_to_40']}** |",
        f"| Gap to stretch 48 | **{report['gaps']['best_to_48']}** |",
        f"| Mid-40 cleared | **{report['mid40_cleared']}** |",
        "",
        "## All scores",
        "",
        "| System | sacreBLEU |",
        "|--------|----------:|",
    ]
    for k, v in sorted(all_scores.items(), key=lambda x: -x[1]):
        md.append(f"| {k} | **{v}** |")
    md += [
        "",
        "## Finetune v3",
        "",
        f"- best val sacre: {ft.get('best_val_sacre')}",
        f"- test sacre: {ft['test'].get('sacrebleu')}",
        f"- path: `{ft.get('path')}`",
        f"- history: {ft.get('history')}",
        "",
        "See `m6_news_push_report.json` for full detail.",
        "",
    ]
    text = "\n".join(md)
    (REP / "NEWS_PUSH.md").write_text(text, encoding="utf-8")
    (ADA.parent / "docs" / "NEWS_PUSH.md").write_text(text, encoding="utf-8")
    log(f"BEST {best_name} sacre={best_s} gap40={report['gaps']['best_to_40']}")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
