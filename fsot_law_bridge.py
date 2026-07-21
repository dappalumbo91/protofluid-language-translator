#!/usr/bin/env python3
"""
FSOT 2.1 law bridge for the Protofluid Language Translator.

Law authority (physical archive):
  I:\\FSOT-Physical-Archive\\02_FSOT-2.1-Lean-Full\\vendor\\fsot_compute.py
  SHA256 D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70

This module:
  - Verifies the authority hash (refuses silent drift)
  - Computes S = K·(T1+T2+T3) via archive compute_scalar when available
  - Falls back to local PFLT_FSOT_2_1_aligned.compute_S_D_chaotic only if archive missing
    (fallback is flagged — not silent law substitution)

Nothing here rewrites FSOT law. Conversation / knowledge layers may *read* S only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Canonical pin (matches I: VERIFICATION_REPORT / AUTHORITY_PIN)
AUTHORITY_SHA256 = "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70"

ARCHIVE_COMPUTE_CANDIDATES = [
    Path(r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py"),
    Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean\FSOT-2.1-Lean-main\FSOT-2.1-Lean-main\vendor\fsot_compute.py"),
    Path(r"C:\Users\damia\Desktop\FSOT document update\fsot_compute.py"),
]


@dataclass
class LawScalar:
    """Law-backed scalar panel for one domain configuration."""
    S: float
    T1: float
    T2: float
    T3: float
    K: float
    D_eff: float
    observed: bool
    delta_psi: float
    delta_theta: float
    recent_hits: float
    domain: str
    authority: str  # "archive_D1D38A" | "local_pflt_fallback"
    authority_path: str
    authority_ok: bool
    formula: str = "S = K*(T1+T2+T3)"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def find_authority_compute() -> Optional[Path]:
    for p in ARCHIVE_COMPUTE_CANDIDATES:
        if p.is_file():
            return p
    return None


def verify_authority(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or find_authority_compute()
    if path is None:
        return {
            "ok": False,
            "path": None,
            "sha256": None,
            "expected": AUTHORITY_SHA256,
            "error": "fsot_compute.py not found on archive/desktop pins",
        }
    digest = file_sha256(path)
    return {
        "ok": digest == AUTHORITY_SHA256,
        "path": str(path),
        "sha256": digest,
        "expected": AUTHORITY_SHA256,
        "match": digest == AUTHORITY_SHA256,
    }


_ARCHIVE_MOD = None
_ARCHIVE_LOAD_ERROR = ""


def _load_archive_module():
    global _ARCHIVE_MOD, _ARCHIVE_LOAD_ERROR
    if _ARCHIVE_MOD is not None:
        return _ARCHIVE_MOD
    path = find_authority_compute()
    if path is None:
        _ARCHIVE_LOAD_ERROR = "authority file missing"
        return None
    check = verify_authority(path)
    if not check["ok"]:
        _ARCHIVE_LOAD_ERROR = (
            f"authority hash mismatch: got {check['sha256'][:12]}… "
            f"expected {AUTHORITY_SHA256[:12]}…"
        )
        # Still load for numeric continuity but mark not ok
    try:
        spec = importlib.util.spec_from_file_location("fsot_compute_authority", path)
        if spec is None or spec.loader is None:
            _ARCHIVE_LOAD_ERROR = "importlib spec failed"
            return None
        mod = importlib.util.module_from_spec(spec)
        # Avoid polluting sys.modules permanently if already present
        sys.modules["fsot_compute_authority"] = mod
        spec.loader.exec_module(mod)
        _ARCHIVE_MOD = mod
        if not check["ok"] and not _ARCHIVE_LOAD_ERROR:
            _ARCHIVE_LOAD_ERROR = "hash mismatch"
        return mod
    except Exception as e:
        _ARCHIVE_LOAD_ERROR = f"{type(e).__name__}: {e}"
        return None


def compute_law_scalar(
    *,
    domain: str = "linguistic",
    D_eff: float = 12.0,
    observed: bool = True,
    delta_psi: float = 0.8,
    delta_theta: float = 1.0,
    recent_hits: float = 0.0,
    N: float = 1.0,
    P: float = 1.0,
    rho: float = 1.0,
    scale: float = 1.0,
    amplitude: float = 1.0,
    trend_bias: float = 0.0,
) -> LawScalar:
    """
    Compute FSOT scalar under law authority.
    Prefers archive fsot_compute.compute_scalar; falls back to local PFLT.
    """
    path = find_authority_compute()
    auth = verify_authority(path)
    mod = _load_archive_module()

    if mod is not None and hasattr(mod, "compute_scalar") and hasattr(mod, "ScalarInput"):
        try:
            from mpmath import mpf

            s_in = mod.ScalarInput(
                N=mpf(N),
                P=mpf(P),
                D_eff=mpf(D_eff),
                delta_psi=mpf(delta_psi),
                delta_theta=mpf(delta_theta),
                recent_hits=mpf(recent_hits),
                rho=mpf(rho),
                observed=bool(observed),
                scale=mpf(scale),
                amplitude=mpf(amplitude),
                trend_bias=mpf(trend_bias),
            )
            # Recompute terms for panel (engine returns S only)
            S = float(mod.compute_scalar(s_in))
            # Derive T1/T2/T3 for microscope-style panel (mirror engine structure)
            T1, T2, T3 = _split_terms_archive(mod, s_in)
            K = float(mod.K)
            return LawScalar(
                S=S,
                T1=T1,
                T2=T2,
                T3=T3,
                K=K,
                D_eff=float(D_eff),
                observed=bool(observed),
                delta_psi=float(delta_psi),
                delta_theta=float(delta_theta),
                recent_hits=float(recent_hits),
                domain=domain,
                authority="archive_D1D38A" if auth.get("ok") else "archive_HASH_MISMATCH",
                authority_path=str(path) if path else "",
                authority_ok=bool(auth.get("ok")),
            )
        except Exception as e:
            global _ARCHIVE_LOAD_ERROR
            _ARCHIVE_LOAD_ERROR = f"compute failed: {e}"

    # Local fallback
    from PFLT_FSOT_2_1_aligned import K as LOCAL_K, compute_S_D_chaotic

    panel = compute_S_D_chaotic(
        N=N,
        P=P,
        D_eff=D_eff,
        observed=observed,
        delta_psi=delta_psi,
        delta_theta=delta_theta,
        recent_hits=recent_hits,
        rho=rho,
        scale=scale,
        amplitude=amplitude,
        trend_bias=trend_bias,
    )
    return LawScalar(
        S=panel.S,
        T1=panel.T1,
        T2=panel.T2,
        T3=panel.T3,
        K=float(LOCAL_K),
        D_eff=panel.D_eff,
        observed=panel.observed,
        delta_psi=panel.delta_psi,
        delta_theta=panel.delta_theta,
        recent_hits=float(recent_hits),
        domain=domain,
        authority="local_pflt_fallback",
        authority_path=_ARCHIVE_LOAD_ERROR or "local",
        authority_ok=False,
    )


def _split_terms_archive(mod, s_in) -> tuple:
    """Mirror archive compute_scalar internals for T1/T2/T3 panel."""
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
        * (1 + s_in.poof * cos(s_in.theta_s + mod.PI) + s_in.suction * sin(s_in.theta_s))
    )
    acoustic = 1 + (s_in.A_bleed * sin(dt) ** 2) / mod.PHI + (s_in.A_in * cos(dt) ** 2) / mod.PHI
    phase = 1 + s_in.B_in * s_in.P_var
    T3 = valve * acoustic * phase
    return float(T1), float(T2), float(T3)


def law_status() -> Dict[str, Any]:
    path = find_authority_compute()
    v = verify_authority(path)
    mod = _load_archive_module()
    return {
        "authority_sha256_expected": AUTHORITY_SHA256,
        "authority_path": v.get("path"),
        "authority_sha256_actual": v.get("sha256"),
        "authority_ok": v.get("ok"),
        "module_loaded": mod is not None,
        "load_error": _ARCHIVE_LOAD_ERROR or None,
        "formula": "S = K*(T1+T2+T3)",
        "role": "Protofluid Language Translator law spine — not an LLM core",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(law_status(), indent=2))
    ls = compute_law_scalar(domain="linguistic", D_eff=12, observed=True, delta_psi=0.8)
    print(json.dumps(ls.to_dict(), indent=2))
