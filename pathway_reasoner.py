#!/usr/bin/env python3
"""
Pathway reasoner for the Protofluid Language Translator.

Port of Realities OS cognition/pathway attention over an FSOT domain graph —
adapted to PFLT domain keys (DOMAIN_PARAMS / FSOT21_DOMAINS) so converse can
multi-hop without a live instrument visual_state dependency.

Optional: if Realities OS visual_state.live.json is present, node scalars
blend live instrument state; otherwise domain params drive the field.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --- Domain families (same geometry idea as Realities OS) -------------------
FAMILIES: Dict[str, List[str]] = {
    "universe": [
        "cosmological",
        "astronomy",
        "astrophysical",
        "astrophysics",
        "quantum",
        "nuclear",
        "particle_physics",
        "high_energy_physics",
        "quantum_gravity",
    ],
    "earth_weather": [
        "geological",
        "geophysics",
        "seismology",
        "meteorology",
        "atmospheric_physics",
        "oceanography",
        "planetary_science",
        "fluid_dynamics",
    ],
    "cellular": [
        "biological",
        "biology",
        "genomic",
        "biochemistry",
        "neural",
        "neuroscience",
        "metabolic",
        "ecological",
        "ecology",
    ],
    "mind_language": [
        "linguistic",
        "english",
        "consciousness",
        "psychology",
        "historical",
        "mythological",
        "fluid_tongue",
        "hieroglyphic",
    ],
    "matter_energy": [
        "material",
        "materials_science",
        "chemistry",
        "atomic",
        "atomic_physics",
        "thermodynamics",
        "electromagnetism",
        "optics",
        "acoustics",
        "condensed_matter",
    ],
}

# Query lexicon → domain mass (PFLT / FSOT keys, lower_snake)
LEXICON: Dict[str, Dict[str, float]] = {
    "universe": {"cosmological": 1.0, "astronomy": 0.6},
    "cosmos": {"cosmological": 1.0},
    "cosmology": {"cosmological": 1.2},
    "galaxy": {"astronomy": 1.0, "astrophysical": 0.8},
    "star": {"astronomy": 0.9, "astrophysical": 0.7},
    "quantum": {"quantum": 1.0},
    "photon": {"quantum": 0.8, "optics": 0.5},
    "nuclear": {"nuclear": 1.0},
    "atom": {"atomic": 1.0, "chemistry": 0.4},
    "gene": {"genomic": 1.0, "biological": 0.6},
    "dna": {"genomic": 1.0, "biological": 0.7},
    "cell": {"biological": 0.9, "biochemistry": 0.6},
    "life": {"biological": 1.0, "ecological": 0.5},
    "brain": {"neural": 1.2, "consciousness": 0.6},
    "mind": {"consciousness": 0.9, "neural": 0.7},
    "word": {"linguistic": 1.0, "english": 0.5},
    "language": {"linguistic": 1.2, "english": 0.6},
    "speech": {"linguistic": 1.0, "acoustics": 0.4},
    "name": {"linguistic": 0.7, "historical": 0.4},
    "write": {"linguistic": 0.8},
    "read": {"linguistic": 0.8},
    "zipf": {"linguistic": 1.2},
    "entropy": {"linguistic": 0.7, "quantum": 0.3},
    "phoneme": {"linguistic": 1.0},
    "syntax": {"linguistic": 1.0},
    "rome": {"historical": 1.0},
    "king": {"historical": 0.9},
    "war": {"historical": 0.8},
    "god": {"mythological": 1.0},
    "zeus": {"mythological": 1.1},
    "soul": {"mythological": 0.7, "consciousness": 0.5},
    "temple": {"mythological": 0.8, "historical": 0.5},
    "hand": {"historical": 0.7, "biological": 0.2},
    "hands": {"historical": 0.7, "biological": 0.2},
    # water alone: mild ocean; "latin/hands" overrides in route_domain
    "water": {"historical": 0.45, "oceanography": 0.35, "linguistic": 0.25, "chemistry": 0.2},
    "aqua": {"historical": 1.0, "linguistic": 0.5},
    "manus": {"historical": 1.0, "linguistic": 0.5},
    "lingua": {"linguistic": 1.1, "historical": 0.6},
    "latin": {"historical": 1.6, "linguistic": 1.1},
    "greek": {"linguistic": 1.2, "mythological": 0.9, "historical": 0.7},
    "roman": {"historical": 1.4},
    "rome": {"historical": 1.3},
    "classical": {"historical": 1.0, "linguistic": 0.8},
    "translate": {"linguistic": 1.3},
    "translation": {"linguistic": 1.2},
    "english": {"linguistic": 1.0, "english": 0.8},
    "zipf": {"linguistic": 1.4},
    "entropy": {"linguistic": 1.0, "quantum": 0.25},
    "exponent": {"linguistic": 0.6},
    "shannon": {"linguistic": 1.1},
    "temple": {"mythological": 1.1, "historical": 0.6},
    "divine": {"mythological": 1.0},
    "earth": {"geological": 0.9, "planetary_science": 0.6},
    "rock": {"geological": 1.0},
    "fluid": {"fluid_dynamics": 1.0, "fluid_tongue": 0.5},
    "energy": {"quantum": 0.5, "nuclear": 0.4, "thermodynamics": 0.5},
    "light": {"optics": 0.9, "electromagnetism": 0.6},
    "sound": {"acoustics": 1.0},
    "memory": {"neural": 0.9, "consciousness": 0.5},
    "formula": {"quantum": 0.3, "linguistic": 0.2},
    "law": {"historical": 0.5, "consciousness": 0.3},
    "observer": {"consciousness": 1.0, "quantum": 0.5},
    "translate": {"linguistic": 1.2},
    "knowledge": {"linguistic": 0.5, "consciousness": 0.4},
}

VISUAL_STATE_CANDIDATES = [
    Path(r"I:\FSOT-Physical-Archive\10_Realities-OS\data\runtime\visual_state.live.json"),
]


@dataclass
class PathwayNode:
    name: str
    scalar: float
    hits: float
    delta_psi: float
    family: str = "abstract"


@dataclass
class PathwayGraph:
    nodes: List[PathwayNode]
    adjacency: List[List[float]]
    scene_kind: str = "pflt_atlas"
    tick: int = 0

    def name_vector(self) -> List[str]:
        return [n.name for n in self.nodes]


@dataclass
class ReasonResult:
    query: str
    answer: str
    confidence: float
    hops: int
    top_domains: List[Dict[str, Any]]
    pathway_trace: List[Dict[str, Any]]
    tokens: List[str]
    engine: str = "pflt_pathway_attention_v0"
    elapsed_ms: float = 0.0
    live_visual: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _family_of(domain: str) -> str:
    for fam, members in FAMILIES.items():
        if domain in members:
            return fam
    return "abstract"


def _softmax(xs: List[float], temperature: float = 1.0) -> List[float]:
    t = max(temperature, 1e-6)
    m = max(xs) if xs else 0.0
    exps = [math.exp((x - m) / t) for x in xs]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _matvec(adj: List[List[float]], v: List[float]) -> List[float]:
    n = len(v)
    out = [0.0] * n
    for i in range(n):
        acc = 0.0
        row = adj[i]
        for j in range(n):
            acc += row[j] * v[j]
        out[i] = acc
    return out


def _l2_normalize(vec: List[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in re.findall(r"[a-zA-Z0-9_\u0370-\u03ff]+", text or "")]


def _load_live_scalars() -> Dict[str, float]:
    """Optional Realities OS visual_state scalars keyed loosely to domain names."""
    for path in VISUAL_STATE_CANDIDATES:
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            vs = raw.get("visual_state", raw)
            digest = vs.get("domain_digest") or vs.get("scalars") or vs.get("domains") or {}
            if isinstance(digest, dict):
                out: Dict[str, float] = {}
                for k, v in digest.items():
                    key = re.sub(r"[^a-z0-9]+", "_", str(k).lower()).strip("_")
                    try:
                        if isinstance(v, dict):
                            out[key] = float(v.get("S") or v.get("scalar") or 0)
                        else:
                            out[key] = float(v)
                    except (TypeError, ValueError):
                        continue
                if out:
                    return out
        except Exception:
            continue
    return {}


def build_pflt_graph(
    domain_params: Dict[str, Dict[str, Any]],
    fsot21: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    max_nodes: int = 80,
) -> PathwayGraph:
    """
    Build pathway graph from PFLT domain atlas.
    Prefer core / frequently used domains; pad from FSOT21.
    """
    fsot21 = fsot21 or {}
    live = _load_live_scalars()

    # Priority cores for language intelligence surface
    priority = [
        "linguistic",
        "historical",
        "mythological",
        "consciousness",
        "english",
        "quantum",
        "cosmological",
        "biological",
        "genomic",
        "neural",
        "geological",
        "nuclear",
        "atomic",
        "material",
        "ecological",
        "fluid_tongue",
        "acoustics",
        "astronomy",
        "astrophysical",
        "chemistry",
        "biochemistry",
        "psychology",
        "geophysics",
        "oceanography",
        "planetary_science",
        "electromagnetism",
        "thermodynamics",
        "optics",
        "fluid_dynamics",
        "neuroscience",
        "meteorology",
    ]
    names: List[str] = []
    for n in priority:
        if n in domain_params and n not in names:
            names.append(n)
    for n in sorted(domain_params.keys()):
        if len(names) >= max_nodes:
            break
        if n not in names:
            names.append(n)

    nodes: List[PathwayNode] = []
    for name in names:
        p = domain_params.get(name) or {}
        hits = 0.0
        if name in fsot21:
            hits = float(fsot21[name].get("recent_hits") or 0)
        # synthetic scalar from D_eff / delta_psi when no live S
        d_eff = float(p.get("D_eff", 12))
        dpsi = float(p.get("delta_psi", 0.8))
        base_s = math.tanh((d_eff - 12.5) / 8.0) * 0.4 + (dpsi - 0.8) * 0.2
        if name in live:
            base_s = 0.55 * live[name] + 0.45 * base_s
        # soft boost linguistic family for translator product
        if _family_of(name) == "mind_language":
            base_s += 0.05
        nodes.append(
            PathwayNode(
                name=name,
                scalar=float(base_s),
                hits=hits,
                delta_psi=dpsi,
                family=_family_of(name),
            )
        )

    n = len(nodes)
    adj = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w = 0.0
            if nodes[i].family == nodes[j].family and nodes[i].family != "abstract":
                w += 0.55
            # scalar alignment
            w += 0.25 * (1.0 - abs(nodes[i].scalar - nodes[j].scalar))
            # name stem soft link
            a, b = nodes[i].name, nodes[j].name
            if a.split("_")[0] == b.split("_")[0]:
                w += 0.2
            if w > 0.15:
                adj[i][j] = adj[j][i] = w

    # ensure connectivity: weak ring
    for i in range(n):
        j = (i + 1) % n
        adj[i][j] = max(adj[i][j], 0.08)
        adj[j][i] = max(adj[j][i], 0.08)

    return PathwayGraph(nodes=nodes, adjacency=adj, scene_kind="pflt_atlas", tick=0)


def project_query(tokens: Iterable[str], graph: PathwayGraph) -> List[float]:
    names = graph.name_vector()
    idx = {n: i for i, n in enumerate(names)}
    vec = [0.0] * len(names)
    tok_list = list(tokens)
    if not tok_list:
        for i, node in enumerate(graph.nodes):
            boost = 1.2 if node.family == "mind_language" else 1.0
            vec[i] = (0.15 + abs(node.scalar) * 0.1) * boost
        return _l2_normalize(vec)

    for tok in tok_list:
        if tok in idx:
            vec[idx[tok]] += 1.5
        if tok in LEXICON:
            for dom, w in LEXICON[tok].items():
                if dom in idx:
                    vec[idx[dom]] += w
        for dom, i in idx.items():
            stem = dom.split("_")[0]
            if len(tok) >= 4 and (tok in stem or stem in tok):
                vec[i] += 0.35
    if sum(abs(x) for x in vec) < 1e-9:
        # default language surface
        if "linguistic" in idx:
            vec[idx["linguistic"]] = 1.0
        else:
            vec[0] = 1.0
    return _l2_normalize(vec)


class PathwayReasoner:
    """Multi-hop attention over PFLT FSOT domain graph."""

    def __init__(
        self,
        domain_params: Optional[Dict[str, Dict[str, Any]]] = None,
        fsot21: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        if domain_params is None:
            from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, FSOT21_DOMAINS

            domain_params = DOMAIN_PARAMS
            fsot21 = FSOT21_DOMAINS
        self.graph = build_pflt_graph(domain_params, fsot21)
        self.live_visual = bool(_load_live_scalars())

    def reason(self, query: str, *, hops: int = 4, temperature: float = 0.85) -> ReasonResult:
        t0 = time.perf_counter()
        g = self.graph
        tokens = tokenize(query)
        q = project_query(tokens, g)

        values = [0.5 + 0.5 * math.tanh(n.scalar) for n in g.nodes]
        h = [0.65 * q[i] + 0.35 * values[i] * q[i] for i in range(len(q))]
        h = _softmax([x * 3.0 for x in h], temperature=temperature)

        trace: List[Dict[str, Any]] = []
        for hop in range(max(1, hops)):
            messages = _matvec(g.adjacency, h)
            deg = [sum(g.adjacency[i]) or 1.0 for i in range(len(h))]
            messages = [messages[i] / math.sqrt(deg[i]) for i in range(len(h))]
            gated = [
                0.55 * messages[i] + 0.45 * q[i] * (1.0 + abs(g.nodes[i].scalar))
                for i in range(len(h))
            ]
            mixed = [0.4 * h[i] + 0.6 * gated[i] for i in range(len(h))]
            h = _softmax([x * 2.5 for x in mixed], temperature=temperature)
            ranked = sorted(
                ((g.nodes[i].name, h[i]) for i in range(len(h))),
                key=lambda t: -t[1],
            )[:5]
            trace.append(
                {
                    "hop": hop + 1,
                    "top": [{"domain": d, "p": round(p, 4)} for d, p in ranked],
                }
            )

        ranked_final = sorted(
            (
                {
                    "domain": g.nodes[i].name,
                    "p": h[i],
                    "scalar": g.nodes[i].scalar,
                    "family": g.nodes[i].family,
                    "hits": g.nodes[i].hits,
                    "delta_psi": g.nodes[i].delta_psi,
                }
                for i in range(len(h))
            ),
            key=lambda d: -d["p"],
        )
        top = ranked_final[:8]
        # Confidence is relative (large graphs make raw softmax tops tiny).
        peak = float(top[0]["p"]) if top else 0.0
        second = float(top[1]["p"]) if len(top) > 1 else peak * 0.5
        margin = peak / (peak + second + 1e-12)
        ent = -sum(p * math.log(p + 1e-12) for p in h)
        max_ent = math.log(max(len(h), 2))
        concentration = max(0.0, 1.0 - (ent / max_ent))
        conf = float(max(0.05, min(0.98, 0.45 * margin + 0.55 * concentration)))

        answer = self._decode(query, tokens, top, conf)
        elapsed = (time.perf_counter() - t0) * 1000.0
        return ReasonResult(
            query=query,
            answer=answer,
            confidence=round(conf, 4),
            hops=hops,
            top_domains=[{**d, "p": round(float(d["p"]), 4)} for d in top],
            pathway_trace=trace,
            tokens=tokens,
            elapsed_ms=round(elapsed, 2),
            live_visual=self.live_visual,
            raw={"n_nodes": len(g.nodes), "scene_kind": g.scene_kind},
        )

    def _decode(
        self,
        query: str,
        tokens: List[str],
        top: List[Dict[str, Any]],
        conf: float,
    ) -> str:
        if not top:
            return "No pathway activation on PFLT domain atlas."
        d0 = top[0]["domain"]
        d1 = top[1]["domain"] if len(top) > 1 else d0
        d2 = top[2]["domain"] if len(top) > 2 else d1
        fam0 = top[0]["family"]
        path = " → ".join(dict.fromkeys([d0, d1, d2]))  # unique order-preserving
        return (
            f"Pathway attention (conf={conf:.2f}, family={fam0}): "
            f"{path}. Query energy on tokens={tokens[:8]}."
        )

    def primary_domain(self, query: str, fallback: str = "linguistic") -> Tuple[str, ReasonResult]:
        rr = self.reason(query, hops=3)
        if rr.top_domains:
            return str(rr.top_domains[0]["domain"]), rr
        return fallback, rr


# lazy singleton
_REASONER: Optional[PathwayReasoner] = None


def get_reasoner() -> PathwayReasoner:
    global _REASONER
    if _REASONER is None:
        _REASONER = PathwayReasoner()
    return _REASONER


if __name__ == "__main__":
    r = get_reasoner()
    for q in [
        "aqua lingua manus",
        "zipf law entropy of english words",
        "quantum photon energy",
        "zeus temple myth",
    ]:
        out = r.reason(q)
        print(q, "=>", out.answer)
        print("  top:", [(d["domain"], d["p"]) for d in out.top_domains[:4]])
