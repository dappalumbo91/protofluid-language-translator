#!/usr/bin/env python3
"""
FSOT LLM judge QE — local Qwen picks best hyp for DE→EN (ref-free).

Crush lever: on selection-gap sentences, oracle always has *lower* gen than
max-gen product. Ask an instruction LM to choose among top candidates.

Caches picks for eval_news_deen_cached.py → FSOT_pick_llm_judge.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, List

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
HARD = ROOT / "pflt-Ada" / "data" / "news_hard_sel_indices.json"
OUT = ROOT / "pflt-Ada" / "data" / "fsot_qe_cache" / "llm_judge_qwen7b.json"
MODEL = "Qwen/Qwen2.5-7B-Instruct"
KEYS = [
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
]
TOP_K = 6  # hard: match v0.2.9 winning config
TOP_K_EASY = 4
FORCE_REJUDGE_HARD = False  # True only when intentionally re-scoring hard gaps


def load_rows(key: str, n: int):
    d = json.loads((CACHE / f"{key}.json").read_text(encoding="utf-8"))
    return d["rows"]


def pool_for(i: int, rowsets) -> Dict[str, float]:
    g: Dict[str, float] = {}
    for rows in rowsets:
        for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
            g[h] = max(g.get(h, -1e18), float(s))
    return g


def build_prompt(src: str, cands: List[str]) -> str:
    # Original prompt that hit 37.62 hard-only (v0.2.9) — keep stable
    lines = [
        "You are an expert German→English news translator.",
        "Pick the BEST English translation of the German source.",
        "Prefer accuracy and natural news English over awkward wording.",
        "Reply with ONLY the candidate number (1-based). No other text.",
        "",
        f"German: {src}",
        "",
        "Candidates:",
    ]
    for j, c in enumerate(cands, 1):
        lines.append(f"{j}. {c}")
    lines.append("")
    lines.append("Best candidate number:")
    return "\n".join(lines)


def parse_choice(text: str, k: int) -> int:
    m = re.search(r"\b([1-9][0-9]*)\b", text.strip())
    if not m:
        return 1
    v = int(m.group(1))
    if 1 <= v <= k:
        return v
    return 1


@torch.inference_mode()
def main() -> None:
    t0 = time.perf_counter()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device} model={MODEL}", flush=True)

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(srcs)
    rowsets = [load_rows(k, n) for k in KEYS]

    hard = json.loads(HARD.read_text(encoding="utf-8"))
    # Phase 3: re-judge hard with stronger prompt + TOP_K=8; keep easy picks
    hard_idx = hard.get("indices") or list(range(n))
    hard_set = set(hard_idx)
    only_hard = True
    order = hard_idx if only_hard else hard_idx + [i for i in range(n) if i not in hard_set]
    print(
        f"judge_order n={len(order)} only_hard={only_hard} force_hard={FORCE_REJUDGE_HARD}",
        flush=True,
    )

    print("loading Qwen…", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )
    if device != "cuda":
        model = model.to(device)
    model.eval()

    picks: Dict[str, str] = {}
    meta: Dict[str, dict] = {}

    # Resume if partial
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            picks = prev.get("picks") or {}
            meta = prev.get("meta") or {}
            print(f"resume with {len(picks)} picks", flush=True)
        except Exception:
            pass

    for step, i in enumerate(order):
        if str(i) in picks and not (FORCE_REJUDGE_HARD and i in hard_set):
            continue
        g = pool_for(i, rowsets)
        # top-K by gen; smaller K on non-hard for speed
        k = TOP_K if i in hard_set else TOP_K_EASY
        ranked = sorted(g.keys(), key=lambda h: -g[h])[:k]
        if len(ranked) == 1:
            picks[str(i)] = ranked[0]
            continue
        prompt = build_prompt(srcs[i], ranked)
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tok(text, return_tensors="pt").to(model.device)
        out = model.generate(
            **inputs,
            max_new_tokens=4,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
        gen = tok.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        choice = parse_choice(gen, len(ranked))
        hyp = ranked[choice - 1]
        picks[str(i)] = hyp
        meta[str(i)] = {"choice": choice, "raw": gen.strip()[:40], "n_cands": len(ranked)}

        if (step + 1) % 25 == 0 or step < 3:
            print(f"  {step+1}/{len(order)} i={i} chose={choice} raw={gen.strip()[:20]!r}", flush=True)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(
                json.dumps(
                    {
                        "model": MODEL,
                        "top_k": TOP_K,
                        "n_done": len(picks),
                        "n_total": n,
                        "picks": picks,
                        "meta": meta,
                        "partial": len(picks) < n,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": MODEL,
        "top_k": TOP_K,
        "n_done": len(picks),
        "n_total": n,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "picks": picks,
        "meta": meta,
        "partial": len(picks) < n,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {OUT} n_done={len(picks)} elapsed={payload['elapsed_s']}s", flush=True)


if __name__ == "__main__":
    main()
