#!/usr/bin/env python3
"""
Knowledge ledger display hygiene for Protofluid.

Append-only history keeps old flowing_* claims; display layer cleans them
so multi-turn recall is readable without mutating the JSONL store.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

_FLUID = ("resonant_", "flowing_", "softened_", "stabilized_")
_SHELLS = {
    "narrative_flow",
    "heritage_flow",
    "generic_dynamics",
    "fluid_resonance",
    "life_process",
    "quantum_state",
    "cosmic_flow",
    "cosmic_event",
}


def strip_fluid_tokens(text: str) -> str:
    t = text or ""
    for p in _FLUID:
        t = t.replace(p, "")
    # collapse multi-spaces / " · " cleanup
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"(?:^|\s)flowing_(?=\S)", " ", t)
    return t.strip()


def claim_display_text(claim: Dict[str, Any], *, max_len: int = 160) -> str:
    raw = (claim.get("claim_text") or claim.get("translation") or "").strip()
    if not raw:
        return ""
    cleaned = strip_fluid_tokens(raw)
    # densify tags keep as-is
    if cleaned.startswith("[densify]"):
        return cleaned[:max_len]
    # if mostly shells after clean, mark legacy
    toks = re.findall(r"[a-z_]+", cleaned.lower())
    if toks and sum(1 for x in toks if x in _SHELLS or x == "unresolved") >= max(1, len(toks) // 2):
        return f"(legacy soft-shell claim) {cleaned[: max(0, max_len - 28)]}"
    # normalize underscore phrases for display
    pretty = cleaned.replace("_", " ")
    pretty = re.sub(r"\s+", " ", pretty).strip()
    if len(pretty) > max_len:
        pretty = pretty[: max_len - 1] + "…"
    return pretty


def is_low_quality_claim(claim: Dict[str, Any]) -> bool:
    raw = (claim.get("claim_text") or "").lower()
    if not raw.strip():
        return True
    if raw.count("flowing_") >= 3 and "densify" not in raw:
        return True
    shells = sum(1 for s in _SHELLS if s in raw)
    if shells >= 2:
        return True
    return False


def filter_session_claims(
    claims: Sequence[Dict[str, Any]],
    *,
    limit: int = 4,
    drop_low_quality: bool = True,
) -> List[Dict[str, Any]]:
    """Prefer cleaner / densify / recent claims for display."""
    scored: List[tuple] = []
    for i, c in enumerate(claims):
        score = 0.0
        # recency: later in list or higher turn
        score += float(c.get("turn") or 0) * 0.1
        score += i * 0.01
        ct = (c.get("claim_text") or "")
        if "densify" in ct or "teach:" in ct:
            score += 3.0
        if " ↔ " in ct or " · " in ct:
            score += 1.5
        if drop_low_quality and is_low_quality_claim(c):
            score -= 5.0
        if ct.count("flowing_") >= 2:
            score -= 2.0
        # clean display available
        disp = claim_display_text(c)
        if disp.startswith("(legacy"):
            score -= 1.5
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    out = []
    for sc, c in scored:
        if drop_low_quality and sc < -3:
            continue
        row = dict(c)
        row["claim_text_display"] = claim_display_text(c)
        out.append(row)
        if len(out) >= limit:
            break
    # fallback if everything filtered
    if not out and claims:
        for c in list(claims)[:limit]:
            row = dict(c)
            row["claim_text_display"] = claim_display_text(c)
            out.append(row)
    return out
