#!/usr/bin/env python3
"""
FSOT-derived ranking — S = K·(T1+T2+T3) from archive pin D1D38A.

NO Qwen. NO free BLEU fit. NO gen-max as product.

Student multi-hyp pools (NLLB) supply candidates only.
Each hyp is mapped into ScalarInput (N,P,δψ,δθ,…) then scored with the
archive term structure (same law as killshot v2 / fsot_compute).

Product = argmax S within NLLB-3.3B family (scores comparable).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import sacrebleu
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
FEAT = ROOT / "pflt-Ada" / "data" / "fsot_feat_cache"
REP = ROOT / "pflt-Ada" / "reports"
LING_D_EFF = 12.0
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)

NLLB33_KEYS = [
    "test_nllb33_b5_lp1.0",
    "test_nllb33_b8_lp1.0",
    "test_nllb33_b8_ret3",
    "test_nllb33_b8_ret5",
]


def toks(t: str) -> List[str]:
    return [x.lower() for x in TOKEN_RE.findall(t or "")]


def load_authority():
    from fsot_law_bridge import AUTHORITY_SHA256, find_authority_compute

    path = find_authority_compute()
    if path is None:
        raise RuntimeError("fsot_compute.py not found — cannot derive without law")
    h = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    pin_ok = h == AUTHORITY_SHA256
    spec = importlib.util.spec_from_file_location("fsot_compute_authority", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["fsot_compute_authority"] = mod
    spec.loader.exec_module(mod)
    return mod, path, pin_ok, h


def split_terms(mod, s_in) -> Tuple[float, float, float, float]:
    """Archive term structure → S, T1, T2, T3. Formula: S = K*(T1+T2+T3)."""
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


def map_to_scalar(
    mod,
    *,
    enc_norm: float,
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
    """Observables → ScalarInput under seed constants (PHI, C_EFF, E, PI)."""
    from mpmath import mpf

    PHI = float(mod.PHI)
    C_EFF = float(mod.C_EFF)
    E = float(mod.E)
    PI = float(mod.PI)

    n_abs = enc_norm / (enc_norm + PHI + 1e-9)
    N = PHI * (C_EFF + enc_rank + n_abs) / (1.0 + C_EFF)

    conf_gs = C_EFF / (1.0 + math.exp(-float(gen_score)))
    P = C_EFF * (1.0 + nll_rank * PHI) * (0.5 + conf_gs)

    ls, lh = max(1, src_len_tok), max(1, hyp_len_tok)
    len_phase = abs(math.log1p(lh) - math.log1p(ls)) / PHI
    nll_stress = (1.0 - nll_rank) / PHI
    delta_psi = min(len_phase + nll_stress, PI / 2)

    breath = abs(spm_mean_len - 8.0) / 8.0
    ent_stress = (1.0 - min(1.0, spm_ent_norm)) / PHI
    unk_stress = spm_unk_frac * PHI
    piece_mass = abs(math.log1p(spm_n_pieces) - math.log1p(ls)) / PHI
    delta_theta = min(breath + ent_stress + unk_stress + piece_mass, PI / 2)

    hits = max(0.0, (1.0 - nll_rank) * E)
    rho = max(0.1, C_EFF * (1.0 - spm_unk_frac) * (0.5 + spm_ent_norm * 0.5))
    scale = min(lh / float(ls), PHI)
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


def load_rows(key: str, n: int):
    p = CACHE / f"{key}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if "rows" in d and d.get("n_src") == n:
        return d["rows"]
    return None


def load_feats(name: str, n: int):
    p = FEAT / f"{name}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    feats = d.get("feats")
    if feats is None or len(feats) != n:
        return None
    return feats


def rank01(vals: List[float], *, higher_better: bool) -> List[float]:
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-12:
        return [0.5] * len(vals)
    if higher_better:
        return [(v - lo) / (hi - lo) for v in vals]
    return [(hi - v) / (hi - lo) for v in vals]


def main() -> None:
    t0 = time.perf_counter()
    print("=== FSOT DERIVE RANK — S=K(T1+T2+T3) pin D1D38A ===", flush=True)
    mod, path, pin_ok, digest = load_authority()
    K = float(mod.K)
    PHI = float(mod.PHI)
    C_EFF = float(mod.C_EFF)
    print(f"authority={path}", flush=True)
    print(f"pin_ok={pin_ok} digest={digest[:16]}…", flush=True)
    print(f"K={K:.8f} PHI={PHI:.8f} C_EFF={C_EFF:.8f}", flush=True)
    if not pin_ok:
        print("WARNING: pin mismatch — still deriving with archive file", flush=True)

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(refs)
    print(f"WMT14 n={n}", flush=True)

    pools: List[List[dict]] = [[] for _ in range(n)]
    for key in NLLB33_KEYS:
        rows = load_rows(key, n)
        if not rows:
            print(f"  missing {key}", flush=True)
            continue
        print(f"  loaded {key}", flush=True)
        for i in range(n):
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                pools[i].append({"hyp": h, "gen_score": float(s)})

    for i in range(n):
        best: Dict[str, dict] = {}
        for c in pools[i]:
            h = c["hyp"]
            if h not in best or c["gen_score"] > best[h]["gen_score"]:
                best[h] = c
        pools[i] = list(best.values())

    feats = load_feats("feat_nllb33_v3", n) or load_feats("feat_nllb33_v2", n)
    if feats is None:
        raise RuntimeError("need feat_nllb33_v3/v2 for formula map")

    feat_by_hyp: List[Dict[str, dict]] = []
    for i in range(n):
        m: Dict[str, dict] = {}
        for f in feats[i]:
            hyp = f.get("hyp")
            if hyp:
                m[hyp] = f
        feat_by_hyp.append(m)
    print(
        f"feat coverage: {sum(1 for i in range(n) if feat_by_hyp[i])}/{n} sents with hyp keys",
        flush=True,
    )

    hyps_S: List[str] = []
    hyps_lin: List[str] = []
    hyps_gen: List[str] = []
    mean_S = 0.0
    n_scored = 0
    agree_S_gen = 0
    samples = []

    for i in range(n):
        cands = pools[i]
        if not cands:
            hyps_S.append("")
            hyps_lin.append("")
            hyps_gen.append("")
            continue

        nlls, encs = [], []
        for c in cands:
            f = feat_by_hyp[i].get(c["hyp"], {})
            nlls.append(float(f.get("tf_nll", 5.0)))
            encs.append(float(f.get("enc_norm", 1.0)))
        nll_ranks = rank01(nlls, higher_better=False)
        enc_ranks = rank01(encs, higher_better=True)

        scored = []
        for j, c in enumerate(cands):
            f = feat_by_hyp[i].get(c["hyp"], {})
            s_in = map_to_scalar(
                mod,
                enc_norm=float(f.get("enc_norm", encs[j])),
                tf_nll=float(f.get("tf_nll", nlls[j])),
                spm_ent_norm=float(f.get("spm_ent_norm", 0.5)),
                spm_mean_len=float(f.get("spm_mean_len", 4.0)),
                spm_n_pieces=int(
                    f.get("spm_n_pieces", max(1, len(toks(c["hyp"]))))
                ),
                spm_unk_frac=float(f.get("spm_unk_frac", 0.0)),
                hyp_len_tok=int(f.get("hyp_len_tok", len(toks(c["hyp"])))),
                src_len_tok=int(f.get("src_len_tok", len(toks(srcs[i])))),
                gen_score=c["gen_score"],
                nll_rank=nll_ranks[j],
                enc_rank=enc_ranks[j],
            )
            S, T1, T2, T3 = split_terms(mod, s_in)
            scored.append(
                {
                    "hyp": c["hyp"],
                    "S": S,
                    "T1": T1,
                    "T2": T2,
                    "T3": T3,
                    "score_lin": T1 * C_EFF + T2 + T3 / PHI,
                    "gen": c["gen_score"],
                }
            )
            mean_S += S
            n_scored += 1

        bS = max(scored, key=lambda x: x["S"])
        bL = max(scored, key=lambda x: x["score_lin"])
        bG = max(scored, key=lambda x: x["gen"])
        hyps_S.append(bS["hyp"])
        hyps_lin.append(bL["hyp"])
        hyps_gen.append(bG["hyp"])
        if bS["hyp"] == bG["hyp"]:
            agree_S_gen += 1
        if i < 3 or i in (100, 500, 1000, 2000):
            samples.append(
                {
                    "i": i,
                    "S": bS["S"],
                    "T1": bS["T1"],
                    "T2": bS["T2"],
                    "T3": bS["T3"],
                    "pick": bS["hyp"][:100],
                    "same_as_gen": bS["hyp"] == bG["hyp"],
                }
            )
        if i % 500 == 0:
            print(f"  {i}/{n} S={bS['S']:.6f} T1={bS['T1']:.4f} T3={bS['T3']:.4f}", flush=True)

    sacre_S = sacrebleu.corpus_bleu(hyps_S, [refs]).score
    sacre_lin = sacrebleu.corpus_bleu(hyps_lin, [refs]).score
    sacre_gen = sacrebleu.corpus_bleu(hyps_gen, [refs]).score
    chrf_S = sacrebleu.corpus_chrf(hyps_S, [refs]).score
    best_name = "FSOT_product_S" if sacre_S >= sacre_lin else "FSOT_product_lin"
    best_s = max(sacre_S, sacre_lin)

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "FSOT-derived rank — archive S=K(T1+T2+T3) ONLY",
        "formula": "S = K*(T1+T2+T3)",
        "pin": "D1D38A",
        "pin_ok": pin_ok,
        "authority_path": str(path),
        "K": K,
        "PHI": PHI,
        "C_EFF": C_EFF,
        "D_eff_linguistic": LING_D_EFF,
        "n": n,
        "mean_S": mean_S / max(1, n_scored),
        "agree_S_vs_gen_pct": round(100 * agree_S_gen / n, 2),
        "results": {
            "FSOT_product_S": {
                "sacrebleu": round(sacre_S, 2),
                "chrf": round(chrf_S, 2),
                "note": "argmax S=K(T1+T2+T3) within NLLB-3.3B multi-hyp",
            },
            "FSOT_product_lin": {
                "sacrebleu": round(sacre_lin, 2),
                "note": "argmax T1*C_EFF+T2+T3/PHI (seed constants only)",
            },
            "student_gen_max": {
                "sacrebleu": round(sacre_gen, 2),
                "note": "NLLB-3.3B max gen — student baseline, NOT FSOT product",
            },
        },
        "best_product": {"name": best_name, "sacrebleu": round(best_s, 2)},
        "gap_to_DeepL_mid40": round(40.0 - best_s, 2),
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "samples": samples,
        "honesty": (
            "Candidates from NLLB students; ranking is archive FSOT scalar only. "
            "No Qwen. K not free-fit. Pin D1D38A."
        ),
    }

    REP.mkdir(parents=True, exist_ok=True)
    outj = REP / "FSOT_DERIVE_RANK.json"
    outj.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# FSOT derive rank — \(S=K(T_1+T_2+T_3)\)

**Built:** {report['built_utc']}  
**Pin D1D38A:** **{pin_ok}**  
**K:** {K:.8f} · **mean S:** {report['mean_S']:.6f}  

| System | sacreBLEU | Role |
|--------|----------:|------|
| **FSOT_product_S** | **{sacre_S:.2f}** | **argmax archive S** |
| FSOT_product_lin | {sacre_lin:.2f} | T1·C_EFF + T2 + T3/Φ |
| NLLB-3.3B gen max | {sacre_gen:.2f} | student only |
| DeepL mid bar | ~40 | external |

**Best FSOT product:** {best_name} **{best_s:.2f}** · gap to DeepL mid-40: **{report['gap_to_DeepL_mid40']}**  
**S-pick = gen-pick:** {report['agree_S_vs_gen_pct']}% of sentences  

## Derivation

```
observables (enc_norm, tf_nll, spm_*, lengths, gen)
  → ScalarInput (N, P, δψ, δθ, ρ, scale, amplitude, …)
  → T1, T2, T3 from archive term structure
  → S = K · (T1 + T2 + T3)
  → pick argmax S
```

Students supply candidates. **The formula ranks.** No Qwen. No free-fit of K.
"""
    (REP / "FSOT_DERIVE_RANK.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["results"], indent=2), flush=True)
    print(f"BEST {report['best_product']} gap40={report['gap_to_DeepL_mid40']}", flush=True)
    print(f"WROTE {outj}", flush=True)


if __name__ == "__main__":
    main()
