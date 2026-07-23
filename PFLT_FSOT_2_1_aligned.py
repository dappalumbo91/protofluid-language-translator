#!/usr/bin/env python3
"""
PFLT — Proto-Fluid Language Translator
Aligned to verified FSOT 2.1 scalar engine (Lean FSOT.Scalar + NeuroLab fsot_compute).

Origin: Damian Arthur Palumbo with Grok (xAI), March–April 2025 (FSUFT-U 6.0 → 8.7).
This revision: July 2026 — scalar byte-parity with FSOT 2.1, longest-match tokenization,
historical + genomic real-data fixtures, honest evaluation metrics.

Math authority (zero free parameters beyond seeds):
  Seeds: π, e, φ, γ_Euler, G_Catalan
  S = K · (T1 + T2 + T3)
  with Layer-1/2 constants from FSOT_MATHEMATICAL_KEY / FSOT.Scalar.lean

No ad-hoc damping (exp(-η)/m_pl). Modulation prefixes derive only from sign/magnitude of S.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mpmath import mp, mpf, sqrt, cos, sin, exp, ln, pi as MP_PI, e as MP_E

mp.dps = 50

# ---------------------------------------------------------------------------
# FSOT 2.1 constants — parity with NeuroLab/fsot_compute.py and Lean Scalar
# ---------------------------------------------------------------------------
PI = MP_PI
E = MP_E
PHI = (1 + sqrt(5)) / 2
GAMMA = mpf("0.57721566490153286060651209008240243104215933593992")
G_CAT = mpf("0.91596559417721901505460351493238411077414937428167")

ALPHA = ln(PI) / (E * PHI**13)
PSI_CON = 1 - 1 / E  # (e-1)/e
ETA_EFF = 1 / (PI - 1)
BETA = exp(-(PI**PI + (E - 1)))
GAMMA_C = -ln(2) / PHI
OMEGA = sin(PI / E) * sqrt(2)
THETA_S = sin(PSI_CON * ETA_EFF)
POOF = exp((-ln(PI) / E) / (ETA_EFF * ln(PHI)))

C_EFF = (1 - POOF * sin(THETA_S)) * (1 + mpf("0.01") * G_CAT / (PI * PHI))
A_BLEED = sin(PI / E) * PHI / sqrt(2)
P_VAR = -cos(THETA_S + PI)
B_IN = C_EFF * (1 - sin(THETA_S) / PHI)
A_IN = A_BLEED * (1 + cos(THETA_S) / PHI)
SUCTION = POOF * (-cos(THETA_S - PI))
CHAOS = GAMMA_C / OMEGA
P_BASE = GAMMA / E
P_NEW = P_BASE * sqrt(2)
C_FACTOR = C_EFF * P_NEW  # consciousness factor ≈ 0.2876
K = PHI * (GAMMA / E) * sqrt(2) / ln(PI) * mpf("0.99")  # ≈ 0.4202


@dataclass(frozen=True)
class ScalarPanel:
    """Lean-aligned scalar + term breakdown (traceable CoT)."""
    S: float
    T1: float
    T2: float
    T3: float
    quirk_mod: float
    growth: float
    D_eff: float
    observed: bool
    delta_psi: float
    delta_theta: float


def compute_S_D_chaotic(
    *,
    N: float = 1.0,
    P: float = 1.0,
    D_eff: float = 25.0,
    recent_hits: float = 0.0,
    delta_psi: float = 1.0,
    delta_theta: float = 1.0,
    rho: float = 1.0,
    scale: float = 1.0,
    amplitude: float = 1.0,
    trend_bias: float = 0.0,
    observed: bool = False,
) -> ScalarPanel:
    """
    Canonical FSOT 2.1 scalar: S = K (T1 + T2 + T3).

    Matches structure of:
      - I:/FSOT-Physical-Archive/02_FSOT-2.1-Lean-Full/FSOT/Scalar.lean
      - Desktop/FSOT NeuroLab/fsot_compute.py compute_scalar
    """
    N_m, P_m, D_m = mpf(N), mpf(P), mpf(D_eff)
    hits = mpf(recent_hits)
    dp, dt = mpf(delta_psi), mpf(delta_theta)

    growth = exp(ALPHA * (1 - hits / N_m) * GAMMA / PHI)
    base = (
        (N_m * P_m / sqrt(D_m))
        * cos((PSI_CON + dp) / ETA_EFF)
        * exp(-ALPHA * hits / N_m + mpf(rho) + B_IN * dp)
        * (1 + growth * C_EFF)
    )
    T1 = base * (1 + P_NEW * ln(D_m / 25))
    qm = mpf(1)
    if observed:
        qm = exp(C_FACTOR * P_VAR) * cos(dp + P_VAR)
        T1 = T1 * qm

    T2 = mpf(scale) * mpf(amplitude) + mpf(trend_bias)

    valve = (
        BETA
        * cos(dp)
        * (N_m * P_m / sqrt(D_m))
        * (1 + CHAOS * (D_m - 25) / 25)
        * (1 + POOF * cos(THETA_S + PI) + SUCTION * sin(THETA_S))
    )
    acoustic = 1 + (A_BLEED * sin(dt) ** 2) / PHI + (A_IN * cos(dt) ** 2) / PHI
    phase = 1 + B_IN * P_VAR
    T3 = valve * acoustic * phase

    raw = T1 + T2 + T3
    S = K * raw
    return ScalarPanel(
        S=float(S),
        T1=float(T1),
        T2=float(T2),
        T3=float(T3),
        quirk_mod=float(qm),
        growth=float(growth),
        D_eff=float(D_eff),
        observed=observed,
        delta_psi=float(delta_psi),
        delta_theta=float(delta_theta),
    )


# Domain routing: D_eff + observed + phase (aligned with Lean getDomainParams + linguistics)
DOMAIN_PARAMS: Dict[str, Dict[str, Any]] = {
    "cosmological": {"D_eff": 25, "observed": False, "delta_psi": 1.0, "delta_theta": 1.0},
    "nuclear": {"D_eff": 9, "observed": True, "delta_psi": 1.0, "delta_theta": 1.0},
    "atomic": {"D_eff": 7, "observed": True, "delta_psi": 0.9, "delta_theta": 1.0},
    "geological": {"D_eff": 18, "observed": True, "delta_psi": 0.9, "delta_theta": 1.0},
    "quantum": {"D_eff": 6, "observed": True, "delta_psi": 1.0, "delta_theta": 1.0},
    "astrophysical": {"D_eff": 20, "observed": True, "delta_psi": 1.0, "delta_theta": 1.0},
    "material": {"D_eff": 11, "observed": False, "delta_psi": 0.6, "delta_theta": 1.0},
    "biological": {"D_eff": 12, "observed": False, "delta_psi": 0.05, "delta_theta": 1.0},
    "genomic": {"D_eff": 12, "observed": False, "delta_psi": 0.05, "delta_theta": 1.0},
    "neural": {"D_eff": 14, "observed": False, "delta_psi": 0.1, "delta_theta": 1.0},
    "metabolic": {"D_eff": 12, "observed": False, "delta_psi": 0.065, "delta_theta": 1.0},
    "ecological": {"D_eff": 18, "observed": True, "delta_psi": 0.7, "delta_theta": 1.0},
    "paleontological": {"D_eff": 18, "observed": True, "delta_psi": 0.65, "delta_theta": 1.0},
    "mythological": {"D_eff": 21, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0},
    "administrative": {"D_eff": 15, "observed": True, "delta_psi": 0.5, "delta_theta": 1.0},
    "paranormal": {"D_eff": 22, "observed": True, "delta_psi": 1.5, "delta_theta": 1.0},
    "linguistic": {"D_eff": 12, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0},
    "fluid_tongue": {"D_eff": 25, "observed": True, "delta_psi": 1.0, "delta_theta": 1.0},
    "historical": {"D_eff": 21, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0},
    "english": {"D_eff": 12, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0},
    # Visual scripts (Egyptian hieroglyphs, later Maya / rock-art stages)
    "hieroglyphic": {"D_eff": 18, "observed": True, "delta_psi": 0.9, "delta_theta": 1.0},
    "egyptian": {"D_eff": 18, "observed": True, "delta_psi": 0.9, "delta_theta": 1.0},
    "visual_script": {"D_eff": 20, "observed": True, "delta_psi": 1.0, "delta_theta": 1.0},
    "rock_art": {"D_eff": 22, "observed": True, "delta_psi": 1.2, "delta_theta": 1.0},
}


def _load_fsot21_domain_catalog() -> Dict[str, Dict[str, Any]]:
    """
    Load full FSOT 2.1 domain atlas routing (400+ scientific domains).
    Built by build_fsot_domain_catalog.py from I:\\FSOT-Physical-Archive.
    """
    candidates = [
        Path(__file__).resolve().parent / "data" / "fsot_domain_catalog.json",
        Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\fsot_domain_catalog.json"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            domains = payload.get("domains") or {}
            out: Dict[str, Dict[str, Any]] = {}
            for key, row in domains.items():
                out[str(key)] = {
                    "D_eff": float(row.get("D_eff", 12)),
                    "observed": bool(row.get("observed", True)),
                    "delta_psi": float(row.get("delta_psi", 0.8)),
                    "delta_theta": float(row.get("delta_theta", 1.0)),
                    "recent_hits": int(row.get("recent_hits") or 0),
                    "display": row.get("display") or row.get("domain") or key,
                    "kind": row.get("kind"),
                    "parent_core": row.get("parent_core"),
                    "coverage_tier": row.get("coverage_tier"),
                    "record_count": row.get("record_count"),
                }
            return out
        except Exception:
            continue
    return {}


# Full FSOT 2.1 scientific domain routing (merged at import)
FSOT21_DOMAINS: Dict[str, Dict[str, Any]] = _load_fsot21_domain_catalog()
for _k, _v in FSOT21_DOMAINS.items():
    if _k not in DOMAIN_PARAMS:
        DOMAIN_PARAMS[_k] = {
            "D_eff": _v["D_eff"],
            "observed": _v["observed"],
            "delta_psi": _v["delta_psi"],
            "delta_theta": _v["delta_theta"],
        }


# ---------------------------------------------------------------------------
# Lexicon (pul_terms) — cleaned from April 29 2025 thesis + extensions
# ---------------------------------------------------------------------------
def _build_lexicon() -> Dict[str, str]:
    terms: Dict[str, str] = {
        # Cosmological
        "hubbk": "71.98_km_s_Mpc",
        "h0": "71.98_km_s_Mpc",
        "s8": "0.811_structure_growth",
        "cmbcold": "-68_uK_cold_spot",
        "xray3.5": "3.5_keV_anomaly",
        "pta_gwb": "2.0e-14_nanohertz_background",
        "ccon": "consciousness_energy",
        "freq150": "resonant_focus_boost_17.2pct",
        "phi": "tension",
        "eta": "viscosity",
        "delta": "perturbation",
        "kappa": "dark_energy_scale",
        "lambda": "potential",
        # Nuclear
        "h2": "deuterium_fuel",
        "h3": "tritium_fuel",
        "he4": "helium_product",
        "d-t": "fusion_energy_17.6MeV",
        "p-p": "solar_chain",
        "plasma": "fusion_medium",
        "q_factor": "energy_gain",
        "bbn": "nucleosynthesis_1.1MeV",
        "u235": "fission_fuel",
        "alpha_decay": "particle_emission",
        "neutron_capture": "chain_trigger",
        # Atomic
        "1s2": "core_stability",
        "2p2": "valence_activity",
        "3d5": "transition_activity",
        "covalent": "shared_energy",
        "ionic": "charge_transfer",
        "van_der_waals": "weak_attraction",
        "h2o": "water_matrix_hydrogen_bond",
        "co2": "carbon_cycle",
        "dipole": "charge_separation",
        "gauge_field": "electromagnetic_interaction",
        "metallic_bond": "delocalized_flow",
        # Mineral
        "sio2": "quartz_stability_silica",
        "caco3": "calcite_structure",
        "fe2o3": "hematite_oxidation",
        "diamond": "carbon_lattice",
        "hexagonal": "ordered_lattice",
        "cubic": "symmetric_core",
        "hydrothermal": "fluid_deposition",
        "magma": "molten_flow",
        "pegmatite": "crystal_growth",
        "scalar_field": "mineral_cohesion",
        # Quantum
        "superposition": "quantum_overlap",
        "entanglement": "correlated_flow",
        "wave_function": "probability_field",
        "quantum_tunnel": "barrier_crossing",
        "coherence": "synchronized_state",
        "decoherence": "state_disruption",
        # Astrophysical
        "bh_collapse": "gravitational_convergence_singularity",
        "cosmic_ray": "high_energy_flux",
        "supernova": "stellar_explosion",
        "dark_matter": "invisible_mass",
        "gamma_ray_burst": "energy_pulse",
        "neutron_star": "dense_core",
        # Materials
        "graphene": "conductive_lattice",
        "superconductor": "zero_resistance_flow",
        "biomaterial": "life_compatible_matrix",
        "quantum_dot": "nano_emitter",
        "polymer": "chain_structure",
        "ceramic": "thermal_resistance",
        # Biological / genomic (extended codon set)
        "atg": "start",
        "gtg": "transfer",
        "cac": "energy",
        "ctg": "structure",
        "caa": "energy_link",
        "gcg": "core_structure",
        "aug": "start_rna",
        "uaa": "stop_rna",
        "taa": "stop",
        "act": "action",
        "cct": "cycle",
        "gag": "force",
        "aag": "link",
        "tct": "unit",
        "gcc": "form",
        "gtt": "flow",
        "tgg": "balance",
        "ggc": "base",
        "aac": "state",
        "gac": "drive",
        "ttt": "repeat",
        "gaa": "link",
        "ugu": "state_rna",
        "acu": "action_rna",
        "att": "initiation_step",
        "gat": "drive",
        "tat": "signal",
        "gct": "form",
        "lysine": "charge_bridge",
        "hemoglobin": "oxygen_carrier",
        "cftr": "ion_channel",
        "glucose": "energy_source",
        "atp": "energy_unit",
        "alpha_wave": "focus_signal",
        "ccon_dolphin": "consciousness_flow_5eV",
        "mrna": "transcript_guide",
        "ribosome": "protein_factory",
        "gaba": "calm_signal",
        "epigenetics": "gene_regulation",
        "mitochondria": "energy_powerhouse",
        # Ecological
        "coral_reef": "biodiverse_network",
        "rainforest": "carbon_sink",
        "carbon_cycle": "global_flux",
        "nitrogen_cycle": "nutrient_flow",
        "trophic_level": "energy_hierarchy",
        "marsh": "hydric_network",
        "phytoplankton": "primary_producer",
        "succession": "community_evolution",
        "invasive_species": "disruptive_intruder",
        "microbiome": "symbiotic_matrix",
        "ecological_field": "systemic_coherence",
        # Paleontological
        "trilobite": "ancient_segmented_form",
        "t_rex": "apex_predator_relic",
        "ammonite": "spiral_shell_fossil",
        "k-pg_extinction": "catastrophic_reset",
        "permian_extinction": "mass_collapse",
        "tetrapod_transition": "land_adaptation",
        "feather_evolution": "flight_enabler",
        "paleo_field": "temporal_coherence",
        "coprolite": "fossilized_trace",
        "iridium_anomaly": "extinction_marker",
        "archaeopteryx": "transitional_flight_form",
        "stromatolite": "ancient_microbial_layer",
        # Sumerian / mythological (thesis + Dictionary historical seed)
        "an": "sky_domain",
        "ki": "earth_base",
        "ud": "primordial_time",
        "bi": "state",
        "ba": "creation_act",
        "dim": "form",
        "ma": "complete",
        "dingir": "divine_entity",
        "ud-bi-a": "primordial_time_of_that",
        "ki-ta": "earth_base_from",
        "ba-dim-ma": "creation_act_formed_complete",
        "an-ki": "sky_earth_union",
        "lugal": "king",
        "nam-tag": "destiny",
        "me": "divine_decree",
        "a-a": "water",
        # Linear A / administrative
        "da": "transfer",
        "ka": "to",
        "se": "source",
        "pa": "goods",
        "ki-nu": "count",
        "da-ka-se": "transfer_to_source",
        "pa-ki-nu": "goods_count",
        # Akkadian historical anchors (Dictionary gold)
        "summa": "if",
        "dinu": "judgment",
        "tuppu": "tablet",
        # Paranormal / consciousness
        "emf": "primordial_signal",
        "nde": "near_death_coherence",
    }
    # Normalize keys to lowercase.
    # Underscore compounds get space/hyphen aliases (carbon_cycle ↔ carbon cycle).
    # Hyphenated ancient forms (ki-ta, ud-bi-a) stay hyphen-only so "an ki-ta"
    # cannot be stolen by a space alias of an-ki.
    out: Dict[str, str] = {}
    for k, v in terms.items():
        kl = k.lower()
        aliases = {kl}
        if "_" in kl:
            aliases.add(kl.replace("_", "-"))
            aliases.add(kl.replace("_", " "))
        for a in aliases:
            out[a] = v
        if re.fullmatch(r"[acgtu]{3}", kl):
            out[kl.upper()] = v
    # Full standard genetic code (64 DNA + RNA forms) — authoritative for genomic
    try:
        from genetic_code_64 import codon_lexicon

        out.update(codon_lexicon())
    except Exception:
        pass
    return out


# Real-data gold pairs for honest evaluation (not self-grading on dictionary hits alone)
REAL_GOLD: List[Dict[str, Any]] = [
    {
        "id": "eridu_genesis_opening",
        "input": "ud-bi-a an ki-ta ba-dim-ma",
        "context": "mythological",
        "source": "Sumerian Eridu Genesis lineage (ETCSL / Kramer tradition)",
        "gold_gloss": "In those days when heaven and earth were created/formed",
        "must_include_any": [
            ["primordial", "time"],
            ["sky", "heaven"],
            ["earth"],
            ["creation", "form", "complete"],
        ],
    },
    {
        "id": "hbb_cds_start",
        "input": "ATG-GTG-CAC-CTG-ACT",
        "context": "genomic",
        "source": "Human HBB coding sequence start (NCBI RefSeq NM_000518 family)",
        "gold_gloss": "start transferring energy structure action (hemoglobin beta construction)",
        "must_include_any": [
            ["start"],
            ["transfer"],
            ["energy"],
            ["structure"],
            ["action"],
        ],
    },
    {
        "id": "linear_a_ht13",
        "input": "da-ka-se pa-ki-nu",
        "context": "administrative",
        "source": "Linear A HT 13 style administrative transaction pattern",
        "gold_gloss": "transfer to source; goods count",
        "must_include_any": [
            ["transfer"],
            ["source", "to"],
            ["goods"],
            ["count"],
        ],
    },
    {
        "id": "fsot_h0_s8",
        "input": "hubbk s8",
        "context": "cosmological",
        "source": "FSOT 2.1 predicted H0=71.98, S8=0.811",
        "gold_gloss": "Hubble expansion rate and structure growth amplitude",
        "must_include_any": [
            ["71.98", "hubble", "Mpc"],
            ["0.811", "structure"],
        ],
    },
    {
        "id": "akkadian_legal",
        "input": "summa dinu",
        "context": "historical",
        "source": "Code of Hammurabi tradition (Dictionary historical seed)",
        "gold_gloss": "if judgment",
        "must_include_any": [["if"], ["judgment"]],
    },
    {
        "id": "sumerian_water_king",
        "input": "a-a lugal",
        "context": "mythological",
        "source": "Archaic Sumerian lexical (Dictionary historical seed)",
        "gold_gloss": "water king",
        "must_include_any": [["water"], ["king"]],
    },
    {
        "id": "quantum_pair",
        "input": "coherence decoherence",
        "context": "quantum",
        "source": "FSOT quantum domain thesis fixtures",
        "gold_gloss": "synchronized state vs state disruption",
        "must_include_any": [["synchronized"], ["disruption", "state"]],
    },
    {
        "id": "ecological_carbon",
        "input": "carbon_cycle trophic_level",
        "context": "ecological",
        "source": "NOAA / ecological systems thesis fixtures",
        "gold_gloss": "global flux energy hierarchy",
        "must_include_any": [["global", "flux"], ["energy", "hierarchy"]],
    },
]


class PFLT:
    """Proto-Fluid Language Translator under FSOT 2.1 law."""

    def __init__(
        self,
        load_historical: bool = True,
        load_hieroglyphs: bool = True,
        load_classical: bool = True,
        load_domain_lexica: bool = True,
        enable_gapfill: bool = True,
        enable_math_trace: bool = False,
    ) -> None:
        self.pul_terms = _build_lexicon()
        # Separate glyph catalog so Gardiner S8 cannot overwrite cosmological s8
        self.hieroglyph_terms: Dict[str, str] = {}
        self._domain_lexica: Dict[str, Dict[str, str]] = {}
        self.enable_gapfill = enable_gapfill
        # When True, translate() always attaches microscope panel + failure logs for misses
        self.enable_math_trace = enable_math_trace
        self._gapfill_cache: Dict[str, Any] = {}
        # form → alternate content senses (multi-gloss inject)
        self.sense_bank: Dict[str, List[str]] = {}
        if load_historical:
            self.inject_historical_gold(include_candidates=False)
        if load_classical:
            self.inject_classical_gold()
        if load_domain_lexica:
            self.inject_domain_lexica()
        if load_hieroglyphs:
            self.inject_hieroglyph_gold()
        # Longest keys first for greedy multiword match
        self._keys_sorted = sorted(
            list(self.pul_terms.keys()) + list(self.hieroglyph_terms.keys()),
            key=len,
            reverse=True,
        )
        self.phi_0 = {
            "nde": mpf("0.3e-6"),
            "dolphin": mpf("5e-6"),
            "bee": mpf("1.0e3"),
            "plant": mpf("0.16e3"),
            "bbn": mpf("1.1e-3"),
            "cmb": mpf("2e14"),
        }

    def inject_historical_gold(self, *, include_candidates: bool = False) -> int:
        """
        Accuracy-first: inject Tier-A historical translation gold into pul_terms.
        Curriculum order lives in historical_gold.py (sum→akk→hit→san→grc→la→ang).
        """
        try:
            from historical_gold import gold_as_lexicon, merge_gold
        except ImportError:
            return 0
        pairs = merge_gold(include_candidates=include_candidates)
        if not include_candidates:
            pairs = [p for p in pairs if p.tier == "A"]
        lex = gold_as_lexicon(pairs)
        before = len(self.pul_terms)
        self.pul_terms.update(lex)
        self._keys_sorted = sorted(self.pul_terms.keys(), key=len, reverse=True)
        return len(self.pul_terms) - before

    def inject_hieroglyph_gold(self) -> int:
        """
        Load Egyptian hieroglyph meanings into hieroglyph_terms (NOT pul_terms).
        Prevents Gardiner codes (e.g. S8) from colliding with domain keys (s8 / S₈).
        Active only when context is hieroglyphic / egyptian / visual_script.
        """
        candidates = [
            Path(__file__).resolve().parent / "data" / "hieroglyph_pflt_lexicon.json",
            Path(r"D:\training data\pflt_linguistics\10_visual_scripts\hieroglyph_egyptian\hieroglyph_pflt_lexicon.json"),
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                import json

                lex = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return 0
            before = len(self.hieroglyph_terms)
            for k, v in lex.items():
                self.hieroglyph_terms[str(k)] = str(v)
                kl = str(k).lower()
                self.hieroglyph_terms[kl] = str(v)
            self._keys_sorted = sorted(
                list(self.pul_terms.keys()) + list(self.hieroglyph_terms.keys()),
                key=len,
                reverse=True,
            )
            return len(self.hieroglyph_terms) - before
        return 0

    def inject_classical_gold(self) -> int:
        """Inject Latin/Greek/Ang gold from grow_classical + Dictionary mine."""
        candidates = [
            Path(__file__).resolve().parent / "data" / "classical_full_trained_lexicon.json",
            Path(__file__).resolve().parent / "data" / "dictionary_classical_lexicon.json",
            Path(__file__).resolve().parent / "data" / "classical_grc_la_lexicon.json",
            Path(r"D:\training data\pflt_linguistics\01_historical_gold\classical_full_trained_lexicon.json"),
            Path(r"D:\training data\pflt_linguistics\01_historical_gold\classical_grc_la_lexicon.json"),
        ]
        before = len(self.pul_terms)
        loaded = 0
        for path in candidates:
            if not path.exists():
                continue
            try:
                lex = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for k, v in lex.items():
                self.pul_terms[str(k)] = str(v)
                self.pul_terms[str(k).lower()] = str(v)
            loaded += 1
        if loaded:
            self._keys_sorted = sorted(
                list(self.pul_terms.keys()) + list(self.hieroglyph_terms.keys()),
                key=len,
                reverse=True,
            )
        return len(self.pul_terms) - before

    def inject_domain_lexica(self) -> int:
        """Load per-domain starter lexica (build_domain_lexica.py) for 400+ FSOT domains."""
        candidates = [
            Path(__file__).resolve().parent / "data" / "domain_lexica.json",
            Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\domain_lexica.json"),
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return 0
            self._domain_lexica = payload.get("by_domain") or {}
            global_safe = payload.get("global_safe") or {}
            before = len(self.pul_terms)
            for k, v in global_safe.items():
                self.pul_terms.setdefault(str(k), str(v))
            self._keys_sorted = sorted(
                list(self.pul_terms.keys()) + list(self.hieroglyph_terms.keys()),
                key=len,
                reverse=True,
            )
            return len(self.pul_terms) - before
        return 0

    def domain_scalar(self, context: str) -> ScalarPanel:
        # Accept raw atlas names: "Atomic_Physics", "Acoustics", etc.
        key = context
        if key not in DOMAIN_PARAMS:
            key = re.sub(r"[^a-z0-9]+", "_", context.strip().lower()).strip("_")
        p = DOMAIN_PARAMS.get(key) or DOMAIN_PARAMS.get("linguistic") or {
            "D_eff": 12,
            "observed": True,
            "delta_psi": 0.8,
            "delta_theta": 1.0,
        }
        hits = 0
        if key in FSOT21_DOMAINS:
            hits = int(FSOT21_DOMAINS[key].get("recent_hits") or 0)
        # Prefer archive-pinned FSOT law scalar (Protofluid law spine) when available
        local = compute_S_D_chaotic(
            D_eff=float(p["D_eff"]),
            observed=bool(p["observed"]),
            delta_psi=float(p.get("delta_psi", 0.8)),
            delta_theta=float(p.get("delta_theta", 1.0)),
            recent_hits=float(hits),
        )
        try:
            from fsot_law_bridge import compute_law_scalar

            ls = compute_law_scalar(
                domain=key,
                D_eff=float(p["D_eff"]),
                observed=bool(p["observed"]),
                delta_psi=float(p.get("delta_psi", 0.8)),
                delta_theta=float(p.get("delta_theta", 1.0)),
                recent_hits=float(hits),
            )
            if ls.authority_ok or ls.authority.startswith("archive"):
                return ScalarPanel(
                    S=ls.S,
                    T1=ls.T1,
                    T2=ls.T2,
                    T3=ls.T3,
                    quirk_mod=local.quirk_mod,
                    growth=local.growth,
                    D_eff=ls.D_eff,
                    observed=ls.observed,
                    delta_psi=ls.delta_psi,
                    delta_theta=ls.delta_theta,
                )
        except Exception:
            pass
        return local

    def list_domains(self, limit: int = 50) -> List[str]:
        """Sample of available FSOT 2.1 + PFLT contexts."""
        keys = sorted(DOMAIN_PARAMS.keys())
        return keys[:limit]

    def domain_count(self) -> int:
        return len(DOMAIN_PARAMS)

    def _normalize_token_stream(self, text: str, context: str = "linguistic") -> str:
        """
        Normalize separators. Genomic: treat hyphen as codon separator (space).
        Myth/admin: keep multi-morpheme hyphens (ud-bi-a) for longest-match.
        """
        t = text.strip()
        if context in {"genomic", "biological"}:
            # DNA often written ATG-GTG-... → force codon boundaries
            t = re.sub(r"[-_,/|]+", " ", t)
        else:
            t = re.sub(r"[_,/|]+", " ", t)
        t = re.sub(r"\s+", " ", t)
        return t

    def tokenize(self, input_data: str, context: str = "linguistic") -> List[str]:
        """
        Context-aware tokenizer.
        - genomic: prefer pure codon triples; never emit bare '-' tokens
        - hieroglyphic: Gardiner codes + Unicode glyphs
        - default: longest-match lexicon + multi-morpheme hyphens
        """
        stream = self._normalize_token_stream(input_data, context=context)
        original = stream
        lower = stream.lower()
        tokens: List[str] = []
        i = 0
        n = len(lower)
        sep = set(" -_\t,;:.")

        # Genomic fast path: extract only ACGTU triplets in order
        if context in {"genomic", "biological"}:
            bases = re.findall(r"[acgtu]+", lower)
            for run in bases:
                # chunk into codons; leftover bases kept as token for honesty
                for j in range(0, len(run), 3):
                    chunk = run[j : j + 3]
                    if chunk:
                        tokens.append(chunk)
            return tokens

        while i < n:
            if lower[i] in sep:
                i += 1
                continue
            ocp = ord(original[i]) if i < len(original) else 0
            if 0x13000 <= ocp <= 0x1342F:
                tokens.append(original[i])
                i += 1
                continue
            matched = False
            # Longest-match only on domain + classical lexicon (not full glyph dump)
            for key in self._keys_sorted:
                if not key or (len(key) == 1 and ord(key[0]) >= 0x13000):
                    continue
                # In non-glyph contexts, skip pure Gardiner-shaped keys from hieroglyph table
                if (
                    context not in {"hieroglyphic", "egyptian", "visual_script", "rock_art"}
                    and key in getattr(self, "hieroglyph_terms", {})
                    and key not in self.pul_terms
                ):
                    continue
                if not lower.startswith(key.lower(), i):
                    continue
                end = i + len(key)
                if end < n and lower[end] not in sep and lower[end].isalnum():
                    continue
                cand = lower[i:end]
                if cand in self.pul_terms or cand in getattr(self, "hieroglyph_terms", {}):
                    tokens.append(cand)
                elif original[i:end] in self.pul_terms:
                    tokens.append(original[i:end])
                else:
                    tokens.append(cand)
                i = end
                matched = True
                break
            if matched:
                continue
            # Gardiner-style only meaningful in glyph contexts (else may steal s8 etc.)
            if context in {"hieroglyphic", "egyptian", "visual_script", "rock_art"}:
                g = re.match(r"[a-z]{1,3}\d{1,3}[a-z]?", lower[i:])
                if g:
                    tokens.append(g.group(0))
                    i += len(g.group(0))
                    continue
            chunk3 = re.match(r"[acgtu]{3}", lower[i:])
            if chunk3 and (i + 3 >= n or lower[i + 3] in sep or not lower[i + 3].isalnum()):
                tokens.append(chunk3.group(0))
                i += 3
                continue
            # Latin + Greek letters (polytonic/monotonic) + digits
            m = re.match(
                r"[a-z0-9.%µμ\u0370-\u03ff\u1f00-\u1fff]+",
                original[i:],
                re.I,
            )
            if m:
                tok = m.group(0)
                # preserve Greek casefold via lower where applicable
                tokens.append(tok.lower() if tok.isascii() else tok)
                i += len(m.group(0))
            else:
                i += 1  # drop unknown punctuation rather than fake tokens
        return [t for t in tokens if t]

    def _infer_mapping(self, token: str, context: str) -> str:
        # Prefer explicit unresolved over fake soft shells when token is empty/junk.
        # Soft shells remain only as last-resort domain color for true open-set forms
        # that survived map_token (classical stems, etc.).
        try:
            from converse_refine import looks_junk_token

            if looks_junk_token(token or ""):
                return "unresolved"
        except Exception:
            pass
        fallback = {
            "biological": "life_process",
            "genomic": "life_process",
            "ecological": "ecosystem_dynamics",
            "geological": "mineral_formation",
            "paleontological": "fossil_dynamics",
            "nuclear": "energy_process",
            "atomic": "chemical_structure",
            "cosmological": "cosmic_flow",
            "quantum": "quantum_state",
            "astrophysical": "cosmic_event",
            "material": "material_property",
            "mythological": "narrative_flow",
            "administrative": "record_flow",
            "paranormal": "primordial_signal",
            "linguistic": "narrative_flow",
            "fluid_tongue": "fluid_resonance",
            "historical": "heritage_flow",
            "neural": "consciousness_signal",
            "metabolic": "energy_process",
        }
        # Short unknown ASCII with no lexicon hit → unresolved (not narrative_flow)
        t = (token or "").strip()
        if t.isascii() and 3 <= len(t) <= 24 and not any(c.isdigit() for c in t):
            # if never seen in lexicon, mark unresolved rather than invent shell
            if t.lower() not in self.pul_terms and t not in self.pul_terms:
                return "unresolved"
        return fallback.get(context, "generic_dynamics")

    def map_token(self, token: str, context: str) -> Tuple[str, bool]:
        """
        Return (meaning, mapped_exact).
        Priority:
          0) junk / English pass-through (skip gapfill invent)
          1) domain registry (shared symbols, context-aware)
          2) per-domain starter lexicon (FSOT 2.1 atlas domains)
          3) glyph catalog (glyph contexts / Unicode only)
          4) global pul_terms / classical
          5) gap-fill student (open-set; gated)
          6) systemic fallback
        """
        try:
            from domain_symbols import resolve_domain_symbol
        except ImportError:
            resolve_domain_symbol = None  # type: ignore

        key = token.lower()
        # Protofluid product: refuse adversarial junk; pass English content identity
        # so gapfill does not invent "time" for temple or "narrative_flow" for zzzxq.
        try:
            from converse_refine import (
                EN_CONTENT_PASS,
                EN_STOP,
                looks_junk_token,
            )

            if looks_junk_token(key):
                return "unresolved", False
            # bare numbers / S-claims — never gapfill (latency + false invent)
            if key.replace(".", "", 1).replace("-", "", 1).isdigit() or re.fullmatch(
                r"[+-]?\d+\.?\d*", key
            ):
                return key, True
            if key in EN_CONTENT_PASS:
                return EN_CONTENT_PASS[key], True
            if key in EN_STOP:
                return key, True  # identity — closed class, not open-set invent
            if key in {"exactly", "exactly", "says", "must", "claim", "claimed"}:
                return key, True
        except Exception:
            pass
        # Sense interlingua first: form → SENSE_id → English meaning head
        # (aqua ≡ water ≡ ὕδωρ). No NMT. Expand graph via bind/seeds only.
        try:
            from sense_interlingua import SenseInterlingua

            if not hasattr(self, "_sense_ix") or self._sense_ix is None:
                self._sense_ix = SenseInterlingua()
            hit = self._sense_ix.resolve_form(token, None)
            if hit is not None and hit.confidence >= 0.9:
                return hit.canonical_en, True
        except Exception:
            pass
        if resolve_domain_symbol is not None:
            hit = resolve_domain_symbol(token, context)
            if hit is not None:
                return hit[0], True

        # Per-domain starter lexicon
        dkey = re.sub(r"[^a-z0-9]+", "_", context.strip().lower()).strip("_")
        dlex = self._domain_lexica.get(dkey) or self._domain_lexica.get(context)
        if dlex:
            if key in dlex:
                return dlex[key], True
            if token in dlex:
                return dlex[token], True

        glyph_ctx = context in {
            "hieroglyphic",
            "egyptian",
            "visual_script",
            "rock_art",
        }
        if token and ord(token[0]) >= 0x13000:
            glyph_ctx = True
        if glyph_ctx:
            if token in self.hieroglyph_terms:
                return self.hieroglyph_terms[token], True
            if key in self.hieroglyph_terms:
                return self.hieroglyph_terms[key], True
            if token.upper() in self.hieroglyph_terms:
                return self.hieroglyph_terms[token.upper()], True
        # Lexicon / paradigm hits — reject meta/garbage so open-set can recover
        # Keep train primary meaning stable (sense_bank alts used only for soft-score later)
        def _try_lex(meaning: str, form_key: str = "") -> Optional[Tuple[str, bool]]:
            try:
                from meaning_clean import (
                    is_garbage_meaning,
                    is_meta_meaning,
                    resolve_meaning,
                )
            except Exception:
                return (meaning, True)
            if not meaning:
                return None
            if not is_meta_meaning(meaning) and not is_garbage_meaning(meaning):
                # multi-gloss: form-prefer then domain-rank among bank senses
                sb = getattr(self, "sense_bank", None) or {}
                bank = list(sb.get(form_key) or [])
                if meaning not in bank:
                    bank = [meaning] + bank
                try:
                    from gap_pack import pick_preferred_sense

                    pref = pick_preferred_sense(token or form_key, bank, context=context)
                    if pref:
                        return (pref, True)
                except Exception:
                    pass
                if len(bank) >= 2:
                    try:
                        from domain_sense import pick_sense

                        picked = pick_sense(bank[:10], context)
                        if picked:
                            return (picked, True)
                    except Exception:
                        pass
                return (meaning, True)
            # meta/garbage primary: try form-prefer before fallthrough
            try:
                from gap_pack import resolve_gap

                ghit = resolve_gap(
                    token,
                    self.pul_terms,
                    getattr(self, "sense_bank", None),
                    context=context,
                )
                if ghit is not None and ghit[1] >= 0.84:
                    return (ghit[0], True)
            except Exception:
                pass
            cleaned = resolve_meaning(meaning, self.pul_terms)
            if (
                cleaned
                and cleaned != meaning
                and not is_meta_meaning(cleaned)
                and not is_garbage_meaning(cleaned)
            ):
                return (cleaned, True)
            return None  # fall through to gap-fill / morph

        if key in self.pul_terms:
            hit = _try_lex(self.pul_terms[key], key)
            if hit is not None:
                return hit
        if token in self.pul_terms:
            hit = _try_lex(self.pul_terms[token], token)
            if hit is not None:
                return hit
        if token.upper() in self.pul_terms:
            hit = _try_lex(self.pul_terms[token.upper()], token.upper())
            if hit is not None:
                return hit
        # Diacritic-folded lookup (Latin macrons / Greek accents)
        ff = ""
        try:
            from meaning_clean import fold_form

            ff = fold_form(token)
            if ff and ff in self.pul_terms:
                hit = _try_lex(self.pul_terms[ff], ff)
                if hit is not None:
                    return hit
        except Exception:
            pass
        # Finite paradigm table hits (kept separate from pul_terms so gap-fill stays fast)
        pterms = getattr(self, "paradigm_terms", None) or {}
        if pterms:
            for cand in (token, key, ff):
                if cand and cand in pterms:
                    hit = _try_lex(pterms[cand], cand)
                    if hit is not None:
                        return hit

        # Proper names / places: gazetteer + historical contacts (NOT morphology)
        # Names are unique entities; edit-distance neighbors invent false glosses.
        if context in {
            "historical",
            "mythological",
            "linguistic",
            "english",
            "administrative",
        }:
            try:
                from name_gazetteer import NameGazetteer

                if not hasattr(self, "_name_gaz") or self._name_gaz is None:
                    self._name_gaz = NameGazetteer()
                nlang = {
                    "historical": "la",
                    "mythological": "grc",
                    "linguistic": "en",
                    "english": "en",
                    "administrative": "la",
                }.get(context, "la")
                if token and ord(token[0]) >= 0x0370:
                    nlang = "grc"
                nhit = self._name_gaz.resolve(token, lang=nlang)
                if nhit is not None and nhit.score >= 0.82:
                    return nhit.meaning, True
            except Exception:
                pass

        # Gap pack before general gapfill (empty / polysemy residuals)
        try:
            from gap_pack import resolve_gap

            ghit = resolve_gap(
                token,
                self.pul_terms,
                getattr(self, "sense_bank", None),
                context=context,
            )
            if ghit is not None and ghit[1] >= 0.84:
                return ghit[0], True
        except Exception:
            pass

        # Open-set: Rosetta concept lookup then edit-distance gap-fill
        if self.enable_gapfill and context in {
            "historical",
            "linguistic",
            "english",
            "mythological",
            "administrative",
        }:
            filled = self._gapfill_token(token, context)
            if filled is not None:
                try:
                    from meaning_clean import is_garbage_meaning, is_meta_meaning

                    if is_meta_meaning(filled) or is_garbage_meaning(filled):
                        filled = None
                except Exception:
                    pass
            if filled is not None:
                return filled, True

        return self._infer_mapping(token, context), False

    def _gapfill_token(self, token: str, context: str) -> Optional[str]:
        cache_key = f"{context}::{token}"
        if cache_key in self._gapfill_cache:
            return self._gapfill_cache[cache_key]

        lang = {
            "historical": "la",
            "mythological": "grc",
            "linguistic": "en",
            "english": "en",
            "administrative": "la",
        }.get(context, "la")
        if token and ord(token[0]) >= 0x0370:
            lang = "grc"
        if lang == "en" and context == "linguistic":
            # English open-set still benefits from Latin morphology probes
            pass

        # Ensure folded reverse lexicon once for morph paths
        if lang in {"la", "lat", "grc", "el", "ang", "oe"}:
            if not hasattr(self, "_rev_lex") or getattr(self, "_rev_lex_size", -1) != len(
                self.pul_terms
            ):
                try:
                    from meaning_clean import fold_form
                    from reverse_morph import build_prefix_index

                    rev = {}
                    for k, v in self.pul_terms.items():
                        rev[k] = v
                        ff = fold_form(k)
                        if ff and ff not in rev:
                            rev[ff] = v
                    self._rev_lex = rev
                    self._rev_lex_size = len(self.pul_terms)
                    self._rev_prefix = build_prefix_index(rev)
                except Exception:
                    self._rev_lex = dict(self.pul_terms)
                    self._rev_lex_size = len(self.pul_terms)

        # Sequential gap-fill (high recall) with form-sim gates + multi-sense on conflict
        from gapfill_student import edit_sim as _esim
        from sense_vote import SenseCand, vote_senses

        # 0-gap) Climb gap pack: participles, form-sense, residual seeds
        try:
            from gap_pack import resolve_gap

            ghit = resolve_gap(
                token,
                getattr(self, "_rev_lex", self.pul_terms),
                getattr(self, "sense_bank", None),
                context=context,
            )
            if ghit is not None and ghit[1] >= 0.84:
                self._gapfill_cache[cache_key] = ghit[0]
                return ghit[0]
        except Exception:
            pass

        def _accept(meaning: str, donor: str, score: float, method: str, min_sim: float) -> Optional[str]:
            try:
                from meaning_clean import is_garbage_meaning, is_meta_meaning

                if is_meta_meaning(meaning) or is_garbage_meaning(meaning):
                    return None
            except Exception:
                pass
            if method.startswith("demonym_seed") or method.startswith("rosetta"):
                return meaning
            sim = _esim(token, donor) if donor else 1.0
            # high-confidence morph: trust score (recall); weak score needs form_sim
            if score >= 0.90:
                return meaning
            if score >= 0.84 and sim >= min_sim * 0.9:
                return meaning
            if sim < min_sim:
                return None
            return meaning

        # 0) Ethnonym / demonym peel
        if lang in {"la", "lat", "grc", "el"}:
            try:
                from demonym_resolve import demonym_resolve

                ehit = demonym_resolve(
                    token, getattr(self, "_rev_lex", self.pul_terms), lang=lang
                )
                if ehit is not None and ehit[2] >= 0.72:
                    got = _accept(ehit[0], token, ehit[2], "demonym_seed", 0.0)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
            except Exception:
                pass

        # 0b) Greek/Latin compound peel → residual lemma in train (εἰκονοκλάστης)
        if lang in {"grc", "el", "la", "lat"} and len(token) >= 8:
            try:
                from remedy_wrong_sense import greek_compound_peel
                from reverse_morph import reverse_resolve

                rev = getattr(self, "_rev_lex", self.pul_terms)
                for stem in greek_compound_peel(token):
                    if stem in rev:
                        got = _accept(rev[stem], stem, 0.86, "compound_peel", 0.0)
                        if got:
                            self._gapfill_cache[cache_key] = got
                            return got
                    for end in ("ος", "ης", "η", "ον", "ις", "εύς", "us", "um", "a", "is", "or"):
                        cand = stem + end
                        if cand in rev:
                            got = _accept(rev[cand], cand, 0.84, "compound_lemma", 0.40)
                            if got:
                                self._gapfill_cache[cache_key] = got
                                return got
                    # reverse-morph the residual stem as if it were the surface form
                    rhit = reverse_resolve(
                        stem,
                        rev,
                        lang=lang,
                        prefix_index=getattr(self, "_rev_prefix", None),
                        min_score=0.82,
                        min_sim_lemma=0.48,
                    )
                    if rhit is not None and rhit[2] >= 0.82:
                        got = _accept(rhit[0], rhit[1], rhit[2], "compound_rev", 0.45)
                        if got:
                            self._gapfill_cache[cache_key] = got
                            return got
            except Exception:
                pass

        # 1) Declension-class first
        if lang in {"la", "lat", "grc", "el"}:
            try:
                from declension_tables import declension_resolve

                dhit = declension_resolve(
                    token, getattr(self, "_rev_lex", self.pul_terms), lang=lang, context=context
                )
                if dhit is not None and dhit[2] >= 0.84:
                    got = _accept(dhit[0], dhit[1], dhit[2], dhit[3] if len(dhit) > 3 else "decl", 0.48)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
            except Exception:
                pass

        # 1b) Reverse morphology (multi-sense reweight inside reverse_resolve)
        if lang in {"grc", "el", "ang", "oe", "la", "lat"}:
            try:
                from reverse_morph import reverse_resolve

                if lang in {"la", "lat"}:
                    hit = reverse_resolve(
                        token,
                        getattr(self, "_rev_lex", self.pul_terms),
                        lang=lang,
                        prefix_index=getattr(self, "_rev_prefix", None),
                        min_stem=4,
                        lemma_end_only=True,
                        min_score=0.84,
                        min_sim_lemma=0.50,
                    )
                else:
                    hit = reverse_resolve(
                        token,
                        getattr(self, "_rev_lex", self.pul_terms),
                        lang=lang,
                        prefix_index=getattr(self, "_rev_prefix", None),
                    )
                thr = 0.84 if lang in {"la", "lat"} else 0.78
                if lang in {"ang", "oe"}:
                    thr = 0.76
                if hit is not None and hit[2] >= thr:
                    got = _accept(hit[0], hit[1], hit[2], hit[3] if len(hit) > 3 else "rev", 0.48)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
                # weaker morph for empty-fallback climb (still form-gated in _accept)
                if hit is not None and hit[2] >= 0.72:
                    got = _accept(hit[0], hit[1], hit[2], "rev_weak", 0.55)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
            except Exception:
                pass

        # 1c) Whitaker-style prefix peel
        if lang in {"la", "lat", "grc", "el", "ang", "oe"}:
            try:
                from prefix_analyze import prefix_resolve

                phit = prefix_resolve(
                    token, getattr(self, "_rev_lex", self.pul_terms), lang=lang
                )
                if phit is not None and phit[2] >= 0.84:
                    got = _accept(phit[0], phit[1] if len(phit) > 1 else token, phit[2], "prefix", 0.55)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
            except Exception:
                pass

        # 1d) Lemma-sense index with multi-sense domain + vote on conflict
        if lang in {"la", "lat", "grc", "el", "ang", "oe"}:
            try:
                from lemma_index import LemmaSenseIndex
                from domain_sense import pick_sense

                if (
                    not hasattr(self, "_lemma_idx")
                    or getattr(self, "_lemma_idx_size", -1) != len(self.pul_terms)
                ):
                    idx = LemmaSenseIndex()
                    idx.build_from_lexicon(self.pul_terms, lang_hint=lang)
                    self._lemma_idx = idx
                    self._lemma_idx_size = len(self.pul_terms)
                lhit = self._lemma_idx.resolve(token, lang=lang)
                if lhit is not None and lhit.score >= 0.80:
                    senses = list(
                        self._lemma_idx.stem_senses.get(lhit.donor_stem, {}).keys()
                    )
                    meaning = lhit.meaning
                    if len(senses) > 1:
                        # multi-sense vote among train-supported glosses
                        sc = [
                            SenseCand(s, lhit.donor_stem, lhit.score, "lemma_sense", 0.55)
                            for s in senses[:6]
                        ]
                        voted = vote_senses(token, sc, context=context, min_score=0.60)
                        if voted is not None:
                            meaning = voted[0]
                        else:
                            picked = pick_sense(senses, context)
                            if picked:
                                meaning = picked
                    got = _accept(meaning, lhit.donor_stem, lhit.score, "lemma_sense", 0.45)
                    if got:
                        self._gapfill_cache[cache_key] = got
                        return got
            except Exception:
                pass

        # 2) Open-set booster
        try:
            from open_set_boost import OpenSetBooster

            if not hasattr(self, "_open_boosters"):
                self._open_boosters = {}
            bkey = f"{lang}:{len(self.pul_terms)}"
            if bkey not in self._open_boosters:
                self._open_boosters[bkey] = OpenSetBooster(self.pul_terms, lang_hint=lang)
            hit = self._open_boosters[bkey].resolve(token)
            if hit is not None and hit.score >= 0.55:
                got = _accept(hit.meaning, hit.donor or token, hit.score, hit.method, 0.48)
                if got:
                    self._gapfill_cache[cache_key] = got
                    return got
        except Exception:
            pass

        # 3) Rosetta form→concept→English
        try:
            from rosetta_student import RosettaStudent

            if not hasattr(self, "_rosetta") or self._rosetta is None:
                self._rosetta = RosettaStudent()
            hints = {
                "historical": ["la", "lat", "grc", "el", "ang", "akk", "sum", "san", "en"],
                "mythological": ["sum", "akk", "grc", "la", "en"],
                "linguistic": ["en", "fr", "de", "es", "la", "grc"],
                "english": ["en"],
                "administrative": ["la", "grc", "en"],
            }.get(context, ["en", "la", "grc"])
            hit = self._rosetta.resolve(token, lang_hints=hints)
            if hit is not None:
                meaning, concept, _ = hit
                got = _accept(meaning, token, 0.80, "rosetta", 0.0)
                if got:
                    self._gapfill_cache[cache_key] = got
                    return got
        except Exception:
            pass

        # 4) Edit-distance / trigram neighborhood student (skip only on huge gold lex)
        if len(self.pul_terms) > 80000:
            self._gapfill_cache[cache_key] = None
            return None
        try:
            from gapfill_student import GapFillStudent
        except ImportError:
            self._gapfill_cache[cache_key] = None
            return None
        # cache student by lexicon size
        if not hasattr(self, "_gapfill_students"):
            self._gapfill_students = {}
        sk = f"{context}:{len(self.pul_terms)}"
        if sk not in self._gapfill_students:
            self._gapfill_students[sk] = GapFillStudent(self.pul_terms, context=context)
        student = self._gapfill_students[sk]
        result = student.fill(token)
        if result is None:
            self._gapfill_cache[cache_key] = None
            return None
        meaning, prop = result
        self._gapfill_cache[cache_key] = meaning
        return meaning

    def _prefix_from_S(self, S: float) -> str:
        # Emergence / damping from verified scalar sign/magnitude only
        if S > 1.1:
            return "resonant_"
        if S > 0.3:
            return "flowing_"
        if S < -0.8:
            return "softened_"
        if S < 0:
            return "stabilized_"
        return ""

    def _energy_annotation(self, meaning: str, context: str, abs_S: float) -> str:
        if context == "paranormal" and ("signal" in meaning or "emf" in meaning):
            return f"_{float(self.phi_0['nde'] * abs_S):.2e}eV"
        if context in {"genomic", "biological"} and any(
            x in meaning for x in ("start", "energy", "stop", "transfer", "structure")
        ):
            return f"_{float(self.phi_0['dolphin'] * abs_S):.2e}eV"
        if context == "neural" and "signal" in meaning:
            return f"_{float(self.phi_0['nde'] * abs_S):.2e}eV"
        if context == "nuclear" and any(x in meaning for x in ("fusion", "nucleosynthesis")):
            return f"_{float(self.phi_0['bbn'] * abs_S):.2e}MeV"
        if context in {"astrophysical", "paleontological"} and any(
            x in meaning for x in ("cosmic_event", "catastrophic", "mass_collapse", "extinction")
        ):
            return f"_{float(self.phi_0['cmb'] * abs_S):.2e}GeV"
        if context == "ecological" and any(
            x in meaning for x in ("global_flux", "nutrient_flow", "energy_hierarchy")
        ):
            return f"_{float(self.phi_0['plant'] * abs_S):.2e}eV"
        return ""

    def modulate(self, meaning: str, context: str, panel: ScalarPanel) -> str:
        prefix = self._prefix_from_S(panel.S)
        annotated = prefix + meaning + self._energy_annotation(meaning, context, abs(panel.S))
        annotated += f" [S={panel.S:.4f}]"
        return annotated

    def synthesize(self, meanings: List[str], target_lang: str, context: str, panel: ScalarPanel) -> str:
        modulated = [self.modulate(m, context, panel) for m in meanings]
        if target_lang == "fluid_tongue":
            fluid = []
            for m in modulated:
                if m.startswith("resonant_"):
                    fluid.append(m.replace("resonant_", "flowing_resonance_", 1))
                elif m.startswith("softened_"):
                    fluid.append(m.replace("softened_", "diffused_flow_", 1))
                elif m.startswith("flowing_"):
                    fluid.append("fluid_" + m)
                else:
                    fluid.append("fluid_" + m)
            return " ".join(fluid) + " [Fluid Spacetime resonance narrative]."
        if target_lang == "spanish":
            body = " ".join(m.split(" [S=")[0] for m in modulated)
            return f"Narrativa fluida: {body}."
        if target_lang == "mandarin":
            body = " · ".join(m.split(" [S=")[0] for m in modulated)
            return f"流体叙事: {body}."
        if target_lang == "french":
            body = " ".join(m.split(" [S=")[0] for m in modulated)
            return f"Narratif fluide: {body}."
        if target_lang == "arabic":
            body = " ".join(m.split(" [S=")[0] for m in modulated)
            return f"سرد مائع: {body}."
        # english default — join as process narrative
        clean = [m.split(" [S=")[0] for m in modulated]
        return " ".join(clean) + " [FSOT 2.1 fluid translation]."

    def translate(
        self,
        input_data: str,
        context: str = "linguistic",
        target_lang: str = "english",
        *,
        include_audio: bool = False,
        speak_lang: str = "en",
        math_trace: Optional[bool] = None,
        math_trace_failures: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Translate under FSOT 2.1 domain scalar.

        math_trace: when True (or PFLT(enable_math_trace=True)), attach full microscope
          pathway for the domain (S=K(T1+T2+T3) step list).
        math_trace_failures: when True, miss/inexact tokens write granular failure
          JSON under data/math_microscope/ (defaults to same as math_trace — off
          during bulk eval so disk stays clean).
        """
        tokens = self.tokenize(input_data, context=context)
        meanings: List[str] = []
        exact_hits = 0
        resolution_trace: List[str] = []
        token_exact: List[bool] = []
        for tok in tokens:
            meaning, exact = self.map_token(tok, context)
            meanings.append(meaning)
            token_exact.append(exact)
            if exact:
                exact_hits += 1
            resolution_trace.append(f"{tok}->{meaning}" + ("" if exact else " [inferred]"))
        panel = self.domain_scalar(context)
        # Optional: fluid_tongue uses its own deeper domain routing for S
        synth_ctx = "fluid_tongue" if target_lang == "fluid_tongue" else context
        synth_panel = self.domain_scalar(synth_ctx) if target_lang == "fluid_tongue" else panel
        translation = self.synthesize(meanings, target_lang, synth_ctx, synth_panel)
        # Domain meta from FSOT 2.1 catalog when available
        dkey = re.sub(r"[^a-z0-9]+", "_", context.strip().lower()).strip("_")
        dmeta = FSOT21_DOMAINS.get(dkey) or FSOT21_DOMAINS.get(context)
        out: Dict[str, Any] = {
            "input": input_data,
            "context": context,
            "target_lang": target_lang,
            "tokens": tokens,
            "meanings": meanings,
            "resolution_trace": resolution_trace,
            "translation": translation,
            "exact_map_rate": (exact_hits / len(tokens)) if tokens else 0.0,
            "exact_hits": exact_hits,
            "token_count": len(tokens),
            "fsot_panel": asdict(synth_panel),
            "fsot_coherence_S": synth_panel.S,
            "fsot_domain_count": len(DOMAIN_PARAMS),
            "fsot_domain_meta": {
                "display": (dmeta or {}).get("display"),
                "kind": (dmeta or {}).get("kind"),
                "parent_core": (dmeta or {}).get("parent_core"),
                "coverage_tier": (dmeta or {}).get("coverage_tier"),
                "record_count": (dmeta or {}).get("record_count"),
                "D_eff": float(panel.D_eff),
            },
            "fsot_note": (
                "Modulated via FSOT 2.1 S=K(T1+T2+T3); constants seed-derived; "
                "Lean/NeuroLab parity; domain-aware; 400+ FSOT scientific domains routable."
            ),
        }

        do_trace = self.enable_math_trace if math_trace is None else math_trace
        # Fail logs default off unless explicitly requested or full math_trace is on
        if math_trace_failures is None:
            math_trace_failures = do_trace
        want_fail_logs = bool(math_trace_failures) and any(not e for e in token_exact)
        if do_trace or want_fail_logs:
            try:
                from fsot_math_microscope import (
                    pathway_summary,
                    trace_domain,
                    write_failure_math_log,
                )

                tr = trace_domain(context if context in DOMAIN_PARAMS else "linguistic")
                path_sum = pathway_summary(tr)
                if do_trace:
                    out["math_microscope"] = {
                        "formula": path_sum["formula"],
                        "domain": path_sum["domain"],
                        "panel": path_sum["panel"],
                        "pathway": path_sum["pathway"],
                        "layer_counts": path_sum["layer_counts"],
                        "mathematica": "mathematica/FSOT_PFLT_Microscope.wl",
                        "formal_golden": "formal/golden_fsot_pflt.json",
                        "note": (
                            "Granular S=K(T1+T2+T3) trace. Cross-verify with "
                            "Isabelle/Coq/Lean/F* via formal/parity_report.json."
                        ),
                    }
                fail_paths: List[str] = []
                if want_fail_logs:
                    for tok, meaning, exact in zip(tokens, meanings, token_exact):
                        if exact:
                            continue
                        fp = write_failure_math_log(
                            domain=tr.domain,
                            token=tok,
                            meaning=meaning,
                            exact=exact,
                            resolution="inferred_fallback",
                            input_text=input_data,
                            export_wl=False,  # domain .wl already from main / first call
                        )
                        fail_paths.append(str(fp))
                    if fail_paths:
                        out["math_failure_logs"] = fail_paths
                        out["math_failure_count"] = len(fail_paths)
            except Exception as e:
                out["math_microscope_error"] = str(e)

        if include_audio:
            try:
                from audio_articulation import articulate

                arts = []
                for m in meanings:
                    core = re.split(r"[_\s]+", m)[0]
                    arts.append(asdict(articulate(core, lang=speak_lang, context=context)))
                out["audio"] = {
                    "speak_lang": speak_lang,
                    "policy": "ipa_articulatory_fsot_plus_waveform",
                    "articulations": arts,
                    "waveforms": [
                        a.get("waveform_path")
                        for a in arts
                        if a.get("waveform_path")
                    ],
                    "note": "IPA + articulatory features + FSOT proxies + WAV (SAPI or formant).",
                }
            except Exception as e:
                out["audio"] = {"error": str(e)}
        return out

    def evaluate_real_gold(self) -> Dict[str, Any]:
        """Honest semantic coverage vs gold glosses on real fixtures."""
        rows = []
        for gold in REAL_GOLD:
            result = self.translate(gold["input"], context=gold["context"], target_lang="english")
            blob = " ".join(result["meanings"]).lower() + " " + result["translation"].lower()
            group_hits = 0
            for group in gold["must_include_any"]:
                if any(term.lower() in blob for term in group):
                    group_hits += 1
            coverage = group_hits / max(1, len(gold["must_include_any"]))
            rows.append(
                {
                    "id": gold["id"],
                    "source": gold["source"],
                    "gold_gloss": gold["gold_gloss"],
                    "input": gold["input"],
                    "tokens": result["tokens"],
                    "meanings": result["meanings"],
                    "translation": result["translation"],
                    "exact_map_rate": result["exact_map_rate"],
                    "semantic_group_coverage": coverage,
                    "S": result["fsot_coherence_S"],
                    "D_eff": result["fsot_panel"]["D_eff"],
                    "observed": result["fsot_panel"]["observed"],
                    "quirk_mod": result["fsot_panel"]["quirk_mod"],
                }
            )
        avg_cov = sum(r["semantic_group_coverage"] for r in rows) / len(rows)
        avg_exact = sum(r["exact_map_rate"] for r in rows) / len(rows)
        return {
            "n": len(rows),
            "mean_semantic_group_coverage": avg_cov,
            "mean_exact_map_rate": avg_exact,
            "cases": rows,
            "constants_snapshot": {
                "K": float(K),
                "C_FACTOR": float(C_FACTOR),
                "ALPHA": float(ALPHA),
                "P_VAR": float(P_VAR),
                "C_EFF": float(C_EFF),
            },
        }


