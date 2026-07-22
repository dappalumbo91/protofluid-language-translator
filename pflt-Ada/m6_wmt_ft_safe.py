#!/usr/bin/env python3
"""Safer WMT finetune: freeze encoder, low LR, short schedule. Law D1D38A unchanged."""
from __future__ import annotations

import json
from pathlib import Path

import torch
from datasets import load_dataset
from torch.utils.data import DataLoader
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
BASE = MODELS / "Helsinki-NLP__opus-mt-de-en"
OUT = MODELS / "Helsinki-NLP__opus-mt-de-en-wmt-ft-v2"
REP = Path(__file__).resolve().parent / "reports"
REP.mkdir(exist_ok=True)


def main():
    print("safe finetune: freeze encoder lr=2e-5 steps=1500", flush=True)
    tok = AutoTokenizer.from_pretrained(str(BASE), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(BASE), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    for p in model.model.encoder.parameters():
        p.requires_grad = False
    model.train()

    ds = load_dataset("wmt/wmt14", "de-en", split="train")
    n = 40000
    idxs = list(range(0, len(ds), max(1, len(ds) // n)))[:n]
    pairs = [
        (ds[int(i)]["translation"]["de"], ds[int(i)]["translation"]["en"]) for i in idxs
    ]
    print("pairs", len(pairs), flush=True)

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

    loader = DataLoader(pairs, batch_size=8, shuffle=True, collate_fn=collate)
    opt = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=2e-5
    )
    steps = 1500
    sched = get_linear_schedule_with_warmup(opt, 50, steps)
    step = 0
    losses = []
    while step < steps:
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            if "labels" in batch:
                batch["labels"][batch["labels"] == tok.pad_token_id] = -100
            loss = model(**batch).loss
            loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad()
            losses.append(float(loss.item()))
            step += 1
            if step % 200 == 0:
                print("step", step, "loss", sum(losses[-200:]) / 200, flush=True)
            if step >= steps:
                break

    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT))
    tok.save_pretrained(str(OUT))
    model.eval()
    te = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in te]
    refs = [ex["translation"]["en"] for ex in te]
    hyps = []
    bs = 12
    for i in range(0, len(srcs), bs):
        batch = srcs[i : i + bs]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            gen = model.generate(
                **enc, max_new_tokens=160, num_beams=5, early_stopping=True
            )
        hyps.extend(tok.batch_decode(gen, skip_special_tokens=True))
    import sacrebleu

    sc = round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)
    print("SAFE_FT_SACRE", sc, flush=True)
    (REP / "wmt_ft_v2.json").write_text(
        json.dumps(
            {
                "sacrebleu": sc,
                "steps": steps,
                "lr": 2e-5,
                "freeze_encoder": True,
                "path": str(OUT),
                "baseline_opus": 33.88,
                "delta": round(sc - 33.88, 2),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
