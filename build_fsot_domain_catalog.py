#!/usr/bin/env python3
"""
Import FSOT 2.1 domain atlas (403 scientific domains) into PFLT routing.

Sources (physical archive):
  - data/publication/domain_atlas.json  (402 listed + summary 403 covered)
  - data/fsot_domain_scalar_fixtures.json  (35 core with D_eff, delta_psi, observed)

Policy:
  - Core domains: exact fixture params (authoritative)
  - Extension domains: inherit from nearest core via keyword/lean_domain map;
    residual use seed-stable D_eff from domain name (phi-fold of 4..25), never free-fit
  - Every domain becomes a valid PFLT context for scalar modulation
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARCHIVE = Path(r"I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\data")
ATLAS = ARCHIVE / "publication" / "domain_atlas.json"
FIXTURES = ARCHIVE / "fsot_domain_scalar_fixtures.json"
OUT_PFLT = Path(r"C:\Users\damia\Desktop\pflt\data")
OUT_DRIVE = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot")

# Keyword → core fixture name (lowercase match on domain slug)
# Match against actual fixture core names (35)
KEYWORD_CORE: List[Tuple[str, str]] = [
    ("acoustic", "Acoustics"),
    ("astronom", "Astronomy"),
    ("astrophys", "Astrophysics"),
    ("atmospher", "Atmospheric_Physics"),
    ("meteor", "Meteorology"),
    ("atomic", "Atomic_Physics"),
    ("biochem", "Biochemistry"),
    ("biolog", "Biology"),
    ("brain", "Neuroscience"),
    ("neuro", "Neuroscience"),
    ("psych", "Psychology"),
    ("conscious", "Psychology"),
    ("chem", "Chemistry"),
    ("molecular_chem", "Molecular_Chemistry"),
    ("physical_chem", "Physical_Chemistry"),
    ("cosmo", "Cosmology"),
    ("dna", "Biology"),
    ("genom", "Biology"),
    ("gene", "Biology"),
    ("protein", "Biochemistry"),
    ("cell", "Biology"),
    ("ecolog", "Ecology"),
    ("electromagn", "Electromagnetism"),
    ("electron", "Atomic_Physics"),
    ("energy", "Thermodynamics"),
    ("fuel", "Thermodynamics"),
    ("fluid", "Fluid_Dynamics"),
    ("galaxy", "Astronomy"),
    ("galactic", "Astronomy"),
    ("geo", "Geophysics"),
    ("seism", "Seismology"),
    ("grav", "Quantum_Gravity"),
    ("higgs", "Particle_Physics"),
    ("high_energy", "High_Energy_Physics"),
    ("lingu", "Psychology"),  # nearest cognitive core until linguistics fixture
    ("language", "Psychology"),
    ("material", "Materials_Science"),
    ("medic", "Biology"),
    ("nuclear", "Nuclear_Physics"),
    ("ocean", "Oceanography"),
    ("optic", "Optics"),
    ("quantum_opt", "Quantum_Optics"),
    ("quantum_comp", "Quantum_Computing"),
    ("quantum_grav", "Quantum_Gravity"),
    ("quantum", "Quantum_Mechanics"),
    ("particle_astro", "Particle_Astrophysics"),
    ("particle", "Particle_Physics"),
    ("planetary", "Planetary_Science"),
    ("plasma", "Astrophysics"),
    ("condens", "Condensed_Matter"),
    ("solid", "Condensed_Matter"),
    ("thermo", "Thermodynamics"),
    ("ai", "Quantum_Computing"),
    ("machine", "Quantum_Computing"),
    ("cyber", "Quantum_Computing"),
    ("blackhole", "Astrophysics"),
    ("black_hole", "Astrophysics"),
    ("cmb", "Cosmology"),
    ("climate", "Atmospheric_Physics"),
    ("weather", "Meteorology"),
    ("actuar", "Economics"),
    ("econ", "Economics"),
    ("finance", "Economics"),
    ("socio", "Sociology"),
    ("radar", "Electromagnetism"),
    ("radio", "Electromagnetism"),
    ("mineral", "Materials_Science"),
    ("crystal", "Condensed_Matter"),
]


def slug(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def seed_deff(name: str) -> float:
    """Deterministic D_eff in [6, 24] from name using phi-fold (no free params)."""
    phi = 1.618033988749895
    h = 0.0
    for i, ch in enumerate(name.lower()):
        h = (h + (ord(ch) + 1) * (phi ** ((i % 7) + 1))) % 1000.0
    # map to 6..24
    return round(6.0 + (h / 1000.0) * 18.0, 2)


def load_fixtures() -> Dict[str, Dict[str, Any]]:
    raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out = {}
    for d in raw["domains"]:
        name = d["name"]
        out[name] = {
            "D_eff": float(d["d_eff"]),
            "recent_hits": int(d.get("hits") or 0),
            "delta_psi": float(d.get("delta_psi") or 1.0),
            "delta_theta": float(d.get("delta_theta") or 1.0),
            "observed": bool(d.get("observed")),
            "python_scalar": d.get("python_scalar"),
            "kind": "core",
            "source": "fsot_domain_scalar_fixtures",
        }
        out[slug(name)] = out[name]
    return out


def nearest_core(domain: str, fixtures: Dict[str, Dict[str, Any]]) -> Optional[str]:
    s = domain.lower()
    for kw, core in KEYWORD_CORE:
        if kw in s and core in fixtures:
            return core
        if kw in s and slug(core) in fixtures:
            return core
    return None


def main() -> None:
    atlas = json.loads(ATLAS.read_text(encoding="utf-8"))
    fixtures = load_fixtures()
    catalog: Dict[str, Dict[str, Any]] = {}

    # Always include fixtures cores
    for name, params in list(fixtures.items()):
        if "_" in name and name == slug(name):
            continue  # skip duplicate slug keys for listing; keep both in catalog
        catalog[slug(name)] = {
            **params,
            "domain": name,
            "display": name,
        }

    # Atlas domains (core + extension)
    for row in atlas["domains"]:
        dom = row["domain"]
        key = slug(dom)
        if key in catalog and catalog[key].get("kind") == "core":
            # enrich core with atlas meta
            catalog[key]["record_count"] = row.get("record_count")
            catalog[key]["median_error_pct"] = row.get("median_error_pct")
            catalog[key]["coverage_tier"] = row.get("coverage_tier")
            catalog[key]["atlas_kind"] = row.get("kind")
            continue

        parent = nearest_core(dom, fixtures)
        lean = (row.get("lean_domain") or "").strip()
        if parent and parent in fixtures:
            base = dict(fixtures[parent])
        elif lean and lean in fixtures:
            base = dict(fixtures[lean])
            parent = lean
        elif lean and slug(lean) in fixtures:
            base = dict(fixtures[slug(lean)])
            parent = lean
        else:
            base = {
                "D_eff": seed_deff(dom),
                "recent_hits": 0,
                "delta_psi": 0.7,
                "delta_theta": 1.0,
                "observed": True,
                "kind": "extension",
                "source": "seed_stable_deff",
            }
            parent = None

        catalog[key] = {
            "domain": dom,
            "display": dom,
            "D_eff": float(base["D_eff"]),
            "recent_hits": int(base.get("recent_hits") or 0),
            "delta_psi": float(base.get("delta_psi") or 0.7),
            "delta_theta": float(base.get("delta_theta") or 1.0),
            "observed": bool(base.get("observed", True)),
            "kind": row.get("kind") or "extension",
            "parent_core": parent,
            "lean_domain": lean or None,
            "lean_module": row.get("lean_module") or None,
            "record_count": row.get("record_count"),
            "median_error_pct": row.get("median_error_pct"),
            "coverage_tier": row.get("coverage_tier"),
            "source": "domain_atlas+fixture_inherit" if parent else "domain_atlas+seed_deff",
        }

    # Also register common PFLT aliases pointing at cores
    aliases = {
        "cosmological": "cosmology",
        "astrophysical": "astrophysics",
        "geological": "geophysics",
        "biological": "biology",
        "genomic": "genomics",
        "neural": "neuroscience",
        "ecological": "ecology",
        "quantum": "quantum_mechanics",
        "nuclear": "nuclear_physics",
        "atomic": "atomic_physics",
        "material": "materials_science",
        "linguistic": "linguistics",
        "hieroglyphic": "linguistics",
        "historical": "linguistics",
        "mythological": "consciousness",
        "paranormal": "consciousness",
        "fluid_tongue": "fluid_dynamics",
        "english": "linguistics",
    }
    for a, target in aliases.items():
        if target in catalog and a not in catalog:
            catalog[a] = {
                **catalog[target],
                "domain": a,
                "display": f"{a} (alias→{target})",
                "alias_of": target,
                "kind": "alias",
            }

    OUT_PFLT.mkdir(parents=True, exist_ok=True)
    OUT_DRIVE.mkdir(parents=True, exist_ok=True)
    payload = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "atlas_domain_count": atlas.get("domain_count"),
        "summary_total_scientific_domains": atlas.get("summary", {}).get(
            "total_scientific_domains_covered"
        ),
        "fixture_cores": 35,
        "catalog_keys": len(catalog),
        "unique_domains": len(
            {v.get("domain") for v in catalog.values() if v.get("kind") != "alias"}
        ),
        "domains": catalog,
    }
    for path in (
        OUT_PFLT / "fsot_domain_catalog.json",
        OUT_DRIVE / "fsot_domain_catalog.json",
    ):
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("wrote", path, "keys", len(catalog))

    # compact list for docs
    names = sorted(
        {
            v["domain"]
            for v in catalog.values()
            if v.get("kind") in {"core", "extension"} or v.get("atlas_kind")
        }
    )
    (OUT_PFLT / "fsot_domain_names.txt").write_text("\n".join(names), encoding="utf-8")
    print(
        f"unique scientific domains registered: {payload['unique_domains']} "
        f"(atlas {payload['atlas_domain_count']}, summary {payload['summary_total_scientific_domains']})"
    )


if __name__ == "__main__":
    main()
