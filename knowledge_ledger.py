#!/usr/bin/env python3
"""
Protofluid Language Translator — knowledge ledger.

Stores claims extracted from translations / conversation under FSOT domain tags
and law-backed scalar S. Append-only; never rewrites FSOT law.

Also retrieves **archive memory** (linguistics_derivations, linguistic targets,
kb_portable summary, formula sample) as first-class prior knowledge — read-only.

Inspired by Realities OS observer growth_ledger: densify knowledge without
mutating the constitution (fsot_compute / Lean).
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_LEDGER = ROOT / "data" / "knowledge_ledger.jsonl"
DEFAULT_INDEX = ROOT / "data" / "knowledge_ledger_index.json"


@dataclass
class KnowledgeClaim:
    """One knowledge unit grounded in translation + FSOT law panel."""
    id: str
    built_utc: str
    source_text: str
    domain: str
    meanings: List[str]
    translation: str
    S: float
    D_eff: float
    observed: bool
    authority_ok: bool
    authority: str
    claim_text: str
    tokens: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    session_id: str = ""
    turn: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeLedger:
    """Append-only JSONL ledger + lightweight inverted index."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path or DEFAULT_LEDGER)
        self.index_path = DEFAULT_INDEX
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._claims: List[Dict[str, Any]] = []
        self._by_domain: Dict[str, List[str]] = {}
        self._by_token: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        self._claims = []
        self._by_domain = {}
        self._by_token = {}
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except Exception:
                continue
            self._claims.append(c)
            self._index_claim(c)

    def _index_claim(self, c: Dict[str, Any]) -> None:
        cid = c.get("id") or ""
        dom = (c.get("domain") or "linguistic").lower()
        self._by_domain.setdefault(dom, []).append(cid)
        blob = " ".join(
            [
                c.get("claim_text") or "",
                c.get("translation") or "",
                " ".join(c.get("meanings") or []),
            ]
        ).lower()
        for tok in re.findall(r"[a-z\u0370-\u03ff]{3,}", blob):
            self._by_token.setdefault(tok, []).append(cid)

    def append(self, claim: KnowledgeClaim) -> KnowledgeClaim:
        row = claim.to_dict()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self._claims.append(row)
        self._index_claim(row)
        self._write_index_snapshot()
        return claim

    def _write_index_snapshot(self) -> None:
        snap = {
            "built_utc": datetime.now(timezone.utc).isoformat(),
            "n_claims": len(self._claims),
            "domains": {k: len(v) for k, v in self._by_domain.items()},
            "path": str(self.path),
        }
        self.index_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")

    def query(
        self,
        text: str = "",
        *,
        domain: Optional[str] = None,
        limit: int = 8,
        include_archive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve session claims by domain and/or token overlap (no LLM)."""
        scores: Dict[str, float] = {}
        tokens = set(re.findall(r"[a-z\u0370-\u03ff]{3,}", (text or "").lower()))
        if domain:
            for cid in self._by_domain.get(domain.lower(), []):
                scores[cid] = scores.get(cid, 0) + 1.5
        for t in tokens:
            for cid in self._by_token.get(t, []):
                scores[cid] = scores.get(cid, 0) + 1.0
        if not scores and not domain and not tokens:
            out = list(reversed(self._claims[-limit:]))
        else:
            ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
            by_id = {c["id"]: c for c in self._claims if "id" in c}
            out = []
            for cid, _ in ranked:
                if cid in by_id:
                    row = dict(by_id[cid])
                    row.setdefault("memory_kind", "session_ledger")
                    out.append(row)
        if include_archive:
            return self.query_unified(text, domain=domain, limit=limit)
        return out

    def query_unified(
        self,
        text: str = "",
        *,
        domain: Optional[str] = None,
        limit: int = 8,
        session_limit: int = 4,
        archive_limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Unified retrieve for Protofluid converse:
          session ledger claims + FSOT archive memory (linguistics / KB).
        Session claims ranked first when scores tie; archive never mutated.
        """
        session = self.query(text, domain=domain, limit=session_limit, include_archive=False)
        for s in session:
            s.setdefault("memory_kind", "session_ledger")

        archive: List[Dict[str, Any]] = []
        try:
            from fsot_archive_memory import get_archive_memory

            mem = get_archive_memory()
            for f in mem.query(text, domain=domain, limit=archive_limit):
                archive.append(
                    {
                        "id": f.get("id"),
                        "domain": f.get("domain"),
                        "claim_text": f.get("claim_text"),
                        "title": f.get("title"),
                        "source": f.get("source"),
                        "tags": f.get("tags") or [],
                        "S": None,
                        "memory_kind": "archive_memory",
                        "authority": "FSOT_Physical_Archive",
                        "numeric": f.get("numeric") or {},
                        "_score": f.get("_score"),
                    }
                )
        except Exception:
            archive = []

        # Prefer session when overlapping ids; archive fills remaining slots
        try:
            from converse_refine import dedup_knowledge

            session = dedup_knowledge(session, limit=session_limit)
            archive = dedup_knowledge(archive, limit=archive_limit)
        except Exception:
            pass
        seen = {c.get("id") for c in session}
        # collapse kb portable mirrors by base id
        seen_base = set()
        for c in session:
            cid = str(c.get("id") or "")
            seen_base.add(cid.split(":")[0] + ":" + cid.split(":")[1] if cid.count(":") >= 1 else cid)
        merged = list(session)
        for a in archive:
            aid = str(a.get("id") or "")
            if aid in seen:
                continue
            if aid.startswith("kb:portable_summary") and any(
                str(x.get("id") or "").startswith("kb:portable_summary") for x in merged
            ):
                continue
            merged.append(a)
            seen.add(aid)
            if len(merged) >= limit:
                break
        try:
            from converse_refine import dedup_knowledge

            return dedup_knowledge(merged, limit=limit)
        except Exception:
            return merged[:limit]

    def stats(self) -> Dict[str, Any]:
        arch: Dict[str, Any] = {}
        try:
            from fsot_archive_memory import get_archive_memory

            arch = get_archive_memory().status()
        except Exception as e:
            arch = {"load_error": str(e)}
        return {
            "n_claims": len(self._claims),
            "path": str(self.path),
            "domains": {k: len(v) for k, v in sorted(self._by_domain.items())},
            "archive_memory": arch,
        }


def claim_from_translate(
    *,
    source_text: str,
    domain: str,
    translate_out: Dict[str, Any],
    law: Dict[str, Any],
    session_id: str = "",
    turn: int = 0,
) -> KnowledgeClaim:
    meanings = list(translate_out.get("meanings") or [])
    translation = str(translate_out.get("translation") or "")
    tokens = list(translate_out.get("tokens") or [])
    # Claim text: cleaned meanings + short translation body
    body = translation.split("[FSOT")[0].strip()
    claim_text = body or " ".join(m.split(" [S=")[0] for m in meanings)
    tags = []
    if law.get("authority_ok"):
        tags.append("law_backed")
    if translate_out.get("exact_map_rate", 0) >= 0.99:
        tags.append("exact_lexicon")
    elif translate_out.get("exact_map_rate", 0) > 0:
        tags.append("partial_lexicon")
    else:
        tags.append("open_set")
    return KnowledgeClaim(
        id=str(uuid.uuid4()),
        built_utc=datetime.now(timezone.utc).isoformat(),
        source_text=source_text,
        domain=domain,
        meanings=meanings,
        translation=translation,
        S=float(law.get("S") or translate_out.get("fsot_coherence_S") or 0),
        D_eff=float(law.get("D_eff") or (translate_out.get("fsot_panel") or {}).get("D_eff") or 0),
        observed=bool(law.get("observed", True)),
        authority_ok=bool(law.get("authority_ok")),
        authority=str(law.get("authority") or "unknown"),
        claim_text=claim_text,
        tokens=tokens,
        tags=tags,
        session_id=session_id,
        turn=turn,
    )