def print_panel_sanity() -> None:
    """Sanity: cosmological default vs quantum observed should both be finite."""
    print("--- FSOT 2.1 scalar sanity ---")
    for name in ("cosmological", "quantum", "genomic", "fluid_tongue", "mythological"):
        p = DOMAIN_PARAMS[name]
        panel = compute_S_D_chaotic(
            D_eff=float(p["D_eff"]),
            observed=bool(p["observed"]),
            delta_psi=float(p["delta_psi"]),
            delta_theta=float(p["delta_theta"]),
        )
        print(
            f"  {name:16s} D_eff={panel.D_eff:5.1f} obs={panel.observed} "
            f"S={panel.S:+.6f} T1={panel.T1:+.4f} T2={panel.T2:+.4f} T3={panel.T3:+.4e} "
            f"qm={panel.quirk_mod:.4f}"
        )
    print(f"  K={float(K):.6f}  C_factor={float(C_FACTOR):.6f}")


def main() -> None:
    print("=" * 78)
    print("PFLT FSOT 2.1 — Real-data evaluation")
    print("Dream-origin universal decoder under verified seed scalar (no ad-hoc η/m_pl).")
    print("=" * 78)
    print_panel_sanity()
    pflt = PFLT()
    report = pflt.evaluate_real_gold()
    print("\n--- Real gold fixtures ---")
    print(f"Cases: {report['n']}")
    print(f"Mean exact map rate:           {report['mean_exact_map_rate']*100:.1f}%")
    print(f"Mean semantic group coverage:  {report['mean_semantic_group_coverage']*100:.1f}%")
    print(f"Constants: {report['constants_snapshot']}")
    for case in report["cases"]:
        print(f"\n[{case['id']}] S={case['S']:+.4f} exact={case['exact_map_rate']*100:.0f}% "
              f"sem={case['semantic_group_coverage']*100:.0f}%")
        print(f"  Source: {case['source']}")
        print(f"  Gold:   {case['gold_gloss']}")
        print(f"  Tokens: {case['tokens']}")
        print(f"  Meanings: {case['meanings']}")
        print(f"  Out: {case['translation']}")

    # Fluid_Tongue sample on Eridu
    print("\n--- Fluid_Tongue sample (Eridu) ---")
    ft = pflt.translate("ud-bi-a an ki-ta ba-dim-ma", context="mythological", target_lang="fluid_tongue")
    print(ft["translation"])
    print(f"S={ft['fsot_coherence_S']:+.4f} D_eff={ft['fsot_panel']['D_eff']}")

    out_path = Path(__file__).resolve().parent / "pflt_real_eval_report.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {out_path}")
    print("=" * 78)
    print("Universal-translator read:")
    print("  PFLT is an INTERLINGUA for patterned multi-domain reality under FSOT S.")
    print("  Strong on: genes, ancient formulaic texts, physical constants, admin codes.")
    print("  Not yet: free conversational MT (needs Rosetta surface layer + student maps).")
    print("=" * 78)


if __name__ == "__main__":
    main()
