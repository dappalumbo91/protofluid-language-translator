#!/usr/bin/env python3
"""
FSOT Physical Archive → first-class memory for the Protofluid Language Translator.

Loads (read-only, never mutates law):
  - vendor/linguistics/linguistics_derivations.json  (FSOT linguistic anchors)
  - vendor/linguistics/data/LINGUISTIC_TARGETS.csv   (measured targets + notes)
  - vendor/knowledge_base/kb_portable_summary.json   (formula inventory stats)
  - optional formula_corpus sample for concept-name retrieve

These are archive-grounded facts for converse / relay — not LLM prose.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent

ARCHIVE_ROOT_CANDIDATES = [
    Path(r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full"),
    Path(r"C:\Users\damia\Desktop\FSOT-2.1-Lean\FSOT-2.1-Lean-main\FSOT-2.1-Lean-main"),
]

LING_REL = Path("vendor/linguistics/linguistics_derivations.json")
TARGETS_REL = Path("vendor/linguistics/data/LINGUISTIC_TARGETS.csv")
KB_SUMMARY_REL = Path("vendor/knowledge_base/kb_portable_summary.json")
STRICT_EMPIRICAL_REL = Path("vendor/formula_corpus/by_domain/strict_empirical.jsonl")

# Soft expansions only for *science* cue words (not bare "language"/"word",
# which appear constantly as translation glosses).
_LING_HINTS: Dict[str, List[str]] = {
    "zipf": ["zipf", "rank", "frequency", "lexicon", "exponent"],
    "entropy": ["entropy", "shannon", "information", "bits", "letter"],
    "phoneme": ["phoneme", "phonology", "consonant", "vowel", "inventory"],
    "syntax": ["sentence", "dependency", "syntax", "parse"],
    "reading": ["saccade", "fixation", "reading"],
    "heaps": ["heaps", "vocabulary", "type", "token", "ratio"],
    "syllable": ["syllable", "mean_syllables"],
    "info_rate": ["info_rate", "bits", "pragmatics", "cross_linguistic"],
}


@dataclass
class ArchiveFact:
    """One archive-grounded knowledge unit (immutable snapshot)."""
    id: str
    source: str  # linguistics_derivations | linguistic_targets | kb_portable | formula_corpus
    domain: str
    title: str
    claim_text: str
    tags: List[str] = field(default_factory=list)
    numeric: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def find_archive_root() -> Optional[Path]:
    for p in ARCHIVE_ROOT_CANDIDATES:
        if (p / "vendor" / "fsot_compute.py").is_file() or (p / LING_REL).is_file():
            return p
    return None


class FSOTArchiveMemory:
    """
    Read-only index of FSOT linguistic anchors + KB inventory.
    Query returns ranked ArchiveFact dicts for converse relay.
    """

    def __init__(self, archive_root: Optional[Path] = None) -> None:
        self.root = Path(archive_root) if archive_root else find_archive_root()
        self.facts: List[Dict[str, Any]] = []
        self._by_token: Dict[str, List[str]] = {}
        self._by_domain: Dict[str, List[str]] = {}
        self._load_error: Optional[str] = None
        self._loaded_paths: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self.root is None or not self.root.is_dir():
            self._load_error = "FSOT archive root not found"
            return
        try:
            self._load_linguistics()
            self._load_targets()
            self._load_kb_summary()
            self._load_formula_sample(limit=400)
        except Exception as e:
            self._load_error = f"{type(e).__name__}: {e}"

    def _index(self, fact: Dict[str, Any]) -> None:
        fid = fact["id"]
        dom = (fact.get("domain") or "linguistic").lower()
        self._by_domain.setdefault(dom, []).append(fid)
        # Index title + tags + selective claim words (skip noise / unit shells).
        stop = {
            "the", "and", "for", "with", "from", "that", "this", "formula",
            "computed", "measured", "error", "pct", "group", "source", "target",
            "fsot", "derive", "dimensionless", "characters", "bits",
        }
        blob = " ".join(
            [
                fact.get("title") or "",
                " ".join(fact.get("tags") or []),
                # claim body without parenthetical derive=... status
                re.sub(r"\(derive=[^)]*\)", "", fact.get("claim_text") or ""),
            ]
        ).lower()
        for tok in re.findall(r"[a-z0-9\u0370-\u03ff]{3,}", blob):
            if tok in stop:
                continue
            self._by_token.setdefault(tok, []).append(fid)
        # also index underscored name pieces (Zipf_exponent_English → zipf, exponent, english)
        for piece in re.split(r"[_\s]+", (fact.get("title") or "").lower()):
            if len(piece) >= 3 and piece not in stop:
                self._by_token.setdefault(piece, []).append(fid)

    def _load_linguistics(self) -> None:
        path = self.root / LING_REL
        if not path.is_file():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        ders = data.get("derivations") if isinstance(data, dict) else data
        if not isinstance(ders, list):
            return
        self._loaded_paths["linguistics_derivations"] = str(path)
        for i, d in enumerate(ders):
            name = str(d.get("name") or f"derivation_{i}")
            formula = str(d.get("formula") or "")
            computed = d.get("computed")
            err = d.get("error_pct")
            status = str(d.get("status") or "")
            claim = (
                f"FSOT linguistic anchor «{name}»: computed={computed}, "
                f"error_pct={err}, formula={formula}"
            )
            if status:
                claim += f" (derive={status})"
            # Do not put short derive-status labels (e.g. "hand") in free-text tags —
            # they pollute token retrieve against English glosses like "hand".
            tags = ["fsot_anchor", "linguistics"]
            if status and len(status) >= 5:
                tags.append(status)
            fact = ArchiveFact(
                id=f"ling:{name}",
                source="linguistics_derivations",
                domain="linguistic",
                title=name,
                claim_text=claim,
                tags=tags,
                numeric={
                    "computed": computed,
                    "error_pct": err,
                },
                meta={"formula": formula, "status": status},
            ).to_dict()
            self.facts.append(fact)
            self._index(fact)

    def _load_targets(self) -> None:
        path = self.root / TARGETS_REL
        if not path.is_file():
            return
        self._loaded_paths["linguistic_targets"] = str(path)
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                measured = row.get("measured")
                unit = (row.get("unit") or "").strip()
                group = (row.get("group") or "lexicon").strip()
                note = (row.get("note") or "").strip()
                source = (row.get("source") or "").strip()
                claim = (
                    f"Linguistic target «{name}»: measured={measured} {unit} "
                    f"(group={group}). {note} Source: {source}."
                ).strip()
                fact = ArchiveFact(
                    id=f"target:{name}",
                    source="linguistic_targets",
                    domain="linguistic",
                    title=name,
                    claim_text=claim,
                    tags=["linguistic_target", group, "measured"],
                    numeric={
                        "measured": _maybe_float(measured),
                        "sigma": _maybe_float(row.get("sigma")),
                    },
                    meta={"unit": unit, "group": group, "source": source},
                ).to_dict()
                self.facts.append(fact)
                self._index(fact)

    def _load_kb_summary(self) -> None:
        path = self.root / KB_SUMMARY_REL
        if not path.is_file():
            return
        self._loaded_paths["kb_portable_summary"] = str(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        cat = data.get("catalog_formulas") or data.get("catalog_formulas_total")
        ver = data.get("observable_verified_formulas") or data.get("observable_verified_matched")
        within = data.get("within_target_2pct")
        tol = data.get("within_tolerable_5pct")
        claim = (
            f"FSOT knowledge base portable inventory: catalog_formulas={cat}, "
            f"observable_verified={ver}, within_target_2pct={within}, "
            f"within_tolerable_5pct={tol}. "
            f"Truth path = seed derivation + empirical gates; not LLM fluency."
        )
        fact = ArchiveFact(
            id="kb:portable_summary",
            source="kb_portable",
            domain="knowledge_base",
            title="FSOT_KB_portable_summary",
            claim_text=claim,
            tags=["kb", "inventory", "portable", "formulas"],
            numeric={
                "catalog_formulas": cat,
                "observable_verified": ver,
                "within_target_2pct": within,
                "within_tolerable_5pct": tol,
                "source_count": data.get("source_count"),
            },
            meta={
                "generated_at": data.get("generated_at"),
                "transfer_present": data.get("transfer_present"),
                "validation_present": data.get("validation_present"),
            },
        ).to_dict()
        self.facts.append(fact)
        self._index(fact)
        # Index the single inventory fact under extra domain tokens (no duplicate rows).
        # Mirrors used to flood replies with the same KB summary 4×.
        for extra_dom in ("cosmological", "quantum", "biological", "linguistic", "historical"):
            self._by_domain.setdefault(extra_dom, []).append(fact["id"])

    def _load_formula_sample(self, limit: int = 400) -> None:
        """
        Sample strict-empirical formulas for concept retrieval.
        Full corpus is large; we keep a diverse sample + token index.
        Prefer records with concept_name / formula_canonical.
        """
        path = self.root / STRICT_EMPIRICAL_REL
        if not path.is_file():
            return
        self._loaded_paths["strict_empirical_sample"] = str(path)
        n = 0
        seen_concepts: set = set()
        with path.open(encoding="utf-8") as f:
            for line in f:
                if n >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                concept = str(o.get("concept_name") or "").strip()
                if not concept or concept.lower() in seen_concepts:
                    continue
                # skip ultra-generic empty formula rows
                formula = (
                    o.get("formula_canonical")
                    or o.get("formula_publication")
                    or o.get("formula_raw")
                    or ""
                )
                formula = str(formula).strip()
                target_q = str(o.get("target_quantity") or "").strip()
                if not formula and not target_q:
                    continue
                seen_concepts.add(concept.lower())
                rid = str(o.get("record_id") or n)
                # crude domain from project / concept tokens
                dom = _infer_domain_from_text(concept + " " + target_q + " " + str(o.get("project") or ""))
                claim = f"KB formula «{concept}»"
                if target_q:
                    claim += f" · target={target_q}"
                if formula:
                    claim += f" · formula={formula[:180]}"
                grade = o.get("citation_grade") or o.get("method_type") or ""
                if grade:
                    claim += f" [{grade}]"
                fact = ArchiveFact(
                    id=f"formula:{rid}",
                    source="formula_corpus",
                    domain=dom,
                    title=concept,
                    claim_text=claim,
                    tags=["formula", "strict_empirical", str(grade)] if grade else ["formula", "strict_empirical"],
                    numeric={},
                    meta={
                        "record_id": rid,
                        "project": o.get("project"),
                        "citation_grade": grade,
                    },
                ).to_dict()
                self.facts.append(fact)
                self._index(fact)
                n += 1

    def query(
        self,
        text: str = "",
        *,
        domain: Optional[str] = None,
        limit: int = 8,
        sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve archive facts by token / domain overlap (no LLM)."""
        scores: Dict[str, float] = {}
        tokens = set(re.findall(r"[a-z0-9\u0370-\u03ff]{3,}", (text or "").lower()))
        # expand soft linguistic hints
        expanded = set(tokens)
        blob = (text or "").lower()
        for _, keys in _LING_HINTS.items():
            if any(k in blob for k in keys):
                expanded.update(keys)

        if domain:
            for fid in self._by_domain.get(domain.lower(), []):
                scores[fid] = scores.get(fid, 0) + 1.2

        for t in expanded:
            for fid in self._by_token.get(t, []):
                scores[fid] = scores.get(fid, 0) + 1.0

        # Linguistic *science* anchors (Zipf, entropy, …) only auto-surface when the
        # query is about those measures — not every form that glosses to "language"/"word"
        # (e.g. Latin lingua would otherwise flood classical relays with Zipf).
        science_ling = expanded & {
            "zipf",
            "entropy",
            "phoneme",
            "phonology",
            "syntax",
            "heaps",
            "lexicon",
            "orthography",
            "saccade",
            "fixation",
            "shannon",
            "syllable",
            "dependency",
            "type",
            "token",
            "bits",
        }
        ling_intent = bool(science_ling) or (domain or "").lower() in {"linguistic", "english"}
        if science_ling:
            for fid in self._by_domain.get("linguistic", []):
                scores[fid] = scores.get(fid, 0) + 0.35

        by_id = {f["id"]: f for f in self.facts}
        if not scores:
            # default: only when no signal — light KB inventory, not full Zipf dump
            preferred = [f for f in self.facts if f.get("source") == "kb_portable"]
            out = preferred[:limit] if preferred else []
            return out

        # Require a minimum score so bare domain soft-boost alone cannot flood results
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])
        out: List[Dict[str, Any]] = []
        for fid, sc in ranked:
            if sc < 0.9 and not ling_intent:
                continue
            if fid not in by_id:
                continue
            fact = by_id[fid]
            if sources and fact.get("source") not in sources:
                continue
            row = dict(fact)
            row["_score"] = sc
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def status(self) -> Dict[str, Any]:
        by_src: Dict[str, int] = {}
        for f in self.facts:
            s = f.get("source") or "?"
            by_src[s] = by_src.get(s, 0) + 1
        return {
            "archive_root": str(self.root) if self.root else None,
            "n_facts": len(self.facts),
            "by_source": by_src,
            "loaded_paths": self._loaded_paths,
            "load_error": self._load_error,
            "role": "FSOT archive memory — linguistics anchors + KB inventory (read-only)",
        }


