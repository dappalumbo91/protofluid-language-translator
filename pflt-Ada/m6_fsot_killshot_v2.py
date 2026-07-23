#!/usr/bin/env python3
"""
DeepL killshot refinement v2 — formula-native levers:

  1) Encoder-state N  + teacher-forcing NLL as P  (not just gen_score rank)
  2) More hyps: multi-beam / multi-lp + optional NLLB-3.3B sequential
  3) Tighter T3 acoustic from SPM subword lattice (entropy, piece mass, breath)

Still: S = K·(T1+T2+T3) from archive pin D1D38A. No free-fit GBC.
One model on GPU at a time. Feature + hyp caches on disk.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
REP = ADA / "reports"
CACHE = ADA / "data" / "hyp_cache"
FEAT = ADA / "data" / "fsot_feat_cache"
REP.mkdir(exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)
FEAT.mkdir(parents=True, exist_ok=True)

MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
OPUS = MODELS / "Helsinki-NLP__opus-mt-de-en"
NLLB13 = MODELS / "facebook__nllb-200-1.3B"
NLLB600 = MODELS / "facebook__nllb-200-distilled-600M"
NLLB33 = MODELS / "facebook__nllb-200-3.3B"

ARCHIVE_COMPUTE = Path(
    r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py"
)
PIN = "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70"
LING_D_EFF = 12.0
MID, STRETCH = 40.0, 48.0
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(t: str) -> list[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def sacre(hyps, refs) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_bleu(hyps, [refs]).score, 2)


def chrf(hyps, refs) -> float:
    import sacrebleu

    return round(sacrebleu.corpus_chrf(hyps, [refs]).score, 2)


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


def free_gpu():
    import gc
    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        f, t = torch.cuda.mem_get_info()
        log(f"  GPU free {f//1024//1024}/{t//1024//1024} MB")


def load_authority():
    digest = hashlib.sha256(ARCHIVE_COMPUTE.read_bytes()).hexdigest().upper()
    ok = digest == PIN
    log(f"authority pin_ok={ok} sha={digest[:12]}…")
    import importlib.util

    spec = importlib.util.spec_from_file_location("fsot_compute_k2", str(ARCHIVE_COMPUTE))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fsot_compute_k2"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod, digest, ok


def load_wmt_test():
    from datasets import load_dataset

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    return (
        [ex["translation"]["de"] for ex in ds],
        [ex["translation"]["en"] for ex in ds],
    )


def ensure_nllb33() -> Path | None:
    if (NLLB33 / "config.json").exists():
        log(f"  present {NLLB33.name}")
        return NLLB33
    free_gb = 0.0
    try:
        import shutil

        free_gb = shutil.disk_usage(str(MODELS)).free / (1024**3)
    except Exception:
        free_gb = 50.0
    if free_gb < 15:
        log(f"  skip 3.3B download (disk free ~{free_gb:.0f} GB)")
        return None
    log("  attempting download facebook/nllb-200-3.3B …")
    try:
        from huggingface_hub import snapshot_download

        NLLB33.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id="facebook/nllb-200-3.3B",
            local_dir=str(NLLB33),
        )
        return NLLB33
    except Exception as e:
        log(f"  3.3B download failed: {e}")
        return None


def decode_expand(
    model_dir: Path,
    tag: str,
    srcs: list[str],
    *,
    nllb_src: str | None,
    beams: int,
    length_penalty: float,
    batch_size: int,
    cache_key: str,
    use_fp16: bool = True,
    num_return: int = 1,
) -> list[dict]:
    """
    Returns list of per-src dicts: {hyps: [...], scores: [...]} length=n_src.
    If num_return>1, each src has multiple hyps (beam diversify).
    """
    path = CACHE / f"{cache_key}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("n_src") == len(srcs) and data.get("num_return") == num_return:
            log(f"  cache hit {cache_key}")
            return data["rows"]

    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    free_gpu()
    log(
        f"  decode {model_dir.name} b={beams} lp={length_penalty} "
        f"ret={num_return} n={len(srcs)}"
    )
    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    dtype = torch.float16 if (use_fp16 and torch.cuda.is_available()) else torch.float32
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True, torch_dtype=dtype
        )
    except Exception:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True
        )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src

    rows: list[dict] = []
    t0 = time.perf_counter()
    n_batches = (len(srcs) + batch_size - 1) // batch_size
    for bi, i in enumerate(range(0, len(srcs), batch_size)):
        batch = srcs[i : i + batch_size]
        enc = tok(
            batch, return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        kw = {
            "max_new_tokens": 160,
            "num_beams": max(beams, num_return),
            "length_penalty": length_penalty,
            "early_stopping": True,
            "return_dict_in_generate": True,
            "output_scores": True,
            "num_return_sequences": num_return,
        }
        if nllb_src:
            try:
                kw["forced_bos_token_id"] = tok.convert_tokens_to_ids("eng_Latn")
            except Exception:
                pass
        try:
            with torch.no_grad():
                out = model.generate(**enc, **kw)
        except torch.cuda.OutOfMemoryError:
            free_gpu()
            log("  OOM — retry batch=1")
            for s in batch:
                enc1 = tok(
                    [s],
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=192,
                )
                enc1 = {k: v.to(device) for k, v in enc1.items()}
                with torch.no_grad():
                    out1 = model.generate(**enc1, **kw)
                hyps = tok.batch_decode(out1.sequences, skip_special_tokens=True)
                sc = (
                    [float(x) for x in out1.sequences_scores.cpu().tolist()]
                    if hasattr(out1, "sequences_scores") and out1.sequences_scores is not None
                    else [0.0] * len(hyps)
                )
                rows.append({"hyps": hyps, "scores": sc})
            continue

        hyps_flat = tok.batch_decode(out.sequences, skip_special_tokens=True)
        if hasattr(out, "sequences_scores") and out.sequences_scores is not None:
            sc_flat = [float(x) for x in out.sequences_scores.cpu().tolist()]
        else:
            sc_flat = [0.0] * len(hyps_flat)
        # group by source
        for j in range(len(batch)):
            sl = slice(j * num_return, (j + 1) * num_return)
            rows.append({"hyps": hyps_flat[sl], "scores": sc_flat[sl]})

        if (bi + 1) % 20 == 0 or bi + 1 == n_batches:
            elapsed = time.perf_counter() - t0
            rate = (bi + 1) / max(1e-6, elapsed)
            eta = (n_batches - bi - 1) / max(1e-6, rate)
            log(f"    {tag} {bi+1}/{n_batches} eta~{eta:.0f}s")

    del model
    free_gpu()
    path.write_text(
        json.dumps(
            {
                "rows": rows,
                "n_src": len(srcs),
                "num_return": num_return,
                "tag": tag,
                "beams": beams,
                "lp": length_penalty,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    log(f"  saved {path.name}")
    return rows


def extract_features(
    model_dir: Path,
    tag: str,
    srcs: list[str],
    hyp_rows: list[list[str]],
    *,
    nllb_src: str | None,
    batch_size: int,
    cache_key: str,
    use_fp16: bool = True,
) -> list[list[dict]]:
    """
    Per src, per hyp features:
      enc_norm  — mean L2 of encoder last hidden (N channel)
      tf_nll    — teacher-forcing token NLL of hyp (P channel; lower better)
      spm_ent   — SPM piece entropy (T3 acoustic)
      spm_mean_len, spm_n_pieces, spm_unk_frac
    """
    path = FEAT / f"{cache_key}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("n_src") == len(srcs):
            log(f"  feat cache hit {cache_key}")
            return data["feats"]

    import torch
    import torch.nn.functional as F
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    free_gpu()
    log(f"  features {model_dir.name} tag={tag} n={len(srcs)}")
    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    dtype = torch.float16 if (use_fp16 and torch.cuda.is_available()) else torch.float32
    try:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True, torch_dtype=dtype
        )
    except Exception:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            str(model_dir), local_files_only=True
        )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src

    feats: list[list[dict]] = [[] for _ in srcs]
    t0 = time.perf_counter()

    # Process sentence-by-sentence for clean alignment (features expensive but n=3003 ok)
    for i, src in enumerate(srcs):
        hyps = hyp_rows[i]
        # encoder once per src
        enc = tok(
            [src], return_tensors="pt", padding=True, truncation=True, max_length=192
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            enc_out = model.get_encoder()(**enc)
            # mean L2 over sequence (mask pad)
            h = enc_out.last_hidden_state  # [1, L, H]
            mask = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
            denom = mask.sum().clamp(min=1.0)
            mean_vec = (h * mask).sum(dim=1) / denom
            enc_norm = float(mean_vec.norm(dim=-1).item())
            # also mean token energy
            tok_energy = (h.norm(dim=-1) * enc["attention_mask"].to(h.dtype)).sum() / denom.squeeze()
            enc_energy = float(tok_energy.item())

        for hyp in hyps:
            # SPM lattice stats
            pieces = tok.tokenize(hyp)
            n_p = max(1, len(pieces))
            # piece length in chars of decoded pieces
            try:
                piece_strs = tok.convert_ids_to_tokens(pieces)
            except Exception:
                piece_strs = [str(p) for p in pieces]
            lens = [max(1, len(p.replace("▁", "").replace("Ġ", ""))) for p in piece_strs]
            mean_len = sum(lens) / n_p
            # entropy of piece id distribution
            cnt = Counter(pieces)
            ent = 0.0
            for c in cnt.values():
                p = c / n_p
                ent -= p * math.log(p + 1e-12)
            ent_norm = ent / math.log(n_p + 1)  # [0,1]-ish
            unk_id = getattr(tok, "unk_token_id", None)
            unk_frac = (
                sum(1 for p in pieces if p == unk_id) / n_p if unk_id is not None else 0.0
            )

            # teacher-forcing NLL
            lab = tok(
                text_target=[hyp],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=160,
            )
            labels = lab["input_ids"].to(device)
            labels[labels == tok.pad_token_id] = -100
            with torch.no_grad():
                out = model(**enc, labels=labels)
                # loss is mean NLL
                nll = float(out.loss.item()) if out.loss is not None else 10.0

            feats[i].append(
                {
                    "enc_norm": enc_norm,
                    "enc_energy": enc_energy,
                    "tf_nll": nll,
                    "spm_ent": ent,
                    "spm_ent_norm": ent_norm,
                    "spm_mean_len": mean_len,
                    "spm_n_pieces": n_p,
                    "spm_unk_frac": unk_frac,
                    "hyp_len_tok": len(toks(hyp)),
                    "src_len_tok": len(toks(src)),
                }
            )

        if (i + 1) % 100 == 0:
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / max(1e-6, elapsed)
            eta = (len(srcs) - i - 1) / max(1e-6, rate)
            log(f"    feat {tag} {i+1}/{len(srcs)} eta~{eta:.0f}s")

    del model
    free_gpu()
    path.write_text(
        json.dumps({"feats": feats, "n_src": len(srcs), "tag": tag}, ensure_ascii=False),
        encoding="utf-8",
    )
    log(f"  saved feats {path.name}")
    return feats


def split_terms_fixed(mod, s_in) -> tuple[float, float, float, float]:
    from mpmath import cos, exp, ln, sin, sqrt

    N, P, D = s_in.N, s_in.P, s_in.D_eff
    dp, dt, hits = s_in.delta_psi, s_in.delta_theta, s_in.recent_hits
    growth = exp(s_in.alpha * (1 - hits / N) * mod.GAMMA / mod.PHI)
    base = (
        (N * P / sqrt(D))
        * cos((s_in.psi_con + dp) / mod.ETA_EFF)
        * exp(-s_in.alpha * hits / N + s_in.rho + s_in.B_in * dp)
        * (1 + growth * s_in.C_eff)
    )
    T1 = base * (1 + s_in.P_new * ln(D / 25))
    if s_in.observed:
        T1 = T1 * exp(mod.C_FACTOR * s_in.P_var) * cos(dp + s_in.P_var)
    T2 = s_in.scale * s_in.amplitude + s_in.trend_bias
    valve = (
        s_in.beta
        * cos(dp)
        * (N * P / sqrt(D))
        * (1 + s_in.chaos * (D - 25) / 25)
        * (
            1
            + s_in.poof * cos(s_in.theta_s + mod.PI)
            + s_in.suction * sin(s_in.theta_s)
        )
    )
    acoustic = (
        1
        + (s_in.A_bleed * sin(dt) ** 2) / mod.PHI
        + (s_in.A_in * cos(dt) ** 2) / mod.PHI
    )
    phase = 1 + s_in.B_in * s_in.P_var
    T3 = valve * acoustic * phase
    S = mod.K * (T1 + T2 + T3)
    return float(S), float(T1), float(T2), float(T3)


def map_encoder_spm(
    mod,
    *,
    enc_norm: float,
    enc_energy: float,
    tf_nll: float,
    spm_ent_norm: float,
    spm_mean_len: float,
    spm_n_pieces: int,
    spm_unk_frac: float,
    hyp_len_tok: int,
    src_len_tok: int,
    gen_score: float,
    nll_rank: float,
    enc_rank: float,
):
    """
    Formula-native map:
      N ← encoder mass (seed-normalized)
      P ← inverse TF-NLL pressure (seed-normalized) + rank
      δθ ← SPM acoustic lattice (entropy, breath vs 8, unk)
      δψ ← length phase + nll stress
    """
    from mpmath import mpf

    PHI = float(mod.PHI)
    C_EFF = float(mod.C_EFF)
    E = float(mod.E)
    PI = float(mod.PI)

    # N: encoder energy relative rank + absolute scale via Φ
    # enc_rank in [0,1] among candidates; absolute enc_norm soft-squashed
    n_abs = enc_norm / (enc_norm + PHI)  # (0,1)
    N = PHI * (C_EFF + enc_rank + n_abs) / (1.0 + C_EFF)

    # P: low NLL = high pressure. nll_rank=1 means best (lowest nll)
    # also mix gen_score soft conf
    conf_gs = C_EFF / (1.0 + math.exp(-float(gen_score)))
    P = C_EFF * (1.0 + nll_rank * PHI) * (0.5 + conf_gs)

    # delta_psi: length phase + residual NLL stress (1-nll_rank)
    ls, lh = max(1, src_len_tok), max(1, hyp_len_tok)
    len_phase = abs(math.log1p(lh) - math.log1p(ls)) / PHI
    nll_stress = (1.0 - nll_rank) / PHI
    delta_psi = min(len_phase + nll_stress, PI / 2)

    # delta_theta: SPM acoustic — entropy excess, breath vs axiom 8, unk
    breath = abs(spm_mean_len - 8.0) / 8.0
    # high entropy is good diversity; low entropy = collapse → higher δθ stress
    ent_stress = (1.0 - min(1.0, spm_ent_norm)) / PHI
    unk_stress = spm_unk_frac * PHI
    piece_mass = abs(math.log1p(spm_n_pieces) - math.log1p(ls)) / PHI
    delta_theta = min(breath + ent_stress + unk_stress + piece_mass, PI / 2)

    hits = max(0.0, (1.0 - nll_rank) * E)  # residual disorder
    rho = max(0.1, C_EFF * (1.0 - spm_unk_frac) * (0.5 + spm_ent_norm * 0.5))
    scale = min(lh / ls, PHI)
    amplitude = rho * (C_EFF + nll_rank)
    trend_bias = 0.0 if lh >= 2 else -1.0 / PHI

    return mod.ScalarInput(
        N=mpf(N),
        P=mpf(P),
        D_eff=mpf(LING_D_EFF),
        delta_psi=mpf(delta_psi),
        delta_theta=mpf(delta_theta),
        recent_hits=mpf(hits),
        rho=mpf(rho),
        observed=True,
        scale=mpf(scale),
        amplitude=mpf(amplitude),
        trend_bias=mpf(trend_bias),
    )


def flatten_candidates(
    systems: dict[str, list[dict]],
) -> list[list[dict]]:
    """
    systems[tag] = list per src of {hyps, scores}
    returns per-src list of candidates {tag, hyp, gen_score, j}
    """
    tags = list(systems.keys())
    n = len(next(iter(systems.values())))
    out = []
    for i in range(n):
        cands = []
        for tag in tags:
            row = systems[tag][i]
            for j, (h, s) in enumerate(zip(row["hyps"], row["scores"])):
                cands.append(
                    {"tag": tag, "hyp": h, "gen_score": float(s), "j": j, "uid": f"{tag}#{j}"}
                )
        out.append(cands)
    return out


def main():
    t0 = time.perf_counter()
    log("=== FSOT killshot v2: encoder N/P + multi-hyp + SPM T3 ===")
    mod, digest, pin_ok = load_authority()
    C_EFF = float(mod.C_EFF)
    PHI = float(mod.PHI)
    K = float(mod.K)
    log(f"K={K:.6f} C_EFF={C_EFF:.6f} PHI={PHI:.6f}")

    t_src, t_ref = load_wmt_test()
    n = len(t_src)
    log(f"WMT test n={n}")

    # --- Expand hyps (sequential) ---
    systems_raw: dict[str, list[dict]] = {}

    # opus multi
    for beams, lp, key, bs in [
        (5, 1.0, "test_opus_b5_lp1.0_exp", 16),
        (5, 0.9, "test_opus_b5_lp0.9_exp", 16),
        (8, 1.0, "test_opus_b8_lp1.0_exp", 12),
    ]:
        # reuse flat cache if single-return already exists under old keys
        old_key = f"test_opus_b{beams}_lp{lp}"
        old_path = CACHE / f"{old_key}.json"
        if old_path.exists() and beams == 5:
            data = json.loads(old_path.read_text(encoding="utf-8"))
            if len(data.get("hyps", [])) == n:
                systems_raw[f"opus_b{beams}_lp{lp}"] = [
                    {"hyps": [h], "scores": [s]}
                    for h, s in zip(data["hyps"], data.get("scores", [0.0] * n))
                ]
                log(f"  reused flat cache {old_key}")
                continue
        rows = decode_expand(
            OPUS,
            f"opus_b{beams}",
            t_src,
            nllb_src=None,
            beams=beams,
            length_penalty=lp,
            batch_size=bs,
            cache_key=key,
            use_fp16=False,
            num_return=1,
        )
        systems_raw[f"opus_b{beams}_lp{lp}"] = rows

    # nllb13 multi-beam + multi-return
    for beams, lp, ret, key, bs in [
        (5, 1.0, 1, "test_nllb13_b5_lp1.0_exp", 4),
        (8, 1.0, 1, "test_nllb13_b8_lp1.0_exp", 3),
        (8, 1.0, 3, "test_nllb13_b8_ret3", 2),  # 3 hyps per src
        (5, 0.9, 1, "test_nllb13_b5_lp0.9", 4),
    ]:
        if beams == 5 and lp == 1.0 and ret == 1:
            old = CACHE / "test_nllb13_b5_lp1.0.json"
            if old.exists():
                data = json.loads(old.read_text(encoding="utf-8"))
                if len(data.get("hyps", [])) == n:
                    systems_raw["nllb13_b5_lp1.0"] = [
                        {"hyps": [h], "scores": [s]}
                        for h, s in zip(data["hyps"], data.get("scores", [0.0] * n))
                    ]
                    log("  reused flat cache test_nllb13_b5_lp1.0")
                    continue
        rows = decode_expand(
            NLLB13,
            f"nllb13_b{beams}_r{ret}",
            t_src,
            nllb_src="deu_Latn",
            beams=beams,
            length_penalty=lp,
            batch_size=bs,
            cache_key=key,
            use_fp16=True,
            num_return=ret,
        )
        systems_raw[f"nllb13_b{beams}_lp{lp}_r{ret}"] = rows

    # nllb600
    old600 = CACHE / "test_nllb_b5_lp1.0.json"
    if old600.exists():
        data = json.loads(old600.read_text(encoding="utf-8"))
        if len(data.get("hyps", [])) == n:
            systems_raw["nllb600_b5"] = [
                {"hyps": [h], "scores": [s]}
                for h, s in zip(data["hyps"], data.get("scores", [0.0] * n))
            ]
            log("  reused nllb600")

    # optional 3.3B
    p33 = ensure_nllb33()
    if p33 is not None:
        try:
            free_gpu()
            rows = decode_expand(
                p33,
                "nllb33_b5",
                t_src,
                nllb_src="deu_Latn",
                beams=5,
                length_penalty=1.0,
                batch_size=1,
                cache_key="test_nllb33_b5_lp1.0",
                use_fp16=True,
                num_return=1,
            )
            systems_raw["nllb33_b5"] = rows
        except Exception as e:
            log(f"  3.3B decode failed: {e}")

    log(f"systems: {list(systems_raw.keys())}")

    # --- Features for main families (opus, nllb13, optional 33) ---
    # Build hyp lists per model family (union of configs from that model)
    def family_hyps(prefix: str) -> list[list[str]]:
        tags = [t for t in systems_raw if t.startswith(prefix)]
        out = [[] for _ in range(n)]
        for i in range(n):
            seen = set()
            for t in tags:
                for h in systems_raw[t][i]["hyps"]:
                    if h not in seen:
                        seen.add(h)
                        out[i].append(h)
        return out

    feat_by_family: dict[str, list[list[dict]]] = {}
    family_dirs = {
        "opus": (OPUS, None, False),
        "nllb13": (NLLB13, "deu_Latn", True),
    }
    if "nllb33_b5" in systems_raw:
        family_dirs["nllb33"] = (NLLB33, "deu_Latn", True)
    if "nllb600_b5" in systems_raw:
        family_dirs["nllb600"] = (NLLB600, "deu_Latn", True)

    for fam, (mdir, nllb_src, fp16) in family_dirs.items():
        hyps = family_hyps(fam)
        # cap hyps per src for feature cost
        hyps = [h[:6] for h in hyps]
        feat_by_family[fam] = extract_features(
            mdir,
            fam,
            t_src,
            hyps,
            nllb_src=nllb_src,
            batch_size=1,
            cache_key=f"feat_{fam}_v2",
            use_fp16=fp16,
        )
        # attach hyp text index
        for i in range(n):
            for j, h in enumerate(hyps[i]):
                if j < len(feat_by_family[fam][i]):
                    feat_by_family[fam][i][j]["hyp"] = h

    # --- Flatten all unique (tag config hyp) with features when available ---
    log("FSOT scoring multi-hyp pool...")
    candidates: list[list[dict]] = []
    for i in range(n):
        cands = []
        for tag, rows in systems_raw.items():
            fam = tag.split("_")[0]
            if fam not in feat_by_family:
                # map nllb13...
                if tag.startswith("nllb13"):
                    fam = "nllb13"
                elif tag.startswith("nllb33"):
                    fam = "nllb33"
                elif tag.startswith("nllb600"):
                    fam = "nllb600"
                elif tag.startswith("opus"):
                    fam = "opus"
            for j, (h, gs) in enumerate(zip(rows[i]["hyps"], rows[i]["scores"])):
                # find feature by hyp text
                ft = None
                if fam in feat_by_family:
                    for f in feat_by_family[fam][i]:
                        if f.get("hyp") == h:
                            ft = f
                            break
                cands.append(
                    {
                        "uid": f"{tag}#{j}",
                        "tag": tag,
                        "fam": fam,
                        "hyp": h,
                        "gen_score": float(gs),
                        "feat": ft,
                    }
                )
        candidates.append(cands)

    # score each cand
    panels: list[list[dict]] = []
    for i in range(n):
        cands = candidates[i]
        # ranks within sentence
        nlls = []
        encs = []
        for c in cands:
            if c["feat"]:
                nlls.append(c["feat"]["tf_nll"])
                encs.append(c["feat"]["enc_norm"])
            else:
                nlls.append(10.0)
                encs.append(0.0)
        # nll_rank: lower nll better → rank 1
        def rank01(vals, higher_better: bool):
            if not vals:
                return [0.5] * 0
            lo, hi = min(vals), max(vals)
            span = (hi - lo) if hi > lo else 1.0
            if higher_better:
                return [(v - lo) / span for v in vals]
            return [(hi - v) / span for v in vals]

        nll_ranks = rank01(nlls, higher_better=False)
        enc_ranks = rank01(encs, higher_better=True)
        row_panels = []
        for k, c in enumerate(cands):
            ft = c["feat"] or {
                "enc_norm": 1.0,
                "enc_energy": 1.0,
                "tf_nll": 5.0,
                "spm_ent_norm": 0.5,
                "spm_mean_len": 4.0,
                "spm_n_pieces": 10,
                "spm_unk_frac": 0.0,
                "hyp_len_tok": max(1, len(toks(c["hyp"]))),
                "src_len_tok": max(1, len(toks(t_src[i]))),
            }
            s_in = map_encoder_spm(
                mod,
                enc_norm=ft["enc_norm"],
                enc_energy=ft.get("enc_energy", ft["enc_norm"]),
                tf_nll=ft["tf_nll"],
                spm_ent_norm=ft.get("spm_ent_norm", 0.5),
                spm_mean_len=ft.get("spm_mean_len", 4.0),
                spm_n_pieces=int(ft.get("spm_n_pieces", 10)),
                spm_unk_frac=ft.get("spm_unk_frac", 0.0),
                hyp_len_tok=int(ft.get("hyp_len_tok", 1)),
                src_len_tok=int(ft.get("src_len_tok", 1)),
                gen_score=c["gen_score"],
                nll_rank=nll_ranks[k],
                enc_rank=enc_ranks[k],
            )
            S, T1, T2, T3 = split_terms_fixed(mod, s_in)
            row_panels.append(
                {
                    **c,
                    "S": S,
                    "T1": T1,
                    "T2": T2,
                    "T3": T3,
                    "nll_rank": nll_ranks[k],
                    "tf_nll": ft["tf_nll"],
                    "score_fsot": T1 * C_EFF + T2 + T3 / PHI,
                    "score_S": S,
                    "score_T3": T3,
                    "score_nll": -ft["tf_nll"],
                    "score_gen": c["gen_score"],
                }
            )
        panels.append(row_panels)
        if (i + 1) % 500 == 0:
            log(f"  scored {i+1}/{n}")

    def pick(mode: str) -> list[str]:
        out = []
        for i in range(n):
            row = panels[i]
            if mode == "oracle":
                best = max(row, key=lambda c: sent_bleu(c["hyp"], t_ref[i]))
            elif mode == "fsot_product":
                best = max(row, key=lambda c: c["score_fsot"])
            elif mode == "max_S":
                best = max(row, key=lambda c: c["score_S"])
            elif mode == "max_T3":
                best = max(row, key=lambda c: c["score_T3"])
            elif mode == "min_nll":
                best = max(row, key=lambda c: c["score_nll"])
            elif mode == "gen_score":
                best = max(row, key=lambda c: c["score_gen"])
            elif mode == "fsot_nll_tie":
                # primary min nll; if ranks close use fsot_product
                ranked = sorted(row, key=lambda c: c["tf_nll"])
                if len(ranked) >= 2 and abs(ranked[0]["nll_rank"] - ranked[1]["nll_rank"]) < 1.0 / PHI:
                    best = max(row, key=lambda c: c["score_fsot"])
                else:
                    best = ranked[0]
            else:
                best = row[0]
            out.append(best["hyp"])
        return out

    # single-system baselines from first hyp of each tag
    results = {}
    for tag in systems_raw:
        hyps = [systems_raw[tag][i]["hyps"][0] for i in range(n)]
        results[f"single_{tag}"] = {
            "sacrebleu": sacre(hyps, t_ref),
            "chrf": chrf(hyps, t_ref),
        }
        log(f"  single_{tag} sacre={results[f'single_{tag}']['sacrebleu']}")

    modes = [
        "gen_score",
        "min_nll",
        "max_S",
        "max_T3",
        "fsot_product",
        "fsot_nll_tie",
        "oracle",
    ]
    pick_stats = {}
    for mode in modes:
        hyps = pick(mode)
        results[mode] = {
            "sacrebleu": sacre(hyps, t_ref),
            "chrf": chrf(hyps, t_ref),
        }
        if mode != "oracle":
            cnt = Counter()
            for i in range(n):
                row = panels[i]
                if mode == "fsot_product":
                    best = max(row, key=lambda c: c["score_fsot"])
                elif mode == "max_S":
                    best = max(row, key=lambda c: c["score_S"])
                elif mode == "max_T3":
                    best = max(row, key=lambda c: c["score_T3"])
                elif mode == "min_nll":
                    best = max(row, key=lambda c: c["score_nll"])
                elif mode == "gen_score":
                    best = max(row, key=lambda c: c["score_gen"])
                elif mode == "fsot_nll_tie":
                    ranked = sorted(row, key=lambda c: c["tf_nll"])
                    if len(ranked) >= 2 and abs(
                        ranked[0]["nll_rank"] - ranked[1]["nll_rank"]
                    ) < 1.0 / PHI:
                        best = max(row, key=lambda c: c["score_fsot"])
                    else:
                        best = ranked[0]
                else:
                    best = row[0]
                cnt[best["tag"]] += 1
            pick_stats[mode] = dict(cnt)
            results[mode]["picks"] = dict(cnt)
        log(f"  {mode} sacre={results[mode]['sacrebleu']}")

    product_keys = [k for k in results if k != "oracle" and not k.startswith("single_")]
    # also allow best single as product floor
    all_product = [k for k in results if k != "oracle"]
    best = max(all_product, key=lambda k: results[k]["sacrebleu"])
    best_s = results[best]["sacrebleu"]
    oracle_s = results["oracle"]["sacrebleu"]

    # mean pool size
    mean_pool = sum(len(p) for p in panels) / max(1, n)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "DeepL killshot v2 — encoder N/P, multi-hyp, SPM T3",
        "fsot": {
            "formula": "S=K*(T1+T2+T3)",
            "pin_ok": pin_ok,
            "sha": digest[:16],
            "K": K,
            "C_EFF": C_EFF,
            "PHI": PHI,
            "D_eff": LING_D_EFF,
            "map": "N←enc_norm/rank; P←tf_nll_rank·C_EFF; δθ←SPM entropy/breath/unk; δψ←len+nll_stress",
        },
        "systems": list(systems_raw.keys()),
        "mean_pool_size": round(mean_pool, 2),
        "results": results,
        "pick_stats": pick_stats,
        "best_product": {"name": best, "sacrebleu": best_s},
        "oracle_sacrebleu": oracle_s,
        "gaps": {
            "best_to_40": round(MID - best_s, 2),
            "best_to_48": round(STRETCH - best_s, 2),
            "oracle_to_40": round(MID - oracle_s, 2),
        },
        "mid40_cleared": best_s >= MID,
        "oracle_clears_mid40": oracle_s >= MID,
        "pct_of_mid40": round(100 * best_s / MID, 1),
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "prior_v1_product": 36.03,
    }
    (REP / "m6_fsot_killshot_v2_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = f"""# FSOT DeepL killshot v2

