#!/usr/bin/env python3
"""
Domain-context awareness for symbols shared across domains.

Problem: the same surface form means different things by domain
  s8   → structure growth (cosmology) vs Gardiner S8 (hieroglyph)
  A1   → Gardiner seated man vs atomic shell 1s... vs generic id
  H2   → deuterium fuel (nuclear) vs plain H2 string
  me   → Sumerian divine decree vs English pronoun (classical)

Policy:
  1) Explicit domain registry wins for that context
  2) Glyph catalog only in glyph contexts (handled in PFLT)
  3) Shared keys list is auditable — never silent overwrite
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

# context -> token_lower -> meaning
DOMAIN_SYMBOLS: Dict[str, Dict[str, str]] = {
    "cosmological": {
        "s8": "0.811_structure_growth",
        "hubbk": "71.98_km_s_Mpc",
        "h0": "71.98_km_s_Mpc",
        "kappa": "dark_energy_scale",
        "lambda": "potential",
    },
    "nuclear": {
        "h2": "deuterium_fuel",
        "h3": "tritium_fuel",
        "he4": "helium_product",
        "d-t": "fusion_energy_17.6MeV",
        "u235": "fission_fuel",
    },
    "atomic": {
        "h2o": "water_matrix_hydrogen_bond",
        "co2": "carbon_cycle",
        "1s2": "core_stability",
        "2p2": "valence_activity",
        "3d5": "transition_activity",
    },
    "genomic": {
        "atg": "start",
        "gtg": "transfer",
        "cac": "energy",
        "ctg": "structure",
        "act": "action",
        "taa": "stop",
        "aug": "start_rna",
        "uaa": "stop_rna",
    },
    "biological": {
        "atg": "start",
        "gtg": "transfer",
        "cac": "energy",
        "ctg": "structure",
        "act": "action",
        "taa": "stop",
    },
    "mythological": {
        "an": "sky_domain",
        "ki": "earth_base",
        "ud": "primordial_time",
        "me": "divine_decree",
        "a-a": "water",
        "lugal": "king",
    },
    "administrative": {
        "da": "transfer",
        "ka": "to",
        "se": "source",
        "pa": "goods",
        "ki-nu": "count",
    },
    "historical": {
        "aqua": "water",
        "lingua": "language",
        "ius": "law",
        "me": "divine_decree",  # if Sumerian; classical me handled by lexicon first
    },
    "hieroglyphic": {
        # bare forms that also exist elsewhere — force glyph reading here
        "s8": "logogram_atef_crown",  # only when context is hieroglyphic
        "a1": "classifier_human_being",
        "n5": "logogram_the_sun_re",
        "s34": "logogram_life_ankh",
    },
    "egyptian": {
        "s8": "logogram_atef_crown",
        "a1": "classifier_human_being",
        "n5": "logogram_the_sun_re",
        "s34": "logogram_life_ankh",
    },
}

# Tokens known to be ambiguous (for logging / tests)
SHARED_SURFACE_FORMS = sorted(
    {
        t
        for ctx_map in DOMAIN_SYMBOLS.values()
        for t in ctx_map
    }
)


def resolve_domain_symbol(token: str, context: str) -> Optional[Tuple[str, str]]:
    """
    Return (meaning, source_tag) if domain registry has an entry.
    source_tag is 'domain_registry:<context>'.
    """
    key = token.lower().strip()
    ctx_map = DOMAIN_SYMBOLS.get(context)
    if not ctx_map:
        return None
    if key in ctx_map:
        return ctx_map[key], f"domain_registry:{context}"
    return None
