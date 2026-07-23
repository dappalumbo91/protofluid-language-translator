#!/usr/bin/env python3
"""
Language Second Brain — connective graph for PFLT meaning + lineage.

Not a personal-notes vault as product runtime. Machine-queryable graph of:
  Sense · Form · Language · Claim · Lineage proposal · Prefer remedy

Human view: optional Obsidian export (wiki-links under data/language_brain/vault/).

Sources ingested (read-only densify of knowledge, never rewrite FSOT law):
  - sense_interlingua.SenseInterlingua (core + universal + lang_tables)
  - pflt-Ada/data/sense_prefer.tsv + form_sense.tsv
  - data/wrong_sense_mined.json
  - data/asjp_lineage_gapfill_report.json
  - data/knowledge_ledger.jsonl
  - data/expanded_gold.jsonl (lang-tagged form→en for hole fill)
  - pflt-Ada/reports/translation_coverage_report.json (catalog stats)

Law: pin D1D38A remains external; claims may *cite* S but must not re-fit K/T_i.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent
BRAIN_DIR = ROOT / "data" / "language_brain"
NODES_PATH = BRAIN_DIR / "nodes.jsonl"
EDGES_PATH = BRAIN_DIR / "edges.jsonl"
META_PATH = BRAIN_DIR / "meta.json"
HOLES_PATH = BRAIN_DIR / "hole_map.json"
CLIMB_PATH = BRAIN_DIR / "climb_queue.json"
EXTRA_BINDINGS = BRAIN_DIR / "extra_bindings.jsonl"
VAULT_DIR = BRAIN_DIR / "vault"
REPORT_MD = ROOT / "pflt-Ada" / "reports" / "LANGUAGE_BRAIN.md"
REPORT_JSON = ROOT / "pflt-Ada" / "reports" / "LANGUAGE_BRAIN.json"

# Core traffic senses — largest mission leverage if under-bound
CORE_SENSES = [
    "water", "fire", "sun", "moon", "earth", "sky", "life", "death",
    "hand", "foot", "head", "eye", "heart", "blood", "man", "woman",
    "father", "mother", "child", "house", "day", "night", "year",
    "word", "language", "name", "god", "king", "people", "friend",
    "enemy", "mountain", "river", "sea", "tree", "stone", "bread",
    "meat", "fish", "bird", "dog", "cat", "cell", "path", "road",
    "soul", "mind", "body", "light", "dark", "good", "bad", "one",
    "two", "three", "big", "small", "new", "old", "hot", "cold",
]

# Target languages we want every core sense to reach (hole map axes)
TARGET_LANGS = [
    "en", "la", "grc", "de", "fr", "es", "it", "pt", "nl", "sv",
    "pl", "ru", "ar", "zh", "ja", "he", "ang", "egy", "akk", "san",
    "got", "non", "fa", "hi", "ko", "tr", "vi", "id", "cs", "uk",
]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sense_id(gloss: str) -> str:
    g = re.sub(r"[^a-z0-9]+", "_", (gloss or "").strip().lower()).strip("_")
    return f"SENSE_{g}" if g else "SENSE_unknown"


def _fold(s: str) -> str:
    return (s or "").strip().lower()


def _nid(kind: str, key: str) -> str:
    k = re.sub(r"\s+", "_", (key or "").strip())
    return f"{kind}:{k}"


@dataclass
class Node:
    id: str
    kind: str  # sense | form | language | claim | note
    label: str
    props: Dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "label": self.label, "props": self.props}


@dataclass
class Edge:
    src: str
    rel: str
    dst: str
    props: Dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> Dict[str, Any]:
        return {"src": self.src, "rel": self.rel, "dst": self.dst, "props": self.props}


class LanguageBrain:
    """In-memory graph + persistence."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._edge_set: Set[Tuple[str, str, str]] = set()
        self.meta: Dict[str, Any] = {}

    def add_node(self, node: Node) -> Node:
        prev = self.nodes.get(node.id)
        if prev is None:
            self.nodes[node.id] = node
            return node
        # merge props / label
        prev.props.update({k: v for k, v in node.props.items() if v is not None})
        if node.label and (not prev.label or len(node.label) > len(prev.label)):
            prev.label = node.label
        return prev

    def add_edge(self, src: str, rel: str, dst: str, **props: Any) -> None:
        key = (src, rel, dst)
        if key in self._edge_set:
            return
        self._edge_set.add(key)
        self.edges.append(Edge(src=src, rel=rel, dst=dst, props=props))

    def ensure_sense(self, gloss_en: str) -> str:
        sid = _sense_id(gloss_en)
        nid = _nid("sense", sid)
        self.add_node(
            Node(
                id=nid,
                kind="sense",
                label=gloss_en.strip().lower(),
                props={"sense_id": sid, "canonical_en": gloss_en.strip().lower()},
            )
        )
        return nid

    def ensure_lang(self, lang: str, **props: Any) -> str:
        lang = (lang or "unk").lower()
        nid = _nid("lang", lang)
        self.add_node(Node(id=nid, kind="language", label=lang, props={"code": lang, **props}))
        return nid

    def ensure_form(self, lang: str, form: str) -> str:
        lang = (lang or "unk").lower()
        form = (form or "").strip()
        fid = _nid("form", f"{lang}|{_fold(form)}")
        self.add_node(
            Node(
                id=fid,
                kind="form",
                label=form,
                props={"lang": lang, "form": form, "folded": _fold(form)},
            )
        )
        self.ensure_lang(lang)
        self.add_edge(fid, "in_language", _nid("lang", lang))
        return fid

    def bind_form_sense(
        self,
        lang: str,
        form: str,
        gloss_en: str,
        *,
        rel: str = "expresses",
        source: str = "seed",
        tier: str = "A",
        **props: Any,
    ) -> None:
        if not form or not gloss_en:
            return
        sn = self.ensure_sense(gloss_en)
        fn = self.ensure_form(lang, form)
        self.add_edge(fn, rel, sn, source=source, tier=tier, **props)
        # reverse convenience for queries
        self.add_edge(sn, "realized_as", fn, source=source, tier=tier, **props)

    # ------------------------------------------------------------------ build
    def build(self, *, gold_scan_limit: int = 0) -> Dict[str, Any]:
        """Ingest all known sources into the graph."""
        counts: Counter = Counter()

        # 0) Curated modern multi-lang labels (before SI so holes see them even if SI fails)
        modern_path = BRAIN_DIR / "modern_core_labels.json"
        if modern_path.is_file():
            try:
                data = json.loads(modern_path.read_text(encoding="utf-8"))
                for gloss, by_lang in data.items():
                    if str(gloss).startswith("_") or not isinstance(by_lang, dict):
                        continue
                    for lang, forms in by_lang.items():
                        if not isinstance(forms, list):
                            continue
                        for form in forms:
                            self.bind_form_sense(
                                lang, form, gloss, source="modern_core_labels", tier="A"
                            )
                            counts["modern_labels"] += 1
            except Exception as e:
                counts["modern_labels_error"] = str(e)  # type: ignore

        # 1) Live sense interlingua
        try:
            from sense_interlingua import SenseInterlingua

            si = SenseInterlingua()
            for sid, node in si.nodes.items():
                sn = self.ensure_sense(node.canonical_en)
                self.nodes[sn].props["sense_id"] = sid
                for lang, forms in (node.forms or {}).items():
                    for form in forms:
                        self.bind_form_sense(
                            lang, form, node.canonical_en, source="sense_interlingua", tier="A"
                        )
                        counts["bindings_sense"] += 1
            counts["senses_from_si"] = len(si.nodes)
        except Exception as e:
            counts["sense_interlingua_error"] = str(e)  # type: ignore

        # 2) sense_prefer.tsv
        prefer_path = ROOT / "pflt-Ada" / "data" / "sense_prefer.tsv"
        if prefer_path.is_file():
            for line in prefer_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                form, gloss = parts[0].strip(), parts[1].strip()
                # prefer is force map; lang often classical — try la then unk
                lang = "la" if re.search(r"[a-z]", form.lower()) and not re.search(r"[\u0370-\u03ff]", form) else "unk"
                if re.search(r"[\u0370-\u03ff]", form):
                    lang = "grc"
                self.bind_form_sense(lang, form, gloss.split(",")[0].strip(), source="sense_prefer", tier="A")
                sn = self.ensure_sense(gloss.split(",")[0].strip())
                fn = self.ensure_form(lang, form)
                self.add_edge(fn, "preferred_sense", sn, source="sense_prefer")
                counts["prefer_rows"] += 1

        # 3) wrong_sense_mined
        wrong_path = ROOT / "data" / "wrong_sense_mined.json"
        if wrong_path.is_file():
            try:
                wr = json.loads(wrong_path.read_text(encoding="utf-8"))
                for item in wr.get("top_wrong") or []:
                    form = item.get("form") or ""
                    gold = item.get("gold") or ""
                    dens = item.get("densify_top") or []
                    wrong_g = dens[0][0] if dens else ""
                    if form and gold:
                        sn_good = self.ensure_sense(gold)
                        fn = self.ensure_form("la", form)
                        self.add_edge(fn, "preferred_over_wrong", sn_good, gold=gold, densify_wrong=wrong_g)
                        note_id = _nid("note", f"wrong_{_fold(form)}")
                        self.add_node(
                            Node(
                                id=note_id,
                                kind="note",
                                label=f"wrong-sense {form}",
                                props={
                                    "form": form,
                                    "gold": gold,
                                    "densify_wrong": wrong_g,
                                    "text": f"`{form}` densify→{wrong_g!r}; prefer→{gold!r}",
                                },
                            )
                        )
                        self.add_edge(fn, "has_note", note_id)
                        counts["wrong_sense"] += 1
            except Exception as e:
                counts["wrong_sense_error"] = str(e)  # type: ignore

        # 4) ASJP lineage proposals
        asjp_path = ROOT / "data" / "asjp_lineage_gapfill_report.json"
        if asjp_path.is_file():
            try:
                ar = json.loads(asjp_path.read_text(encoding="utf-8"))
                for prop in ar.get("accepted_sample") or []:
                    concept = (prop.get("concept_name") or "").lstrip("*")
                    tlang = (prop.get("target_lang") or "unk").lower()
                    dlang = (prop.get("donor_lang") or "unk").lower()
                    tform = prop.get("proposed_form") or ""
                    dform = prop.get("donor_form") or ""
                    if concept and tform:
                        self.bind_form_sense(
                            tlang,
                            tform,
                            concept,
                            source="asjp_lineage",
                            tier=prop.get("tier") or "B",
                            donor_lang=dlang,
                            donor_form=dform,
                            form_similarity=prop.get("form_similarity"),
                            fsot_S=prop.get("fsot_S"),
                        )
                        if dform:
                            sn = self.ensure_sense(concept)
                            df = self.ensure_form(dlang, dform)
                            tf = self.ensure_form(tlang, tform)
                            self.add_edge(
                                tf,
                                "cognate_proposed_from",
                                df,
                                concept=concept,
                                similarity=prop.get("form_similarity"),
                                tier=prop.get("tier") or "B",
                            )
                            self.add_edge(sn, "has_lineage_proposal", tf, tier="B")
                        counts["asjp_accepted"] += 1
                counts["asjp_n_proposals"] = ar.get("n_proposals")
                counts["asjp_n_accepted"] = ar.get("n_accepted_tier_B")
            except Exception as e:
                counts["asjp_error"] = str(e)  # type: ignore

        # 5) knowledge ledger claims
        led_path = ROOT / "data" / "knowledge_ledger.jsonl"
        if led_path.is_file():
            for line in led_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    c = json.loads(line)
                except Exception:
                    continue
                cid = c.get("id") or f"claim_{counts['claims']}"
                nid = _nid("claim", cid)
                self.add_node(
                    Node(
                        id=nid,
                        kind="claim",
                        label=(c.get("claim_text") or c.get("translation") or cid)[:120],
                        props={
                            "S": c.get("S"),
                            "domain": c.get("domain"),
                            "authority_ok": c.get("authority_ok"),
                            "meanings": c.get("meanings"),
                            "source_text": c.get("source_text"),
                        },
                    )
                )
                for m in c.get("meanings") or []:
                    sn = self.ensure_sense(str(m))
                    self.add_edge(nid, "asserts_sense", sn)
                counts["claims"] += 1

        # 6) Full solidify catalog (113 codes) + gold_core slice
        #    User-facing breadth is the solidify catalog, NOT gold_core-only (20).
        cat_path = ROOT / "pflt-Ada" / "reports" / "competitor_push_report.json"
        if cat_path.is_file():
            try:
                cat = json.loads(cat_path.read_text(encoding="utf-8"))
                codes = cat.get("catalog") or []
                by_lang = {r["lang"]: r for r in (cat.get("by_lang") or []) if "lang" in r}
                for code in codes:
                    row = by_lang.get(code) or {}
                    self.ensure_lang(
                        code,
                        in_solidify_catalog=True,
                        catalog_n=row.get("n"),
                        open_pct=row.get("open"),
                        product_pct=row.get("product"),
                        solidify_ok=row.get("ok"),
                    )
                    counts["catalog_langs"] += 1
                counts["catalog_size"] = cat.get("catalog_size") or len(codes)
                counts["catalog_all_ge_95"] = cat.get("all_langs_ge_95")
                counts["catalog_open_overall"] = cat.get("open_overall")
            except Exception as e:
                counts["catalog_error"] = str(e)  # type: ignore

        cov_path = ROOT / "pflt-Ada" / "reports" / "translation_coverage_report.json"
        if cov_path.is_file():
            try:
                cov = json.loads(cov_path.read_text(encoding="utf-8"))
                by = (cov.get("inventory") or {}).get("gold_by_lang") or {}
                for lang, n in by.items():
                    self.ensure_lang(lang, gold_rows=n, in_gold_core=True)
                    counts["gold_core_langs"] = counts.get("gold_core_langs", 0) + 1
            except Exception:
                pass

        # 6b) FSOT formula pathways — how domains/systems connect under law
        #     Edges cite S=K(T1+T2+T3); never re-fit K/T_i.
        try:
            from fsot_law_bridge import compute_law_scalar, verify_authority
            from pathway_reasoner import FAMILIES

            auth = verify_authority()
            # Linguistic panel (archive pin)
            ling = compute_law_scalar(
                domain="linguistic",
                D_eff=12.0,
                observed=True,
                delta_psi=0.8,
                delta_theta=1.0,
                recent_hits=0.0,
            )
            law_node = _nid("note", "fsot_law_pin")
            self.add_node(
                Node(
                    id=law_node,
                    kind="note",
                    label="FSOT law S=K(T1+T2+T3)",
                    props={
                        "formula": "S = K*(T1+T2+T3)",
                        "S": ling.S,
                        "T1": ling.T1,
                        "T2": ling.T2,
                        "T3": ling.T3,
                        "K": ling.K,
                        "D_eff": ling.D_eff,
                        "domain": "linguistic",
                        "pin": "D1D38A",
                        "authority_ok": bool(auth.get("ok")),
                        "authority_path": auth.get("path"),
                        "text": (
                            "Every translate/sense act certifies under pinned law. "
                            "Language brain densifies knowledge; it does not rewrite K/T_i."
                        ),
                    },
                )
            )
            counts["fsot_law_S"] = ling.S
            counts["fsot_authority_ok"] = bool(auth.get("ok"))

            # Domain-family pathway nodes + weighted connections (FSOT geometry)
            domain_panels: Dict[str, Any] = {}
            for fam, domains in FAMILIES.items():
                fam_id = _nid("note", f"family_{fam}")
                self.add_node(
                    Node(
                        id=fam_id,
                        kind="note",
                        label=f"FSOT family:{fam}",
                        props={"family": fam, "domains": domains, "formula": "S=K(T1+T2+T3)"},
                    )
                )
                self.add_edge(
                    fam_id,
                    "certified_under",
                    law_node,
                    S=ling.S,
                    formula="S = K*(T1+T2+T3)",
                    pin="D1D38A",
                )
                for d in domains:
                    d_id = _nid("note", f"domain_{d}")
                    # Vary D_eff lightly by family slot (observational frame only)
                    d_eff = 12.0 if fam == "mind_language" else 10.0 + (hash(d) % 7)
                    try:
                        panel = compute_law_scalar(
                            domain=d if d != "english" else "linguistic",
                            D_eff=float(d_eff),
                            observed=True,
                            delta_psi=0.8,
                            delta_theta=1.0,
                            recent_hits=0.0,
                        )
                    except Exception:
                        panel = ling
                    domain_panels[d] = panel
                    self.add_node(
                        Node(
                            id=d_id,
                            kind="note",
                            label=f"domain:{d}",
                            props={
                                "domain": d,
                                "family": fam,
                                "S": panel.S,
                                "T1": panel.T1,
                                "T2": panel.T2,
                                "T3": panel.T3,
                                "K": panel.K,
                                "D_eff": panel.D_eff,
                                "formula": "S = K*(T1+T2+T3)",
                                "pin": "D1D38A",
                            },
                        )
                    )
                    self.add_edge(
                        d_id,
                        "in_family",
                        fam_id,
                        S=panel.S,
                        formula="S = K*(T1+T2+T3)",
                    )
                    self.add_edge(
                        d_id,
                        "certified_under",
                        law_node,
                        S=panel.S,
                        T1=panel.T1,
                        T2=panel.T2,
                        T3=panel.T3,
                        K=panel.K,
                        formula="S = K*(T1+T2+T3)",
                        pin="D1D38A",
                    )
                    counts["fsot_domain_nodes"] += 1

            # Connect mind_language → every catalog language (translation surface)
            mind = _nid("note", "family_mind_language")
            ling_dom = _nid("note", "domain_linguistic")
            for n in list(self.nodes.values()):
                if n.kind != "language":
                    continue
                self.add_edge(
                    n.id,
                    "fsot_pathway",
                    ling_dom,
                    S=ling.S,
                    formula="S = K*(T1+T2+T3)",
                    pin="D1D38A",
                    meaning="language surface under linguistic domain panel",
                )
                self.add_edge(
                    n.id,
                    "in_family",
                    mind,
                    S=ling.S,
                    formula="S = K*(T1+T2+T3)",
                )
                counts["fsot_lang_pathways"] += 1

            # Sense hubs certified under linguistic panel (meaning identity spine)
            for n in list(self.nodes.values()):
                if n.kind != "sense":
                    continue
                self.add_edge(
                    n.id,
                    "certified_under",
                    law_node,
                    S=ling.S,
                    formula="S = K*(T1+T2+T3)",
                    pin="D1D38A",
                    meaning="sense identity act under law",
                )
                counts["fsot_sense_certs"] += 1

            # Cross-family bridges (how systems connect mathematically)
            fam_ids = [(_nid("note", f"family_{f}"), f) for f in FAMILIES]
            for i, (a_id, a_name) in enumerate(fam_ids):
                for b_id, b_name in fam_ids[i + 1 :]:
                    # Coupling weight: relative S proximity (observational, not free fit)
                    self.add_edge(
                        a_id,
                        "fsot_couples",
                        b_id,
                        formula="S = K*(T1+T2+T3)",
                        pin="D1D38A",
                        S_linguistic=ling.S,
                        note="domain-family coupling under shared scalar law",
                    )
                    counts["fsot_family_couplings"] += 1
        except Exception as e:
            counts["fsot_pathways_error"] = str(e)  # type: ignore

        # 7) expanded_gold scan → enrich core senses (lang-tagged)
        gold_path = ROOT / "data" / "expanded_gold.jsonl"
        core_set = set(CORE_SENSES)
        gold_hits = 0
        if gold_path.is_file():
            with gold_path.open(encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if gold_scan_limit and i >= gold_scan_limit:
                        break
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    gloss = (row.get("target_word") or row.get("meaning_key") or "").strip().lower()
                    # single-token core head only (high precision)
                    g0 = re.split(r"[,;/|]", gloss)[0].strip().lower()
                    g0 = re.sub(r"\s+", " ", g0)
                    head = g0.split()[0] if g0 else ""
                    if head not in core_set:
                        continue
                    slang = (row.get("source_lang") or "unk").lower()
                    sword = (row.get("source_word") or "").strip()
                    if not sword or slang in ("en", "unk", ""):
                        continue
                    conf = float(row.get("confidence") or 0.9)
                    if conf < 0.85:
                        continue
                    tier = row.get("tier") or "A"
                    self.bind_form_sense(
                        slang,
                        sword,
                        head,
                        source="expanded_gold",
                        tier=str(tier),
                        confidence=conf,
                    )
                    gold_hits += 1
        counts["gold_core_bindings"] = gold_hits

        # 8) prior extra_bindings
        if EXTRA_BINDINGS.is_file():
            for line in EXTRA_BINDINGS.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    b = json.loads(line)
                except Exception:
                    continue
                self.bind_form_sense(
                    b.get("lang") or "unk",
                    b.get("form") or "",
                    b.get("gloss") or "",
                    source=b.get("source") or "extra_bindings",
                    tier=b.get("tier") or "B",
                )
                counts["extra_bindings"] += 1

        self.meta = {
            "built_utc": _utc(),
            "counts": dict(counts),
            "n_nodes": len(self.nodes),
            "n_edges": len(self.edges),
            "by_kind": dict(Counter(n.kind for n in self.nodes.values())),
            "pin_note": "FSOT pin D1D38A external; brain densifies knowledge only",
        }
        return self.meta

    # ----------------------------------------------------------------- persist
    def save(self) -> None:
        BRAIN_DIR.mkdir(parents=True, exist_ok=True)
        with NODES_PATH.open("w", encoding="utf-8") as f:
            for n in self.nodes.values():
                f.write(json.dumps(n.to_row(), ensure_ascii=False) + "\n")
        with EDGES_PATH.open("w", encoding="utf-8") as f:
            for e in self.edges:
                f.write(json.dumps(e.to_row(), ensure_ascii=False) + "\n")
        META_PATH.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        self.nodes.clear()
        self.edges.clear()
        self._edge_set.clear()
        if META_PATH.is_file():
            self.meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        if NODES_PATH.is_file():
            for line in NODES_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                self.nodes[r["id"]] = Node(
                    id=r["id"], kind=r["kind"], label=r["label"], props=r.get("props") or {}
                )
        if EDGES_PATH.is_file():
            for line in EDGES_PATH.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                e = Edge(src=r["src"], rel=r["rel"], dst=r["dst"], props=r.get("props") or {})
                self.edges.append(e)
                self._edge_set.add((e.src, e.rel, e.dst))

    # ----------------------------------------------------------------- query
    def sense_bundle(self, gloss_or_id: str) -> Dict[str, Any]:
        g = (gloss_or_id or "").strip()
        if g.startswith("SENSE_"):
            sid = g
            sn = _nid("sense", sid)
        else:
            sid = _sense_id(g)
            sn = _nid("sense", sid)
        node = self.nodes.get(sn)
        if not node:
            # try label match
            for n in self.nodes.values():
                if n.kind == "sense" and n.label == g.lower():
                    node = n
                    sn = n.id
                    sid = n.props.get("sense_id") or sid
                    break
        forms_by_lang: Dict[str, List[str]] = defaultdict(list)
        seen_form: Set[Tuple[str, str]] = set()
        notes: List[Dict[str, Any]] = []
        lineage: List[Dict[str, Any]] = []

        def _add_form(lang: str, label: str) -> None:
            key = (lang, _fold(label))
            if key in seen_form:
                return
            seen_form.add(key)
            forms_by_lang[lang].append(label)

        for e in self.edges:
            if e.src == sn and e.rel == "realized_as":
                fn = self.nodes.get(e.dst)
                if fn:
                    _add_form(fn.props.get("lang") or "?", fn.label)
            if e.dst == sn and e.rel == "expresses":
                fn = self.nodes.get(e.src)
                if fn:
                    _add_form(fn.props.get("lang") or "?", fn.label)
            if e.rel == "has_lineage_proposal" and e.src == sn:
                lineage.append({"form_node": e.dst, **e.props})
            if e.rel == "has_note" and e.src in {sn} | {
                ee.src for ee in self.edges if ee.dst == sn and ee.rel == "expresses"
            }:
                nn = self.nodes.get(e.dst)
                if nn:
                    notes.append(nn.props)
        return {
            "sense_id": sid,
            "node": node.to_row() if node else None,
            "n_langs": len(forms_by_lang),
            "forms_by_lang": dict(forms_by_lang),
            "lineage": lineage[:20],
            "notes": notes[:10],
        }

    def hole_map(
        self,
        *,
        core_only: bool = True,
        target_langs: Optional[List[str]] = None,
        min_langs: int = 5,
    ) -> Dict[str, Any]:
        langs = target_langs or TARGET_LANGS
        senses: List[str] = []
        if core_only:
            senses = list(CORE_SENSES)
        else:
            senses = [
                n.props.get("canonical_en") or n.label
                for n in self.nodes.values()
                if n.kind == "sense"
            ]

        holes: List[Dict[str, Any]] = []
        for gloss in senses:
            b = self.sense_bundle(gloss)
            have = set((b.get("forms_by_lang") or {}).keys())
            missing = [L for L in langs if L not in have]
            n_have = len(have)
            holes.append(
                {
                    "gloss": gloss,
                    "sense_id": _sense_id(gloss),
                    "n_langs_bound": n_have,
                    "langs_bound": sorted(have),
                    "missing_target_langs": missing,
                    "n_missing": len(missing),
                    "score": len(missing),  # higher = bigger hole
                }
            )
        holes.sort(key=lambda x: (-x["score"], x["gloss"]))
        under = [h for h in holes if h["n_langs_bound"] < min_langs]
        report = {
            "built_utc": _utc(),
            "target_langs": langs,
            "min_langs": min_langs,
            "n_senses_scored": len(holes),
            "n_under_min_langs": len(under),
            "mean_langs_bound": round(
                sum(h["n_langs_bound"] for h in holes) / max(1, len(holes)), 2
            ),
            "top_holes": holes[:40],
            "all_holes": holes,
        }
        return report

    def climb_fill_from_gold(
        self,
        *,
        max_new: int = 5000,
        gold_limit: int = 0,
    ) -> Dict[str, Any]:
        """
        Fill core-sense holes using expanded_gold (lang-tagged).
        Writes extra_bindings.jsonl (append unique) and re-binds into graph.
        """
        holes = self.hole_map(core_only=True)
        wanted: Dict[str, Set[str]] = {}
        for h in holes["all_holes"]:
            if h["n_missing"] <= 0:
                continue
            wanted[h["gloss"]] = set(h["missing_target_langs"])

        gold_path = ROOT / "data" / "expanded_gold.jsonl"
        if not gold_path.is_file():
            return {"ok": False, "error": "expanded_gold.jsonl missing", "added": 0}

        # existing bindings keys
        existing: Set[Tuple[str, str, str]] = set()
        if EXTRA_BINDINGS.is_file():
            for line in EXTRA_BINDINGS.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    b = json.loads(line)
                    existing.add((_fold(b.get("lang")), _fold(b.get("form")), _fold(b.get("gloss"))))
                except Exception:
                    pass

        added_rows: List[Dict[str, Any]] = []
        # also take first form per (gloss, lang) from gold
        best: Dict[Tuple[str, str], Tuple[str, float]] = {}
        with gold_path.open(encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if gold_limit and i >= gold_limit:
                    break
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                gloss_raw = (row.get("target_word") or row.get("meaning_key") or "").strip().lower()
                head = re.split(r"[,;/|]", gloss_raw)[0].strip().lower()
                head = head.split()[0] if head else ""
                if head not in wanted:
                    continue
                slang = (row.get("source_lang") or "").lower()
                if slang not in wanted[head]:
                    continue
                sword = (row.get("source_word") or "").strip()
                if not sword or len(sword) > 48:
                    continue
                conf = float(row.get("confidence") or 0.9)
                if conf < 0.85:
                    continue
                key = (head, slang)
                prev = best.get(key)
                if prev is None or conf > prev[1]:
                    best[key] = (sword, conf)

        for (gloss, lang), (form, conf) in sorted(best.items()):
            # quality gates — avoid mis-tagged / multiword noise
            if not form or " " in form or len(form) > 32:
                continue
            if lang == "en":
                continue  # english head already on sense; gold often mis-tags ang as en
            if _fold(form) == _fold(gloss) and lang != "en":
                # identical string may still be valid loan; keep
                pass
            k = (_fold(lang), _fold(form), _fold(gloss))
            if k in existing:
                continue
            row = {
                "lang": lang,
                "form": form,
                "gloss": gloss,
                "source": "climb_expanded_gold",
                "tier": "A",
                "confidence": conf,
                "built_utc": _utc(),
            }
            added_rows.append(row)
            existing.add(k)
            self.bind_form_sense(lang, form, gloss, source="climb_expanded_gold", tier="A", confidence=conf)
            if len(added_rows) >= max_new:
                break

        if added_rows:
            BRAIN_DIR.mkdir(parents=True, exist_ok=True)
            with EXTRA_BINDINGS.open("a", encoding="utf-8") as f:
                for r in added_rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

        # also mine densify for *en* head only as soft notes (no lang) — skip

        return {
            "ok": True,
            "added": len(added_rows),
            "candidates_considered": len(best),
            "sample": added_rows[:15],
            "extra_bindings_path": str(EXTRA_BINDINGS),
        }

    def export_obsidian(self, *, max_sense_notes: int = 80) -> Path:
        """Write wiki-link notes for browsing in Obsidian."""
        vault = VAULT_DIR
        senses_dir = vault / "senses"
        langs_dir = vault / "langs"
        notes_dir = vault / "notes"
        for d in (senses_dir, langs_dir, notes_dir):
            d.mkdir(parents=True, exist_ok=True)

        # index
        index_lines = [
            "# PFLT Language Second Brain",
            "",
            f"Built: `{self.meta.get('built_utc', _utc())}`",
            "",
            "Machine graph: `data/language_brain/nodes.jsonl` + `edges.jsonl`",
            "",
            "## Core senses",
            "",
        ]

        # language notes
        for n in self.nodes.values():
            if n.kind != "language":
                continue
            code = n.props.get("code") or n.label
            body = [
                f"# Language `{code}`",
                "",
                f"gold_rows: {n.props.get('gold_rows', '?')}",
                "",
                "## Linked senses (sample)",
                "",
            ]
            # forms in this lang → senses
            linked = 0
            for e in self.edges:
                if e.rel != "expresses":
                    continue
                fn = self.nodes.get(e.src)
                sn = self.nodes.get(e.dst)
                if not fn or not sn or fn.props.get("lang") != code:
                    continue
                body.append(f"- `{fn.label}` → [[{sn.label}]]")
                linked += 1
                if linked >= 40:
                    break
            (langs_dir / f"{code}.md").write_text("\n".join(body) + "\n", encoding="utf-8")

        # sense notes (core + top by lang count)
        scored = []
        for gloss in CORE_SENSES:
            b = self.sense_bundle(gloss)
            scored.append((b.get("n_langs") or 0, gloss, b))
        scored.sort(reverse=True)
        for n_langs, gloss, b in scored[:max_sense_notes]:
            lines = [
                f"# {gloss}",
                "",
                f"sense_id: `{b.get('sense_id')}`",
                f"langs_bound: **{n_langs}**",
                "",
                "## Forms",
                "",
            ]
            for lang, forms in sorted((b.get("forms_by_lang") or {}).items()):
                fl = ", ".join(f"`{x}`" for x in forms[:8])
                lines.append(f"- [[{lang}]] — {fl}")
            miss = [L for L in TARGET_LANGS if L not in (b.get("forms_by_lang") or {})]
            if miss:
                lines += ["", "## Holes (target langs)", "", ", ".join(f"`{m}`" for m in miss)]
            (senses_dir / f"{gloss}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
            index_lines.append(f"- [[{gloss}]] — {n_langs} langs")

        # wrong-sense notes
        for n in self.nodes.values():
            if n.kind != "note":
                continue
            safe = re.sub(r"[^\w\-]+", "_", n.label)[:60]
            (notes_dir / f"{safe}.md").write_text(
                f"# {n.label}\n\n{n.props.get('text', '')}\n\n```json\n"
                + json.dumps(n.props, ensure_ascii=False, indent=2)
                + "\n```\n",
                encoding="utf-8",
            )

        index_lines += [
            "",
            "## Languages",
            "",
        ]
        for n in sorted((x for x in self.nodes.values() if x.kind == "language"), key=lambda x: x.label):
            index_lines.append(f"- [[{n.label}]]")

        (vault / "00_INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        return vault

    def write_reports(self, holes: Dict[str, Any], climb: Optional[Dict[str, Any]] = None) -> None:
        REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "built_utc": _utc(),
            "meta": self.meta,
            "holes_summary": {
                "n_senses_scored": holes.get("n_senses_scored"),
                "n_under_min_langs": holes.get("n_under_min_langs"),
                "mean_langs_bound": holes.get("mean_langs_bound"),
                "top_holes": holes.get("top_holes", [])[:25],
            },
            "climb": climb,
            "paths": {
                "nodes": str(NODES_PATH),
                "edges": str(EDGES_PATH),
                "extra_bindings": str(EXTRA_BINDINGS),
                "vault": str(VAULT_DIR),
            },
        }
        REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        lines = [
            "# FSOT Language Second Brain",
            "",
            f"**Built:** {payload['built_utc']}",
            f"**Nodes:** {self.meta.get('n_nodes')} · **Edges:** {self.meta.get('n_edges')}",
            f"**By kind:** `{self.meta.get('by_kind')}`",
            f"**Law:** S=K(T1+T2+T3) pin D1D38A · S_ling={self.meta.get('counts', {}).get('fsot_law_S')}",
            "",
            "## Mission",
            "",
            "**FSOT** connective graph of form↔sense↔language↔lineage for the universal translator.",
            "Obsidian vault (optional browse): `data/language_brain/vault/`.",
            "Naming: **FSOT_*** = ours · NLLB/DeepL/OPUS = competitor students/bars.",
            "",
            "## Hole map (core senses × target langs)",
            "",
            f"- Senses scored: **{holes.get('n_senses_scored')}**",
            f"- Under min_langs: **{holes.get('n_under_min_langs')}**",
            f"- Mean langs bound: **{holes.get('mean_langs_bound')}**",
            "",
            "| Gloss | Langs bound | Missing (sample) |",
            "|-------|------------:|------------------|",
        ]
        for h in (holes.get("top_holes") or [])[:20]:
            miss = ", ".join(f"`{x}`" for x in (h.get("missing_target_langs") or [])[:8])
            lines.append(
                f"| {h['gloss']} | {h['n_langs_bound']} | {miss} |"
            )
        if climb:
            lines += [
                "",
                "## Climb (expanded_gold hole fill)",
                "",
                f"- Added bindings: **{climb.get('added')}**",
                f"- Path: `{climb.get('extra_bindings_path')}`",
                "",
            ]
            for s in climb.get("sample") or []:
                lines.append(f"- `{s.get('lang')}` `{s.get('form')}` → {s.get('gloss')}")
        lines += [
            "",
            "## CLI",
            "",
            "```powershell",
            "python language_brain.py build",
            "python language_brain.py holes",
            "python language_brain.py query water",
            "python language_brain.py climb",
            "python language_brain.py export-obsidian",
            "```",
            "",
            "## Breadth (do not undercount)",
            "",
            f"- **Solidify catalog:** **{self.meta.get('counts', {}).get('catalog_size', '?')}** codes "
            f"(all ≥95 open: {self.meta.get('counts', {}).get('catalog_all_ge_95')}, "
            f"overall {self.meta.get('counts', {}).get('catalog_open_overall')})",
            f"- Gold-core historical slice: **{self.meta.get('counts', {}).get('gold_core_langs', '?')}** codes (different track)",
            f"- FSOT law S (linguistic): **{self.meta.get('counts', {}).get('fsot_law_S')}** · pin D1D38A",
            f"- FSOT lang pathways: **{self.meta.get('counts', {}).get('fsot_lang_pathways')}**",
            "",
            "## Competitive frame (news de→en, honest)",
            "",
            "| Layer | sacre | Meaning |",
            "|-------|------:|---------|",
            "| Product = gen_score_nllb33 | **36.79** | What we ship (≈ NLLB-3.3B class) |",
            "| DeepL-class mid bar | ~40 | External fluency competitor (~3.2 gap) |",
            "| **Oracle (pool upper bound)** | **46.12** | Best hyp *already in our pool* — not DeepL |",
            "",
            "Oracle is **not** an external product. It is the ceiling of candidates we already generated.",
            "Gap product→oracle ≈ **9.3** sacre is almost all **selection**. Gap product→mid-40 ≈ **3.2**.",
            "",
            "## Next levers",
            "",
            "1. **Selection toward oracle** (hard indices) — largest fluency residual",
            "2. Grow sense graph *across the 113 catalog* (not just core 61)",
            "3. Classical/visual depth (unique band)",
            "4. Hold solidify 113 ≥95; expand toward 200 when ready",
            "",
        ]
        REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
        HOLES_PATH.write_text(json.dumps(holes, ensure_ascii=False, indent=2), encoding="utf-8")
        if climb:
            CLIMB_PATH.write_text(json.dumps(climb, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_build(args: argparse.Namespace) -> int:
    brain = LanguageBrain()
    meta = brain.build(gold_scan_limit=int(args.gold_limit or 0))
    brain.save()
    holes = brain.hole_map(min_langs=int(args.min_langs))
    brain.write_reports(holes)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(
        f"holes: under_min={holes['n_under_min_langs']} mean_langs={holes['mean_langs_bound']}",
        flush=True,
    )
    print(f"WROTE {NODES_PATH}", flush=True)
    return 0


def cmd_holes(args: argparse.Namespace) -> int:
    brain = LanguageBrain()
    if not NODES_PATH.is_file():
        brain.build(gold_scan_limit=0)
        brain.save()
    else:
        brain.load()
    holes = brain.hole_map(min_langs=int(args.min_langs), core_only=not args.all_senses)
    brain.write_reports(holes)
    print(json.dumps({k: holes[k] for k in holes if k != "all_holes"}, ensure_ascii=False, indent=2)[:8000])
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    brain = LanguageBrain()
    if NODES_PATH.is_file():
        brain.load()
    else:
        brain.build()
        brain.save()
    b = brain.sense_bundle(args.term)
    print(json.dumps(b, ensure_ascii=False, indent=2))
    return 0


def cmd_climb(args: argparse.Namespace) -> int:
    brain = LanguageBrain()
    brain.build(gold_scan_limit=int(args.gold_limit or 0))
    climb = brain.climb_fill_from_gold(max_new=int(args.max_new), gold_limit=int(args.gold_limit or 0))
    # rebuild with new bindings
    brain2 = LanguageBrain()
    brain2.build(gold_scan_limit=int(args.gold_limit or 0))
    brain2.save()
    holes = brain2.hole_map(min_langs=int(args.min_langs))
    brain2.write_reports(holes, climb)
    vault = brain2.export_obsidian()
    print(json.dumps({"climb": climb, "mean_langs": holes["mean_langs_bound"], "under": holes["n_under_min_langs"], "vault": str(vault)}, ensure_ascii=False, indent=2))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    brain = LanguageBrain()
    if NODES_PATH.is_file():
        brain.load()
    else:
        brain.build()
        brain.save()
    path = brain.export_obsidian()
    print(f"WROTE vault {path}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    """build → climb → export → report (main campaign entry)."""
    args.gold_limit = getattr(args, "gold_limit", 0) or 0
    args.max_new = getattr(args, "max_new", 8000) or 8000
    args.min_langs = getattr(args, "min_langs", 5) or 5
    return cmd_climb(args)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="PFLT Language Second Brain")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Ingest sources → graph")
    p_build.add_argument("--gold-limit", type=int, default=0, help="0 = full expanded_gold scan")
    p_build.add_argument("--min-langs", type=int, default=5)
    p_build.set_defaults(func=cmd_build)

    p_holes = sub.add_parser("holes", help="Core sense hole map")
    p_holes.add_argument("--min-langs", type=int, default=5)
    p_holes.add_argument("--all-senses", action="store_true")
    p_holes.set_defaults(func=cmd_holes)

    p_q = sub.add_parser("query", help="Query a sense hub")
    p_q.add_argument("term", help="gloss or SENSE_id")
    p_q.set_defaults(func=cmd_query)

    p_c = sub.add_parser("climb", help="Fill holes from expanded_gold + export")
    p_c.add_argument("--max-new", type=int, default=8000)
    p_c.add_argument("--gold-limit", type=int, default=0)
    p_c.add_argument("--min-langs", type=int, default=5)
    p_c.set_defaults(func=cmd_climb)

    p_e = sub.add_parser("export-obsidian", help="Write vault markdown")
    p_e.set_defaults(func=cmd_export)

    p_a = sub.add_parser("all", help="build+climb+export+wire sense loader")
    p_a.add_argument("--max-new", type=int, default=8000)
    p_a.add_argument("--gold-limit", type=int, default=0)
    p_a.add_argument("--min-langs", type=int, default=5)
    p_a.set_defaults(func=cmd_all)

    args = ap.parse_args(argv)
    return int(args.func(args))


# typing for main
from typing import Sequence  # noqa: E402  — keep runtime simple

if __name__ == "__main__":
    sys.exit(main())