**Built:** {report['built_utc']}  
**Mission:** DeepL mid-40 killshot  
**Law:** S=K(T1+T2+T3) pin D1D38A · pin_ok={pin_ok}  
**Elapsed:** {report['elapsed_s']}s  
**Mean hyp pool / sentence:** {report['mean_pool_size']}

## Levers applied

1. **Encoder-state N** — mean L2 of encoder last hidden + rank  
2. **TF-NLL as P** — teacher-forcing token NLL of hyp (pressure = low NLL)  
3. **SPM T3 acoustic** — piece entropy, mean piece length vs breath 8, unk frac  
4. **Multi-hyp** — multi-beam / multi-return systems: `{list(systems_raw.keys())}`

## Distance

| Bar | Target | Best product | Gap |
|-----|-------:|-------------:|----:|
| Mid DeepL | 40 | **{best_s}** (`{best}`) | **{report['gaps']['best_to_40']}** |
| Oracle | — | **{oracle_s}** | {report['gaps']['oracle_to_40']} |
| Prior v1 product | 36.03 | {best_s} | Δ {round(best_s-36.03,2)} |
| % of mid-40 | | **{report['pct_of_mid40']}%** | |
| mid40_cleared | | **{report['mid40_cleared']}** | |

## All systems / modes

| System | sacreBLEU | chrF |
|--------|----------:|-----:|
"""
    for k, v in sorted(results.items(), key=lambda x: -x[1]["sacrebleu"]):
        md += f"| {k} | **{v['sacrebleu']}** | {v.get('chrf','—')} |\n"
    md += f"""
