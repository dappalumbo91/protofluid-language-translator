#!/usr/bin/env python3
"""
FSOT multi-aspect association for language (linguistics domain).

Associates what the archive + PFLT already solve:

  SOUND / vibration / frequency  → Acoustics domain (D=10)
  VISUAL form / written surface  → Optics domain (D=10)
  MEANING / understanding        → Biology cluster (D=12) + sense-ready ranks

Combined under golden partition (seed identity: 1 + 1/φ + 1/φ² = 2):

  S_assoc = ( S_meaning + S_acoustic/φ + S_visual/φ² ) / 2

Each S_* = K(T1+T2+T3) from archive pin D1D38A with domain-table D_eff.
No free parameters. No LLM judge. Students supply candidates only.

Product = argmax S_assoc within NLLB-3.3B multi-hyp pool.
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
sys.path.insert(0, str(ROOT))

CACHE = ROOT / "pflt-Ada" / "data" / "hyp_cache"
FEAT = ROOT / "pflt-Ada" / "data" / "fsot_feat_cache"
REP = ROOT / "pflt-Ada" / "reports"
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
# Latin / letter class for visual regularity of written English hyp
LETTER_RE = re.compile(r"[A-Za-zÀ-ÿ]")
SPACE_RE = re.compile(r"\s+")

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
        raise RuntimeError("fsot_compute.py missing")
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    pin_ok = digest == AUTHORITY_SHA256
    spec = importlib.util.spec_from_file_location("fsot_compute_authority", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["fsot_compute_authority"] = mod
    spec.loader.exec_module(mod)
    return mod, path, pin_ok, digest


def domain_cfg(mod, name: str, fallback: Tuple[float, float, float]):
    domains = getattr(mod, "DOMAINS", {}) or {}
    if name in domains:
        d = domains[name]
        return float(d.D_eff), float(d.delta_psi), float(d.delta_theta)
    return fallback


def split_terms(mod, s_in) -> Tuple[float, float, float, float]:
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


def rank01(vals: List[float], *, higher_better: bool) -> List[float]:
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-15:
        return [0.5] * len(vals)
    if higher_better:
        return [(v - lo) / (hi - lo) for v in vals]
    return [(hi - v) / (hi - lo) for v in vals]


def visual_form_stats(text: str) -> Dict[str, float]:
    """
    Written / visual channel: letter density, space rhythm, script regularity.
    All scale-free or φ-squash ready — not free-fit features.
    """
    t = text or ""
    n = max(1, len(t))
    letters = len(LETTER_RE.findall(t))
    spaces = len(SPACE_RE.findall(t))
    # digit/punct as visual noise
    other = n - letters - sum(1 for c in t if c.isspace())
    letter_frac = letters / n
    space_frac = spaces / n
    # char class entropy (visual diversity)
    from collections import Counter

    classes = []
    for c in t:
        if c.isalpha():
            classes.append("L")
        elif c.isspace():
            classes.append("S")
        elif c.isdigit():
            classes.append("D")
        else:
            classes.append("P")
    cnt = Counter(classes)
    ent = 0.0
    for v in cnt.values():
        p = v / n
        ent -= p * math.log(p + 1e-15)
    ent_norm = ent / math.log(4)  # 4 classes max
    return {
        "letter_frac": letter_frac,
        "space_frac": space_frac,
        "class_ent_norm": min(1.0, ent_norm),
        "other_frac": max(0.0, other) / n,
    }


def phonotactic_proxy(hyp: str) -> float:
    """Vowel energy ≈ 1/e target (killshot seed)."""
    th = toks(hyp)
    if not th:
        return 0.0
    vowels = set("aeiou")
    ratios = []
    for w in th:
        if not w:
            continue
        v = sum(1 for c in w if c in vowels)
        ratios.append(v / max(1, len(w)))
    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


def map_aspect(
    mod,
    *,
    D_eff: float,
    nll_rank: float,
    enc_rank: float,
    gen_rank: float,
    enc_norm: float,
    spm_ent_norm: float,
    spm_mean_len: float,
    spm_n_pieces: int,
    spm_unk_frac: float,
    hyp_len_tok: int,
    src_len_tok: int,
    aspect: str,
    vis: Dict[str, float],
    phon: float,
):
    """
    Aspect-conditioned ScalarInput. Same seed rules; different domain D_eff
    and which observables stress δψ vs δθ.
    """
    from mpmath import mpf

    PHI = float(mod.PHI)
    E = float(mod.E)
    C_EFF = float(mod.C_EFF)
    PI = float(mod.PI)
    BREATH = PHI * E

    n_abs = enc_norm / (enc_norm + PHI + 1e-15)
    N = PHI * (C_EFF + enc_rank + n_abs) / (1.0 + C_EFF)

    w_nll = PHI / (1.0 + PHI)
    w_gen = 1.0 / (1.0 + PHI)
    rank_p = w_nll * nll_rank + w_gen * gen_rank
    P = C_EFF * (1.0 + rank_p * PHI)

    ls, lh = max(1, src_len_tok), max(1, hyp_len_tok)
    len_phase = abs(math.log1p(lh) - math.log1p(ls)) / PHI
    nll_stress = (1.0 - nll_rank) / PHI

    if aspect == "meaning":
        # meaning / understanding: NLL + gen pressure, length phase
        delta_psi = min((len_phase + nll_stress) * (1.0 - gen_rank / PHI), PI / 2)
        delta_theta = min(
            (abs(spm_mean_len - BREATH) / BREATH + (1 - spm_ent_norm) / PHI + spm_unk_frac * PHI)
            * (1.0 - gen_rank / (PHI + 1)),
            PI / 2,
        )
        rho = max(
            1 / PHI,
            C_EFF * (1 - spm_unk_frac) * (1 / PHI + spm_ent_norm * (1 - 1 / PHI)),
        )
    elif aspect == "acoustic":
        # sound / vibration / frequency: SPM + phonotactic vs 1/e
        phon_dev = abs(phon - 1.0 / E)
        breath = abs(spm_mean_len - BREATH) / max(BREATH, 1e-9)
        delta_theta = min(
            breath + phon_dev + (1 - spm_ent_norm) / PHI + spm_unk_frac * PHI,
            PI / 2,
        )
        delta_psi = min(len_phase / PHI + phon_dev, PI / 2)
        rho = max(1 / PHI, C_EFF * (1.0 - phon_dev) * (C_EFF + spm_ent_norm) / (1 + C_EFF))
    else:  # visual / written form
        # optics: letter regularity, class entropy, space rhythm
        vis_stress = (
            abs(vis["letter_frac"] - (1.0 / PHI))  # letter mass near 1/φ?
            + abs(vis["space_frac"] - 1.0 / (PHI * PHI))
            + (1.0 - vis["class_ent_norm"]) / PHI
            + vis["other_frac"] * PHI
        )
        delta_psi = min(vis_stress * (1.0 - gen_rank / PHI), PI / 2)
        delta_theta = min(len_phase + vis["other_frac"] * PHI, PI / 2)
        rho = max(1 / PHI, C_EFF * vis["letter_frac"] * (C_EFF + vis["class_ent_norm"]) / (1 + C_EFF))

    hits = max(0.0, (1.0 - nll_rank) * E)
    scale = min(lh / float(ls), PHI)
    amplitude = rho * (C_EFF + rank_p)
    trend_bias = 0.0 if lh >= 2 else -1.0 / PHI

    return mod.ScalarInput(
        N=mpf(N),
        P=mpf(P),
        D_eff=mpf(D_eff),
        delta_psi=mpf(delta_psi),
        delta_theta=mpf(delta_theta),
        recent_hits=mpf(hits),
        rho=mpf(rho),
        observed=True,
        scale=mpf(scale),
        amplitude=mpf(amplitude),
        trend_bias=mpf(trend_bias),
    )


def associate_S(S_m: float, S_a: float, S_v: float, PHI: float) -> float:
    """
    Golden association: 1 + 1/φ + 1/φ² = 2
    S_assoc = (S_m + S_a/φ + S_v/φ²) / 2
    Meaning primary; acoustic next; visual tertiary — all seed weights.
    """
    return (S_m + S_a / PHI + S_v / (PHI * PHI)) / 2.0


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
    if not feats or len(feats) != n:
        return None
    return feats


def main() -> None:
    t0 = time.perf_counter()
    print("=== FSOT associate language: sound + vision + meaning ===", flush=True)
    mod, path, pin_ok, dig = load_authority()
    PHI, E, C_EFF, K = float(mod.PHI), float(mod.E), float(mod.C_EFF), float(mod.K)
    D_m, _, _ = domain_cfg(mod, "Biology", (12.0, 0.08, 1.0))
    D_a, _, _ = domain_cfg(mod, "Acoustics", (10.0, 0.3, 1.0))
    D_v, _, _ = domain_cfg(mod, "Optics", (10.0, 0.6, 1.0))
    print(f"pin_ok={pin_ok} K={K:.6f} φ={PHI:.6f}", flush=True)
    print(f"domains meaning D={D_m} acoustic D={D_a} visual D={D_v}", flush=True)
    print(f"S_assoc = (S_m + S_a/φ + S_v/φ²)/2", flush=True)

    ds = load_dataset("wmt/wmt14", "de-en", split="test")
    refs = [ex["translation"]["en"] for ex in ds]
    srcs = [ex["translation"]["de"] for ex in ds]
    n = len(refs)

    pools: List[List[dict]] = [[] for _ in range(n)]
    for key in NLLB33_KEYS:
        rows = load_rows(key, n)
        if not rows:
            continue
        print(f"  pool {key}", flush=True)
        for i in range(n):
            for h, s in zip(rows[i]["hyps"], rows[i]["scores"]):
                pools[i].append({"hyp": h, "gen": float(s)})
    for i in range(n):
        best = {}
        for c in pools[i]:
            h = c["hyp"]
            if h not in best or c["gen"] > best[h]["gen"]:
                best[h] = c
        pools[i] = list(best.values())

    feats = load_feats("feat_nllb33_v3", n) or load_feats("feat_nllb33_v2", n)
    if feats is None:
        raise RuntimeError("need feat cache")
    feat_by_hyp = []
    for i in range(n):
        m = {f["hyp"]: f for f in feats[i] if f.get("hyp")}
        feat_by_hyp.append(m)

    hyps_assoc, hyps_gen = [], []
    mean_S = 0.0
    n_scored = 0
    samples = []

    for i in range(n):
        cands = pools[i]
        if not cands:
            hyps_assoc.append("")
            hyps_gen.append("")
            continue
        nlls, encs, gens = [], [], []
        for c in cands:
            f = feat_by_hyp[i].get(c["hyp"], {})
            nlls.append(float(f.get("tf_nll", 5.0)))
            encs.append(float(f.get("enc_norm", 1.0)))
            gens.append(c["gen"])
        nr = rank01(nlls, higher_better=False)
        er = rank01(encs, higher_better=True)
        gr = rank01(gens, higher_better=True)

        scored = []
        for j, c in enumerate(cands):
            f = feat_by_hyp[i].get(c["hyp"], {})
            vis = visual_form_stats(c["hyp"])
            phon = phonotactic_proxy(c["hyp"])
            kw = dict(
                nll_rank=nr[j],
                enc_rank=er[j],
                gen_rank=gr[j],
                enc_norm=float(f.get("enc_norm", encs[j])),
                spm_ent_norm=float(f.get("spm_ent_norm", 1 / PHI)),
                spm_mean_len=float(f.get("spm_mean_len", PHI * E)),
                spm_n_pieces=int(f.get("spm_n_pieces", max(1, len(toks(c["hyp"]))))),
                spm_unk_frac=float(f.get("spm_unk_frac", 0.0)),
                hyp_len_tok=int(f.get("hyp_len_tok", len(toks(c["hyp"])))),
                src_len_tok=int(f.get("src_len_tok", len(toks(srcs[i])))),
                vis=vis,
                phon=phon,
            )
            Sm, _, _, _ = split_terms(
                mod, map_aspect(mod, D_eff=D_m, aspect="meaning", **kw)
            )
            Sa, _, _, _ = split_terms(
                mod, map_aspect(mod, D_eff=D_a, aspect="acoustic", **kw)
            )
            Sv, _, _, _ = split_terms(
                mod, map_aspect(mod, D_eff=D_v, aspect="visual", **kw)
            )
            S = associate_S(Sm, Sa, Sv, PHI)
            scored.append(
                {
                    "hyp": c["hyp"],
                    "S": S,
                    "S_m": Sm,
                    "S_a": Sa,
                    "S_v": Sv,
                    "gen": c["gen"],
                }
            )
            mean_S += S
            n_scored += 1

        b = max(scored, key=lambda x: x["S"])
        bg = max(scored, key=lambda x: x["gen"])
        hyps_assoc.append(b["hyp"])
        hyps_gen.append(bg["hyp"])
        if i < 3 or i in (500, 1500, 2500):
            samples.append(
                {
                    "i": i,
                    "S": b["S"],
                    "S_m": b["S_m"],
                    "S_a": b["S_a"],
                    "S_v": b["S_v"],
                    "pick": b["hyp"][:90],
                    "same_gen": b["hyp"] == bg["hyp"],
                }
            )
        if i % 500 == 0:
            print(
                f"  {i}/{n} S={b['S']:.4f} m={b['S_m']:.3f} a={b['S_a']:.3f} v={b['S_v']:.3f}",
                flush=True,
            )

    sacre_a = sacrebleu.corpus_bleu(hyps_assoc, [refs]).score
    sacre_g = sacrebleu.corpus_bleu(hyps_gen, [refs]).score
    chrf_a = sacrebleu.corpus_chrf(hyps_assoc, [refs]).score

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "mission": "FSOT associate sound+vision+meaning under seed law",
        "formula": "S = K*(T1+T2+T3) per aspect; S_assoc=(S_m + S_a/φ + S_v/φ²)/2",
        "pin": "D1D38A",
        "pin_ok": pin_ok,
        "authority_path": str(path),
        "aspects": {
            "meaning": {"domain": "Biology", "D_eff": D_m},
            "acoustic": {"domain": "Acoustics", "D_eff": D_a, "note": "sound/vibration/frequency"},
            "visual": {"domain": "Optics", "D_eff": D_v, "note": "written form / symbolism surface"},
        },
        "association": "golden partition 1+1/φ+1/φ²=2",
        "no_free_parameters": True,
        "n": n,
        "mean_S_assoc": mean_S / max(1, n_scored),
        "results": {
            "FSOT_product_associate": {
                "sacrebleu": round(sacre_a, 2),
                "chrf": round(chrf_a, 2),
                "note": "argmax multi-aspect S_assoc",
            },
            "student_gen_max": {
                "sacrebleu": round(sacre_g, 2),
                "note": "NLLB-3.3B gen baseline",
            },
        },
        "best_product": {
            "name": "FSOT_product_associate",
            "sacrebleu": round(sacre_a, 2),
        },
        "gap_to_DeepL_mid40": round(40.0 - sacre_a, 2),
        "gap_to_student_gen": round(sacre_g - sacre_a, 2),
        "samples": samples,
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "honesty": (
            "Associates archive Acoustics + Optics + Biology under φ partition. "
            "Meaning/understanding primary; sound secondary; visual tertiary. "
            "No free-fit. No Qwen. Students = candidates only."
        ),
    }

    REP.mkdir(parents=True, exist_ok=True)
    outj = REP / "FSOT_ASSOCIATE_LANGUAGE.json"
    outj.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = f"""# FSOT associate language — sound · vision · meaning