def _maybe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _infer_domain_from_text(text: str) -> str:
    t = (text or "").lower()
    pairs = [
        ("linguistic", ["language", "linguistic", "word", "phoneme", "zipf", "syntax"]),
        ("genomic", ["gene", "dna", "genome", "codon", "smiles", "protein"]),
        ("biological", ["cell", "biology", "organism", "neuron", "brain"]),
        ("quantum", ["quantum", "qubit", "photon", "entangle"]),
        ("cosmological", ["cosmo", "galaxy", "hubble", "universe", "cmb"]),
        ("nuclear", ["nuclear", "fission", "fusion", "isotope"]),
        ("material", ["material", "crystal", "alloy", "metal"]),
        ("neural", ["neural", "neuro", "synapse", "cortex"]),
        ("historical", ["history", "empire", "rome", "ancient"]),
    ]
    best, score = "scientific", 0
    for dom, keys in pairs:
        sc = sum(1 for k in keys if k in t)
        if sc > score:
            best, score = dom, sc
    return best


# Module-level singleton (lazy)
_MEMORY: Optional[FSOTArchiveMemory] = None


def get_archive_memory() -> FSOTArchiveMemory:
    global _MEMORY
    if _MEMORY is None:
        _MEMORY = FSOTArchiveMemory()
    return _MEMORY


if __name__ == "__main__":
    mem = get_archive_memory()
    print(json.dumps(mem.status(), indent=2))
    print("--- query zipf entropy ---")
    for f in mem.query("zipf entropy language word", domain="linguistic", limit=5):
        print(f"  [{f.get('source')}] {f.get('claim_text', '')[:140]}")
    print("--- query quantum formula ---")
    for f in mem.query("quantum energy photon", domain="quantum", limit=4):
        print(f"  [{f.get('source')}] {f.get('title')}: {f.get('claim_text', '')[:100]}")