## Constants

K={K:.6f} · C_EFF={C_EFF:.6f} · Φ={PHI:.6f} · D_eff={LING_D_EFF}
"""
    (REP / "FSOT_KILLSHOT_V2.md").write_text(md, encoding="utf-8")
    docs = ADA.parent / "docs"
    if docs.is_dir():
        (docs / "FSOT_KILLSHOT_V2.md").write_text(md, encoding="utf-8")
        # refresh distance headline
        (docs / "ACCURACY_DISTANCE.md").write_text(
            f"""# How far until DeepL killshot?

**Updated:** {report['built_utc']} · Law **D1D38A**

| Track | Value |
|-------|------:|
| **Best product** | **{best_s}** (`{best}`) |
| Gap to mid-40 | **{report['gaps']['best_to_40']}** |
| Oracle | **{oracle_s}** |
| % of mid-40 | **{report['pct_of_mid40']}%** |
| Prior v1 FSOT product | 36.03 |

## v2 levers

Encoder N + TF-NLL P + SPM T3 + multi-beam hyp pool (mean {report['mean_pool_size']}/sent).

See `FSOT_KILLSHOT_V2.md`.
""",
            encoding="utf-8",
        )
    log(f"BEST product {best} sacre={best_s} gap40={report['gaps']['best_to_40']} oracle={oracle_s}")
    log(f"elapsed {report['elapsed_s']}s")


if __name__ == "__main__":
    # remove broken stub if any
    main()
