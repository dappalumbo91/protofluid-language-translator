#!/usr/bin/env python3
"""
Observer-style densify for Protofluid Language Translator.

When knowledge is thin (few session claims, high unresolved, empty archive
hits), plan rate-limited densification — without rewriting FSOT law.

Inspired by Realities OS observer (detect thin → plan ingest → growth ledger).
Desktop PFLT densifies from:
  - teach tables / classical seeds
  - archive linguistics memory
  - optional ledger claims (append-only)

Never mutates fsot_compute / Lean.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_LOG = ROOT / "data" / "observer_densify.jsonl"
DEFAULT_STATE = ROOT / "data" / "observer_densify_state.json"

# rate limits
MIN_INTERVAL_SEC = 2.0
MAX_ACTIONS_PER_TURN = 3
MAX_ACTIONS_PER_HOUR = 40


@dataclass
class DensifyAction:
    kind: str  # teach_inject | archive_note | lexicon_seed | ledger_claim
    domain: str
    detail: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DensifyPlan:
    thin: bool
    reasons: List[str]
    actions: List[DensifyAction]
    domain: str
    built_utc: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thin": self.thin,
            "reasons": self.reasons,
            "actions": [a.to_dict() for a in self.actions],
            "domain": self.domain,
            "built_utc": self.built_utc,
        }


class ObserverDensify:
    """Rate-limited densify planner + optional executor."""

    def __init__(
        self,
        log_path: Optional[Path] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        self.log_path = Path(log_path or DEFAULT_LOG)
        self.state_path = Path(state_path or DEFAULT_STATE)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.is_file():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"last_ts": 0.0, "hour_ts": 0.0, "hour_count": 0, "total": 0}

    def _save_state(self) -> None:
        self.state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def _rate_ok(self) -> bool:
        now = time.time()
        last = float(self._state.get("last_ts") or 0)
        if now - last < MIN_INTERVAL_SEC:
            return False
        hour_ts = float(self._state.get("hour_ts") or 0)
        if now - hour_ts > 3600:
            self._state["hour_ts"] = now
            self._state["hour_count"] = 0
        if int(self._state.get("hour_count") or 0) >= MAX_ACTIONS_PER_HOUR:
            return False
        return True

    def assess(
        self,
        *,
        domain: str,
        mode: str,
        unresolved_n: int,
        token_n: int,
        prior: List[Dict[str, Any]],
        teach_n: int = 0,
        product_map_rate: float = 1.0,
        ledger_domain_n: int = 0,
    ) -> DensifyPlan:
        reasons: List[str] = []
        session = [p for p in prior if p.get("memory_kind") != "archive_memory"]
        archive = [p for p in prior if p.get("memory_kind") == "archive_memory"]

        if unresolved_n >= 2:
            reasons.append(f"unresolved_tokens={unresolved_n}")
        if token_n and unresolved_n / max(token_n, 1) >= 0.4:
            reasons.append("high_unresolved_ratio")
        if product_map_rate < 0.45:
            reasons.append(f"low_map_rate={product_map_rate:.2f}")
        if len(session) == 0:
            reasons.append("empty_session_prior")
        if len(archive) == 0:
            reasons.append("empty_archive_prior")
        if ledger_domain_n < 2:
            reasons.append(f"thin_domain_ledger={ledger_domain_n}")
        if mode in {"english_meta", "science_query"} and teach_n == 0 and mode == "english_meta":
            reasons.append("missing_teach_panel")

        thin = len(reasons) >= 2 or (unresolved_n >= 2 and len(archive) == 0)
        actions: List[DensifyAction] = []

        if thin or unresolved_n >= 1:
            if mode == "english_meta":
                actions.append(
                    DensifyAction(
                        kind="teach_inject",
                        domain=domain,
                        detail="Prefer classical form↔gloss teach panel for meta questions",
                        payload={"mode": mode},
                    )
                )
            if len(archive) == 0:
                actions.append(
                    DensifyAction(
                        kind="archive_note",
                        domain=domain,
                        detail="Query FSOT linguistics_derivations / KB for domain facts",
                        payload={"domain": domain},
                    )
                )
            if unresolved_n >= 2:
                actions.append(
                    DensifyAction(
                        kind="lexicon_seed",
                        domain=domain,
                        detail="Mark open-set residuals for gap_pack / lang_tables seed",
                        payload={"unresolved_n": unresolved_n},
                    )
                )
            if ledger_domain_n < 2:
                actions.append(
                    DensifyAction(
                        kind="ledger_claim",
                        domain=domain,
                        detail="Store densify claim so future turns have session mass",
                        payload={},
                    )
                )

        actions = actions[:MAX_ACTIONS_PER_TURN]
        return DensifyPlan(
            thin=thin,
            reasons=reasons,
            actions=actions,
            domain=domain,
            built_utc=datetime.now(timezone.utc).isoformat(),
        )

    def execute(
        self,
        plan: DensifyPlan,
        *,
        ledger: Any = None,
        teach_panel: Optional[Dict[str, Any]] = None,
        law: Optional[Dict[str, Any]] = None,
        user_text: str = "",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Apply densify actions that are safe offline (append ledger notes).
        Returns log row.
        """
        applied: List[Dict[str, Any]] = []
        skipped_rate = False
        if not plan.actions:
            row = {
                "id": str(uuid.uuid4()),
                "built_utc": datetime.now(timezone.utc).isoformat(),
                "thin": plan.thin,
                "reasons": plan.reasons,
                "applied": [],
                "note": "no actions",
            }
            return row

        if not self._rate_ok() and not dry_run:
            skipped_rate = True
            row = {
                "id": str(uuid.uuid4()),
                "built_utc": datetime.now(timezone.utc).isoformat(),
                "thin": plan.thin,
                "reasons": plan.reasons,
                "applied": [],
                "note": "rate_limited",
            }
            self._append_log(row)
            return row

        for act in plan.actions:
            if act.kind == "ledger_claim" and ledger is not None and not dry_run:
                try:
                    from knowledge_ledger import KnowledgeClaim

                    claim_text = (
                        f"[densify] domain={plan.domain} reasons={','.join(plan.reasons[:4])}"
                    )
                    if teach_panel and teach_panel.get("pairs"):
                        bits = [
                            f"{p['form']}={p['gloss']}" for p in teach_panel["pairs"][:4]
                        ]
                        claim_text += " teach:" + ",".join(bits)
                    law = law or {}
                    claim = KnowledgeClaim(
                        id=str(uuid.uuid4()),
                        built_utc=datetime.now(timezone.utc).isoformat(),
                        source_text=user_text or "(densify)",
                        domain=plan.domain,
                        meanings=[],
                        translation=claim_text,
                        S=float(law.get("S") or 0),
                        D_eff=float(law.get("D_eff") or 0),
                        observed=bool(law.get("observed", True)),
                        authority_ok=bool(law.get("authority_ok")),
                        authority=str(law.get("authority") or "densify"),
                        claim_text=claim_text,
                        tokens=[],
                        tags=["densify", "observer", plan.domain],
                        session_id="observer_densify",
                        turn=0,
                    )
                    ledger.append(claim)
                    applied.append({"kind": act.kind, "ok": True, "claim_id": claim.id})
                except Exception as e:
                    applied.append({"kind": act.kind, "ok": False, "error": str(e)})
            elif act.kind == "teach_inject":
                applied.append(
                    {
                        "kind": act.kind,
                        "ok": bool(teach_panel and teach_panel.get("ok")),
                        "pairs": (teach_panel or {}).get("n", 0),
                    }
                )
            else:
                applied.append({"kind": act.kind, "ok": True, "planned": True})

        if not dry_run and applied:
            now = time.time()
            self._state["last_ts"] = now
            self._state["hour_count"] = int(self._state.get("hour_count") or 0) + 1
            self._state["total"] = int(self._state.get("total") or 0) + 1
            self._save_state()

        row = {
            "id": str(uuid.uuid4()),
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "thin": plan.thin,
            "domain": plan.domain,
            "reasons": plan.reasons,
            "applied": applied,
            "rate_limited": skipped_rate,
        }
        if not dry_run:
            self._append_log(row)
        return row

    def _append_log(self, row: Dict[str, Any]) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def format_lines(self, plan: DensifyPlan, result: Optional[Dict[str, Any]] = None) -> List[str]:
        if not plan.thin and not plan.actions:
            return []
        lines = [
            f"Observer densify: thin={plan.thin} reasons={', '.join(plan.reasons) or '—'}"
        ]
        for a in plan.actions:
            lines.append(f"  · plan[{a.kind}]: {a.detail}")
        if result and result.get("applied"):
            ok_n = sum(1 for x in result["applied"] if x.get("ok"))
            lines.append(f"  · applied {ok_n}/{len(result['applied'])} (rate_limited={result.get('rate_limited')})")
        elif result and result.get("note") == "rate_limited":
            lines.append("  · skipped (rate limited)")
        return lines


_OBS: Optional[ObserverDensify] = None


def get_observer() -> ObserverDensify:
    global _OBS
    if _OBS is None:
        _OBS = ObserverDensify()
    return _OBS