**Built:** {report['built_utc']}  
**Pin D1D38A:** {pin_ok}  
**Idea:** frequency/vibration/sound + written visual form + culture/meaning/symbolism  
already solved as **domains** in the Physical Archive — associate under seeds.

## Association (seed identity)

\\[
1 + \\frac{{1}}{{\\varphi}} + \\frac{{1}}{{\\varphi^2}} = 2
\\]

\\[
S_{{\\mathrm{{assoc}}}} = \\frac{{1}}{{2}}\\left( S_{{\\mathrm{{meaning}}}} + \\frac{{S_{{\\mathrm{{acoustic}}}}}}{{\\varphi}} + \\frac{{S_{{\\mathrm{{visual}}}}}}{{\\varphi^2}} \\right)
\\]

Each \(S_* = K(T_1+T_2+T_3)\) with domain \(D_{{\\mathrm{{eff}}}}\) from the archive table.

| Aspect | Domain | D_eff | Channel |
|--------|--------|------:|---------|
| Meaning / understanding | Biology | {D_m} | NLL + gen ranks, length phase |
| Sound / vibration | Acoustics | {D_a} | SPM lattice, phonotactic vs 1/e, breath φ·e |
| Written / visual | Optics | {D_v} | letter density, class entropy, space rhythm |

## Results

| System | sacreBLEU |
|--------|----------:|
| **FSOT_product_associate** | **{sacre_a:.2f}** |
| NLLB-3.3B gen (student) | {sacre_g:.2f} |
| DeepL mid | ~40 |

Gap → student: **{report['gap_to_student_gen']}** · → DeepL mid: **{report['gap_to_DeepL_mid40']}**

## Rule

No free parameters. No ad-hoc judges. Arrange archive domains + seeds.  
Students supply candidates; **FSOT associates and ranks**.
"""
    (REP / "FSOT_ASSOCIATE_LANGUAGE.md").write_text(md, encoding="utf-8")
    print(json.dumps(report["results"], indent=2), flush=True)
    print(f"BEST sacre={sacre_a:.2f} gap_student={report['gap_to_student_gen']}", flush=True)
    print(f"WROTE {outj}", flush=True)


if __name__ == "__main__":
    main()
