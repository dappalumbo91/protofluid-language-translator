#!/usr/bin/env python3
"""
Open-set gap-fill student for PFLT.

When a token is missing from the lexicon, propose a meaning from nearest
neighbors (edit similarity + shared character 3-grams), then accept only if
evidence clears an explicit gate (not free neural MT).

Waveform TTS is NOT used. This is form→meaning under FSOT teacher gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, compute_S_D_chaotic


def _norm(s: str) -> str:
    s = s.lower().strip()
    # strip combining marks roughly; keep greek letters
    s = re.sub(r"[^\w\u0370-\u03ff\u1f00-\u1fff]+", "", s, flags=re.UNICODE)
    return s


def edit_sim(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    if abs(n - m) > max(4, int(0.6 * max(n, m))):
        return 0.0
    prev = list(range(m + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return 1.0 - prev[m] / max(n, m)


def trigram_dice(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if len(a) < 2 or len(b) < 2:
        return 1.0 if a == b else 0.0

    def grams(s: str):
        s = f"^{s}$"
        return {s[i : i + 3] for i in range(len(s) - 2)}

    A, B = grams(a), grams(b)
    if not A or not B:
        return 0.0
    return 2 * len(A & B) / (len(A) + len(B))


def combined_sim(a: str, b: str) -> float:
    return 0.65 * edit_sim(a, b) + 0.35 * trigram_dice(a, b)


@dataclass
class GapProposal:
    token: str
    proposed_meaning: str
    donor_token: str
    similarity: float
    support: int
    accepted: bool
    reason: str
    fsot_S: float


class GapFillStudent:
    def __init__(self, lexicon: Dict[str, str], context: str = "historical"):
        # Prefer multi-char keys as donors
        self.lex = {k: v for k, v in lexicon.items() if len(_norm(k)) >= 2}
        self.keys = list(self.lex.keys())
        self.context = context
        # index by first char for speed
        self.by_prefix: Dict[str, List[str]] = {}
        for k in self.keys:
            nk = _norm(k)
            if not nk:
                continue
            self.by_prefix.setdefault(nk[0], []).append(k)

    def _candidates(self, token: str, limit_bucket: int = 400) -> Iterable[str]:
        nk = _norm(token)
        if not nk:
            return []
        bucket = self.by_prefix.get(nk[0], [])
        L = len(nk)
        # Always length-band first on large lexica
        if len(self.keys) > 20000:
            band = [k for k in bucket if abs(len(k) - L) <= 3][:limit_bucket]
            if len(band) < 30 and len(nk) >= 3:
                # secondary: same 2-char prefix across all keys is too slow — stick to band
                return band
            return band
        if len(bucket) > limit_bucket:
            band = [k for k in bucket if abs(len(_norm(k)) - L) <= 3]
            return band[:limit_bucket] if band else bucket[:limit_bucket]
        if len(bucket) < 20:
            extra = [k for k in self.keys if abs(len(_norm(k)) - L) <= 2][:400]
            return list(dict.fromkeys(list(bucket) + extra))
        return bucket

    def propose(self, token: str, top_k: int = 5) -> Optional[GapProposal]:
        if not token or token in self.lex or _norm(token) in self.lex:
            return None
        scored: List[Tuple[float, str]] = []
        for donor in self._candidates(token):
            s = combined_sim(token, donor)
            if s >= 0.35:
                scored.append((s, donor))
        if not scored:
            return None
        scored.sort(reverse=True)
        top = scored[:top_k]
        best_sim, best_donor = top[0]
        # support: how many top donors share same meaning
        meaning = self.lex[best_donor]
        support = sum(1 for s, d in top if self.lex[d] == meaning and s >= 0.45)
        # also support by high-sim neighbors even if different meaning count
        support = max(support, sum(1 for s, _ in top if s >= 0.55))

        p = DOMAIN_PARAMS.get(self.context, DOMAIN_PARAMS.get("linguistic", {
            "D_eff": 12, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0
        }))
        panel = compute_S_D_chaotic(
            D_eff=float(p["D_eff"]),
            observed=bool(p["observed"]),
            delta_psi=float(p.get("delta_psi", 0.8)),
            delta_theta=float(p.get("delta_theta", 1.0)),
        )
        S = panel.S
        if not (S == S) or abs(S) > 1e3:
            return GapProposal(token, meaning, best_donor, best_sim, support, False, "scalar_unhealthy", S)

        # Prefer content glosses; slightly looser gates when donor meaning is concrete
        try:
            from meaning_clean import content_score, is_meta_meaning

            cscore = content_score(meaning)
            meta = is_meta_meaning(meaning)
        except Exception:
            cscore, meta = 0.5, False

        if meta:
            # require stronger evidence before transferring grammatical meta
            if best_sim >= 0.88 and support >= 2:
                ok, reason = True, "high_sim_meta_donor"
            else:
                ok, reason = False, "meta_meaning_blocked"
        elif best_sim >= 0.74 and support >= 1:
            ok, reason = True, "high_form_similarity"
        elif best_sim >= 0.58 and support >= 2:
            ok, reason = True, "moderate_sim_multi_neighbor"
        elif best_sim >= 0.48 and support >= 3 and cscore >= 0.5:
            ok, reason = True, "neighborhood_vote_content"
        elif best_sim >= 0.70 and cscore >= 0.7:
            ok, reason = True, "high_sim_content_gloss"
        else:
            ok, reason = False, "below_evidence_threshold"

        return GapProposal(
            token=token,
            proposed_meaning=meaning if ok else f"unverified_near_{meaning}",
            donor_token=best_donor,
            similarity=round(best_sim, 4),
            support=support,
            accepted=ok,
            reason=reason,
            fsot_S=float(S),
        )

    def fill(self, token: str) -> Optional[Tuple[str, GapProposal]]:
        prop = self.propose(token)
        if prop and prop.accepted:
            return prop.proposed_meaning, prop
        return None
