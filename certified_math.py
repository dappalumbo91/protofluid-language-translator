#!/usr/bin/env python3
"""
Certified numeric gate for Protofluid Language Translator.

Rule (archive certified-agent culture):
  - Numeric claims presented as FSOT / physical law must come from pinned
    fsot_compute (D1D38A) or declared archive linguistics anchors.
  - Free-form "vibes math" is refused or marked uncertified.

Does not rewrite law — only certifies or refuses display of numbers.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Patterns that look like someone asserting a law-level number
_NUMERIC_CLAIM = re.compile(
    r"(?i)(?:\bS\s*=\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?))"
    r"|(?:\b(?:zipf|entropy|heaps)\b[^\d]{0,24}(\d+\.?\d*))"
    r"|(?:\b(\d+\.?\d*)\s*(?:bits?(?:/letter|/s)?|dimensionless)?\b)"
)

_FSOT_S_TALK = re.compile(
    r"(?i)\b(fsot|scalar|coherence|S\s*=|T1|T2|T3|D_eff|domain scalar)\b"
)
_LING_MEASURE = re.compile(
    r"(?i)\b(zipf|entropy|heaps|shannon|bits?\s*/\s*letter|type[- ]token)\b"
)


@dataclass
class CertResult:
    ok: bool
    certified: List[Dict[str, Any]] = field(default_factory=list)
    refused: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    engine: str = "pflt_certified_math_v0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _archive_ling_numbers() -> Dict[str, Dict[str, Any]]:
    """Pull measured/computed linguistics anchors for certification."""
    out: Dict[str, Dict[str, Any]] = {}
    try:
        from fsot_archive_memory import get_archive_memory

        mem = get_archive_memory()
        for f in mem.facts:
            if f.get("source") not in {"linguistics_derivations", "linguistic_targets"}:
                continue
            title = (f.get("title") or "").lower()
            num = f.get("numeric") or {}
            if "zipf" in title:
                out["zipf"] = {
                    "value": num.get("measured", num.get("computed")),
                    "title": f.get("title"),
                    "source": f.get("source"),
                    "claim": f.get("claim_text"),
                }
            if "letter_entropy" in title or "entropy" in title and "letter" in title:
                out["letter_entropy"] = {
                    "value": num.get("measured", num.get("computed")),
                    "title": f.get("title"),
                    "source": f.get("source"),
                    "claim": f.get("claim_text"),
                }
            if "heaps" in title:
                out["heaps"] = {
                    "value": num.get("measured", num.get("computed")),
                    "title": f.get("title"),
                    "source": f.get("source"),
                    "claim": f.get("claim_text"),
                }
    except Exception:
        pass
    return out


def certify_turn(
    text: str,
    *,
    law: Optional[Dict[str, Any]] = None,
    domain: str = "linguistic",
    archive_facts: Optional[List[Dict[str, Any]]] = None,
) -> CertResult:
    """
    Certify numeric content for this conversational turn.
    """
    law = law or {}
    text = text or ""
    certified: List[Dict[str, Any]] = []
    refused: List[str] = []
    notes: List[str] = []

    wants_s = bool(_FSOT_S_TALK.search(text))
    wants_ling = bool(_LING_MEASURE.search(text))

    # Always certify the turn's law scalar when authority_ok
    if law.get("authority_ok"):
        certified.append(
            {
                "kind": "fsot_law_scalar",
                "domain": domain,
                "S": law.get("S"),
                "D_eff": law.get("D_eff"),
                "authority": law.get("authority"),
                "formula": "S = K*(T1+T2+T3)",
                "pin": "D1D38A",
            }
        )
    elif wants_s:
        refused.append(
            "FSOT scalar requested but authority_ok=false — refuse uncertified S"
        )
        notes.append("Re-run with archive fsot_compute pin (D1D38A) for certified S.")

    # Linguistics measures from archive only
    if wants_ling:
        anchors = _archive_ling_numbers()
        if "zipf" in text.lower() and "zipf" in anchors:
            certified.append({"kind": "linguistic_anchor", **anchors["zipf"]})
        elif "zipf" in text.lower():
            refused.append("Zipf number not found in archive linguistics anchors")
        if "entropy" in text.lower() and "letter_entropy" in anchors:
            certified.append({"kind": "linguistic_anchor", **anchors["letter_entropy"]})
        if "heaps" in text.lower() and "heaps" in anchors:
            certified.append({"kind": "linguistic_anchor", **anchors["heaps"]})

    # Explicit S= user assertions → recompute and compare
    for m in re.finditer(r"(?i)\bS\s*=\s*([+-]?\d+\.?\d*)", text):
        claimed = float(m.group(1))
        true_s = float(law.get("S") or 0)
        if law.get("authority_ok"):
            if abs(claimed - true_s) < 1e-3:
                certified.append(
                    {
                        "kind": "user_S_match",
                        "claimed": claimed,
                        "authority_S": true_s,
                    }
                )
            else:
                refused.append(
                    f"User claimed S={claimed} but authority S={true_s:+.6f} — reject free number"
                )
                certified.append(
                    {
                        "kind": "authority_S_override",
                        "claimed": claimed,
                        "authority_S": true_s,
                        "note": "law wins",
                    }
                )
        else:
            refused.append(f"Uncertified S={claimed} (no authority pin)")

    # Free floating "law constants" without archive context
    if re.search(r"(?i)\b(?:exactly|must be|law says)\s+\d+\.?\d*", text) and not (
        wants_ling or wants_s or law.get("authority_ok")
    ):
        refused.append("Imperative numeric law claim without certified source")

    ok = len(refused) == 0 or len(certified) > 0
    if certified and not refused:
        notes.append("All numeric display paths certified under FSOT pin / archive anchors.")
    elif refused and certified:
        notes.append("Mixed: authority values certified; free claims refused.")
    elif refused:
        notes.append("Numeric claims refused — no vibes math as law.")
    else:
        notes.append("No numeric law claims detected.")

    return CertResult(ok=ok, certified=certified, refused=refused, notes=notes)


def format_cert_lines(cert: CertResult) -> List[str]:
    if not cert.certified and not cert.refused:
        return []
    lines = ["Certified math gate:"]
    for c in cert.certified[:5]:
        kind = c.get("kind")
        if kind == "fsot_law_scalar":
            lines.append(
                f"  · OK law S={c.get('S'):+.6f} domain={c.get('domain')} pin={c.get('pin')}"
            )
        elif kind == "linguistic_anchor":
            lines.append(
                f"  · OK {c.get('title')}: {c.get('value')} [{c.get('source')}]"
            )
        elif kind == "authority_S_override":
            lines.append(
                f"  · OVERRIDE claimed S={c.get('claimed')} → authority S={c.get('authority_S'):+.6f}"
            )
        else:
            lines.append(f"  · OK {kind}: { {k: v for k, v in c.items() if k != 'claim'} }")
    for r in cert.refused[:4]:
        lines.append(f"  · REFUSE: {r}")
    return lines
