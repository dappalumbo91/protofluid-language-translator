#!/usr/bin/env python3
"""
Protofluid Language Translator — conversation + knowledge relay.

Product surface:

  input (any language/script)
    → mode detect (classical / science / english meta / modern)
    → pathway reason (FSOT domain graph multi-hop)
    → domain route (language cues beat earth-science false hits)
    → translate (language surface; English pass-through; junk → unresolved)
    → FSOT law scalar (archive-pinned authority)
    → retrieve (session ledger + archive memory, deduped)
    → compose relay (archive-first for science; no flowing_* on English)
    → append claims (append-only; never rewrite law)

FSOT is the factual base. Lexicon/morph is the language surface only.
"""
from __future__ import annotations

import argparse
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from certified_math import certify_turn, format_cert_lines
from converse_refine import (
    clean_meanings,
    dedup_knowledge,
    detect_input_mode,
    gloss_line,
    plain_relay,
    preferred_domain,
    science_answer_lines,
)
from fsot_law_bridge import compute_law_scalar, law_status
from knowledge_ledger import KnowledgeLedger, claim_from_translate
from ledger_hygiene import filter_session_claims
from observer_densify import get_observer
from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, FSOT21_DOMAINS, PFLT
from teach_panel import format_teach_block, teach_pairs

ROOT = __file__  # noqa: F841 — kept for path-relative tools

# Keyword domain hints (weighted in route_domain)
_DOMAIN_HINTS: Dict[str, List[str]] = {
    "linguistic": [
        "word", "language", "speech", "name", "write", "read", "say",
        "lingua", "λόγος", "verbum", "zipf", "entropy", "phoneme",
        "translate", "translation", "lexicon", "english", "greek",
    ],
    "historical": [
        "war", "king", "city", "empire", "people", "rome", "roman",
        "latin", "hand", "hands", "aqua", "manus", "classical",
    ],
    "mythological": [
        "god", "goddess", "hero", "zeus", "temple", "myth", "divine",
        "soul", "θεός",
    ],
    "quantum": ["quantum", "photon", "qubit", "entangle"],
    "cosmological": ["cosmos", "galaxy", "hubble", "universe", "star", "sky"],
    "genomic": ["gene", "dna", "codon", "protein", "genome"],
    "biological": ["cell", "life", "blood", "organism", "species"],
    "consciousness": ["mind", "conscious", "observer", "aware", "thought"],
    "nuclear": ["nuclear", "fission", "fusion", "isotope"],
    "geological": ["rock", "earth", "mineral", "plate", "quake"],
}

# Domains that must not steal language questions
_SECONDARY_SCIENCE = {
    "oceanography",
    "chemistry",
    "fluid_dynamics",
    "meteorology",
    "atmospheric_physics",
    "seismology",
}


def route_domain(
    text: str,
    explicit: Optional[str] = None,
    *,
    pathway_hint: Optional[str] = None,
) -> str:
    """Pick FSOT/PFLT domain — language / classical overrides first."""
    if explicit and explicit in DOMAIN_PARAMS:
        return explicit
    if explicit:
        key = re.sub(r"[^a-z0-9]+", "_", explicit.strip().lower()).strip("_")
        if key in DOMAIN_PARAMS:
            return key

    blob = (text or "").lower()
    scores: Dict[str, float] = {}
    for dom, keys in _DOMAIN_HINTS.items():
        sc = float(sum(1 for k in keys if k.lower() in blob))
        if sc > 0 and dom in DOMAIN_PARAMS:
            scores[dom] = sc

    best = "linguistic"
    score = 0.0
    if scores:
        best, score = max(scores.items(), key=lambda kv: kv[1])

    # Product hard overrides (latin / zipf / classical forms)
    override = preferred_domain(
        text,
        pathway_hint=pathway_hint,
        keyword_domain=best if score else None,
        keyword_score=int(score),
    )
    if override and override in DOMAIN_PARAMS:
        return override

    # Pathway hint when keywords weak
    if pathway_hint and pathway_hint in DOMAIN_PARAMS:
        if score < 2:
            # never let secondary earth-science win on language-ish text
            if pathway_hint in _SECONDARY_SCIENCE and score >= 1:
                return best
            if pathway_hint in _SECONDARY_SCIENCE:
                # re-check language cues
                o2 = preferred_domain(text, pathway_hint=pathway_hint)
                if o2:
                    return o2
            return pathway_hint
        if pathway_hint == best:
            return pathway_hint

    # Atlas name match only if whole-word-ish (avoid 'water' ⊂ nothing;
    # still avoid loose substring domain names for short queries)
    if score == 0:
        for k in DOMAIN_PARAMS:
            if len(k) >= 5 and (f" {k.replace('_', ' ')} " in f" {blob} " or blob == k):
                if k not in _SECONDARY_SCIENCE or "ocean" in blob or "sea" in blob:
                    return k
    return best if best in DOMAIN_PARAMS else "linguistic"


@dataclass
class ConverseTurn:
    turn: int
    role: str  # user | pflt
    text: str
    domain: str = ""
    S: float = 0.0
    meanings: List[str] = field(default_factory=list)
    claim_ids: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


class ProtofluidTranslator:
    """
    Protofluid Language Translator intelligence surface.
    """

    def __init__(
        self,
        *,
        pflt: Optional[PFLT] = None,
        ledger: Optional[KnowledgeLedger] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.pflt = pflt or PFLT(
            load_historical=True,
            load_classical=True,
            load_hieroglyphs=True,
            load_domain_lexica=True,
            enable_gapfill=True,
        )
        self.ledger = ledger or KnowledgeLedger()
        self.session_id = session_id or str(uuid.uuid4())
        self.history: List[ConverseTurn] = []
        self._turn = 0
        self._reasoner = None  # lazy PathwayReasoner

    def _get_reasoner(self):
        if self._reasoner is None:
            try:
                from pathway_reasoner import PathwayReasoner

                self._reasoner = PathwayReasoner(DOMAIN_PARAMS, FSOT21_DOMAINS)
            except Exception:
                self._reasoner = False
        return self._reasoner if self._reasoner is not False else None

    def law(self, domain: str) -> Dict[str, Any]:
        key = domain if domain in DOMAIN_PARAMS else "linguistic"
        p = DOMAIN_PARAMS.get(key) or DOMAIN_PARAMS["linguistic"]
        hits = 0
        if key in FSOT21_DOMAINS:
            hits = int(FSOT21_DOMAINS[key].get("recent_hits") or 0)
        hits = min(hits + max(0, self._turn // 3), 20)
        ls = compute_law_scalar(
            domain=key,
            D_eff=float(p.get("D_eff", 12)),
            observed=bool(p.get("observed", True)),
            delta_psi=float(p.get("delta_psi", 0.8)),
            delta_theta=float(p.get("delta_theta", 1.0)),
            recent_hits=float(hits),
        )
        return ls.to_dict()

    def pathway(self, text: str) -> Dict[str, Any]:
        r = self._get_reasoner()
        if r is None:
            return {"ok": False, "answer": "pathway reasoner unavailable", "top_domains": []}
        rr = r.reason(text, hops=3)
        return rr.to_dict()

    def translate(self, text: str, domain: Optional[str] = None) -> Dict[str, Any]:
        mode_info = detect_input_mode(text)
        path = self.pathway(text)
        path_dom = None
        if path.get("top_domains"):
            path_dom = path["top_domains"][0].get("domain")
        dom = route_domain(text, domain, pathway_hint=path_dom)

        # Light path: science / modern English — temporarily skip heavy gapfill
        # when translating whole English questions (still map classical extracts).
        prev_gap = getattr(self.pflt, "enable_gapfill", True)
        if mode_info.get("light_gapfill"):
            self.pflt.enable_gapfill = False
        try:
            # For english_meta with classical forms, prefer translating forms only
            surface = text
            if mode_info["mode"] == "english_meta" and mode_info.get("classical_forms"):
                surface = " ".join(mode_info["classical_forms"])
            elif mode_info["mode"] == "science_query":
                # still tokenize for completeness but gapfill off
                surface = text
            out = self.pflt.translate(surface, context=dom, target_lang="english")
        finally:
            self.pflt.enable_gapfill = prev_gap

        # Clean meanings for product display / exact rate
        raw_meanings = list(out.get("meanings") or [])
        tokens = list(out.get("tokens") or [])
        cleaned = clean_meanings(raw_meanings, tokens)
        unresolved_n = sum(1 for m in cleaned if m == "unresolved")
        content_n = max(len(cleaned), 1)
        # Recompute product-facing exact rate (exclude stopword identity noise lightly)
        exact_hits = sum(
            1
            for m, raw in zip(cleaned, raw_meanings)
            if m != "unresolved" and m == (raw.split(" [S=")[0] if raw else "")
            or (m != "unresolved" and not m.startswith("flowing_"))
        )
        # Simpler: tokens not unresolved and not fallback
        resolved = [m for m in cleaned if m != "unresolved"]
        product_map_rate = len(resolved) / content_n if cleaned else 0.0

        law = self.law(dom)
        out["domain_routed"] = dom
        out["fsot_law"] = law
        out["fsot_coherence_S"] = law["S"]
        out["pathway"] = path
        out["input_mode"] = mode_info
        out["meanings_raw"] = raw_meanings
        out["meanings"] = cleaned
        out["meanings_clean"] = cleaned
        out["unresolved_n"] = unresolved_n
        out["product_map_rate"] = product_map_rate
        out["exact_map_rate"] = out.get("exact_map_rate", product_map_rate)
        # Plain relay without fluid S-prefix when English/science mode
        hide_stop = mode_info.get("mode") in {
            "science_query",
            "english_meta",
            "modern_english",
        }
        if mode_info.get("skip_fluid_prefix"):
            out["translation"] = plain_relay(cleaned, hide_stop=hide_stop)
            out["translation_style"] = "plain"
        else:
            out["translation"] = (
                plain_relay(cleaned, hide_stop=False) + " [FSOT 2.1 fluid translation]."
            )
            out["translation_style"] = "classical_plain"
        out["hide_stop"] = hide_stop
        return out

    def _compose_reply(
        self,
        user_text: str,
        tr: Dict[str, Any],
        law: Dict[str, Any],
        prior: List[Dict[str, Any]],
        pathway: Optional[Dict[str, Any]] = None,
        *,
        teach: Optional[Dict[str, Any]] = None,
        densify_lines: Optional[List[str]] = None,
        cert_lines: Optional[List[str]] = None,
    ) -> str:
        mode_info = tr.get("input_mode") or detect_input_mode(user_text)
        mode = mode_info.get("mode", "mixed")
        meanings = list(tr.get("meanings_clean") or tr.get("meanings") or [])
        S = law.get("S", 0)
        auth = "law-backed" if law.get("authority_ok") else "local-scalar-fallback"
        emerge = "emergence" if S > 0 else "damping" if S < 0 else "neutral"
        lines = [
            f"[Protofluid · domain={tr.get('domain_routed')} · mode={mode} · "
            f"S={S:+.6f} · {emerge} · {auth}]",
        ]

        pathway = pathway or tr.get("pathway") or {}
        if pathway.get("top_domains"):
            tops = pathway["top_domains"][:4]
            chain = " → ".join(f"{d.get('domain')}({d.get('p'):.2f})" for d in tops)
            conf = pathway.get("confidence", 0)
            lines.append(f"Pathway: {chain}  [conf={conf:.2f}]")

        session_k = [c for c in prior if c.get("memory_kind") != "archive_memory"]
        archive_k = [c for c in prior if c.get("memory_kind") == "archive_memory"]
        session_k = filter_session_claims(
            dedup_knowledge(session_k, limit=8), limit=4, drop_low_quality=True
        )
        archive_k = dedup_knowledge(archive_k, limit=5)

        hide_stop = bool(tr.get("hide_stop") or mode in {
            "science_query", "english_meta", "modern_english"
        })

        # --- English-meta: teaching panel LEADS (not pH_water) ---
        if mode == "english_meta" and teach and teach.get("ok"):
            lines.extend(format_teach_block(teach))
            if mode_info.get("classical_forms"):
                lines.append(
                    "Classical forms in input: " + ", ".join(mode_info["classical_forms"])
                )
            lines.append(
                f"Surface tokens (secondary): {gloss_line(meanings, hide_stop=True)}"
            )
            # optional water formula only as tertiary if present
            water_bits = [
                c for c in archive_k
                if "water" in (c.get("title") or "").lower()
                or "water" in (c.get("claim_text") or "").lower()
            ]
            if water_bits and any(
                g in (user_text or "").lower() for g in ("water", "aqua")
            ):
                lines.append("Related KB (tertiary):")
                for c in water_bits[:1]:
                    lines.append(f"  · [{c.get('source')}] {(c.get('claim_text') or '')[:140]}")

        elif mode == "science_query" or (
            mode_info.get("archive_first") and mode != "english_meta"
        ):
            sci = science_answer_lines(archive_k)
            if sci:
                lines.append("Answer (FSOT archive — linguistics / KB):")
                lines.extend(sci)
            else:
                lines.append("Answer: (no archive linguistic hit — densify candidate)")
            contentish = [
                m for m in meanings if m not in {"unresolved"} and m not in {
                    "a", "an", "the", "is", "are", "of", "and", "in", "to", "for",
                    "what", "which", "who", "how", "why", "when", "where",
                }
            ]
            if contentish:
                lines.append(
                    f"Surface tokens (secondary): {gloss_line(meanings, hide_stop=True)}"
                )
            else:
                lines.append("Surface gloss: (English science query — archive answer path)")
        else:
            lines.append(f"Surface gloss: {gloss_line(meanings, hide_stop=hide_stop)}")
            relay = tr.get("translation") or plain_relay(meanings, hide_stop=hide_stop)
            if relay and not relay.startswith("(no"):
                lines.append(f"Relay: {relay}")
            if mode == "english_meta" and teach and not teach.get("ok"):
                lines.extend(format_teach_block(teach or {}))

        if session_k:
            lines.append("Related knowledge (session ledger):")
            for c in session_k[:3]:
                ct = c.get("claim_text_display") or (c.get("claim_text") or "")[:160]
                s_val = c.get("S")
                s_bit = f"  (S={s_val:+.4f})" if isinstance(s_val, (int, float)) else ""
                lines.append(f"  · [{c.get('domain')}] {ct}{s_bit}")

        if archive_k and mode not in {"science_query", "english_meta"}:
            lines.append("FSOT archive facts (linguistics / KB — read-only):")
            for c in archive_k[:4]:
                src = c.get("source") or "archive"
                ct = (c.get("claim_text") or "")[:180]
                lines.append(f"  · [{src}] {ct}")
        elif archive_k and mode == "science_query":
            pass  # already in Answer block

        if not session_k and not archive_k and mode != "english_meta":
            lines.append(
                "Related knowledge: (thin — densify candidate for this domain)."
            )

        # Certified math gate
        if cert_lines:
            lines.extend(cert_lines)

        # Observer densify
        if densify_lines:
            lines.extend(densify_lines)

        # Unknown gate notice
        un = int(tr.get("unresolved_n") or 0)
        if un:
            lines.append(
                f"Unknown gate: {un} token(s) unresolved (no invented shell gloss)."
            )

        dkey = tr.get("domain_routed") or ""
        meta = FSOT21_DOMAINS.get(dkey) or {}
        if meta.get("display"):
            lines.append(
                f"FSOT atlas: {meta.get('display')} "
                f"(tier={meta.get('coverage_tier')}, records={meta.get('record_count')})"
            )
        lines.append(
            "Factual base: FSOT 2.1 seed scalar S=K(T1+T2+T3); "
            "language surface is morph/lexicon — law is not rewritten by dialogue."
        )
        return "\n".join(lines)

    def converse(
        self,
        user_text: str,
        *,
        domain: Optional[str] = None,
        store: bool = True,
    ) -> Dict[str, Any]:
        self._turn += 1
        self.history.append(
            ConverseTurn(turn=self._turn, role="user", text=user_text, domain=domain or "")
        )

        tr = self.translate(user_text, domain=domain)
        law = tr["fsot_law"]
        dom = tr["domain_routed"]
        pathway = tr.get("pathway") or {}
        mode_info = tr.get("input_mode") or {}

        # Retrieve: for science, prefer original English query text (not morph junk)
        qblob = user_text
        if mode_info.get("mode") not in {"science_query", "english_meta", "modern_english"}:
            qblob = user_text + " " + " ".join(
                m for m in (tr.get("meanings") or []) if m != "unresolved"
            )
        prior = self.ledger.query_unified(
            qblob, domain=dom, limit=8, session_limit=4, archive_limit=5
        )
        if len(prior) < 3:
            prior2 = self.ledger.query_unified(user_text, limit=5, session_limit=2, archive_limit=4)
            seen = {p.get("id") for p in prior}
            for p in prior2:
                if p.get("id") not in seen:
                    prior.append(p)
        prior = dedup_knowledge(prior, limit=8)

        # Teaching panel (english_meta / latin-greek questions)
        teach = teach_pairs(
            user_text,
            meanings=tr.get("meanings_clean") or tr.get("meanings") or [],
            tokens=tr.get("tokens") or [],
            pul_terms=getattr(self.pflt, "pul_terms", None),
            limit=8,
        )
        # force teach attempt when mode is english_meta even if detector missed lang
        if mode_info.get("mode") == "english_meta" and not teach.get("ok"):
            teach = teach_pairs(
                user_text + " latin",
                meanings=tr.get("meanings_clean") or [],
                tokens=tr.get("tokens") or [],
                lang="la",
                limit=8,
            )

        # Certified numeric gate
        archive_prior = [p for p in prior if p.get("memory_kind") == "archive_memory"]
        cert = certify_turn(
            user_text,
            law=law,
            domain=dom,
            archive_facts=archive_prior,
        )
        cert_lines = format_cert_lines(cert)

        # Observer densify when thin
        stats = self.ledger.stats()
        dom_n = int((stats.get("domains") or {}).get(dom, 0))
        obs = get_observer()
        plan = obs.assess(
            domain=dom,
            mode=str(mode_info.get("mode") or "mixed"),
            unresolved_n=int(tr.get("unresolved_n") or 0),
            token_n=len(tr.get("tokens") or []),
            prior=prior,
            teach_n=int(teach.get("n") or 0),
            product_map_rate=float(tr.get("product_map_rate") or 0),
            ledger_domain_n=dom_n,
        )
        densify_result = obs.execute(
            plan,
            ledger=self.ledger if store else None,
            teach_panel=teach,
            law=law,
            user_text=user_text,
            dry_run=not store,
        )
        densify_lines = obs.format_lines(plan, densify_result)

        reply = self._compose_reply(
            user_text,
            tr,
            law,
            prior,
            pathway=pathway,
            teach=teach,
            densify_lines=densify_lines,
            cert_lines=cert_lines,
        )

        claim_ids: List[str] = []
        if store:
            store_out = dict(tr)
            store_out["meanings"] = tr.get("meanings_clean") or tr.get("meanings")
            # Prefer teach summary in claim when english_meta
            if mode_info.get("mode") == "english_meta" and teach.get("ok"):
                bits = [f"{p['form']}={p['gloss']}" for p in teach["pairs"][:6]]
                store_out["translation"] = "teach: " + ", ".join(bits)
                store_out["meanings"] = [p["gloss"] for p in teach["pairs"][:6]]
            else:
                store_out["translation"] = tr.get("translation") or plain_relay(
                    store_out["meanings"] or []
                )
            claim = claim_from_translate(
                source_text=user_text,
                domain=dom,
                translate_out=store_out,
                law=law,
                session_id=self.session_id,
                turn=self._turn,
            )
            self.ledger.append(claim)
            claim_ids.append(claim.id)

        self.history.append(
            ConverseTurn(
                turn=self._turn,
                role="pflt",
                text=reply,
                domain=dom,
                S=float(law.get("S") or 0),
                meanings=list(tr.get("meanings") or []),
                claim_ids=claim_ids,
                meta={
                    "authority_ok": law.get("authority_ok"),
                    "authority": law.get("authority"),
                    "pathway_conf": pathway.get("confidence"),
                    "mode": mode_info.get("mode"),
                    "unresolved_n": tr.get("unresolved_n"),
                    "teach_n": teach.get("n"),
                    "densify_thin": plan.thin,
                    "cert_ok": cert.ok,
                },
            )
        )

        return {
            "session_id": self.session_id,
            "turn": self._turn,
            "user": user_text,
            "reply": reply,
            "domain": dom,
            "mode": mode_info.get("mode"),
            "input_mode": mode_info,
            "teach": teach,
            "certified_math": cert.to_dict(),
            "densify": densify_result,
            "meanings": tr.get("meanings"),
            "meanings_clean": tr.get("meanings_clean"),
            "tokens": tr.get("tokens"),
            "translation": tr.get("translation"),
            "exact_map_rate": tr.get("exact_map_rate"),
            "product_map_rate": tr.get("product_map_rate"),
            "unresolved_n": tr.get("unresolved_n"),
            "fsot_law": law,
            "pathway": pathway,
            "prior_knowledge": prior,
            "claim_ids": claim_ids,
            "ledger_stats": self.ledger.stats(),
            "law_status": law_status(),
            "product": "Protofluid Language Translator",
            "note": (
                "Converse under FSOT law. Mode-aware surface; archive-first science; "
                "unknown gate; claims append without rewriting law."
            ),
        }

    def status(self) -> Dict[str, Any]:
        arch = {}
        try:
            from fsot_archive_memory import get_archive_memory

            arch = get_archive_memory().status()
        except Exception as e:
            arch = {"error": str(e)}
        r = self._get_reasoner()
        return {
            "product": "Protofluid Language Translator",
            "session_id": self.session_id,
            "turns": self._turn,
            "law": law_status(),
            "ledger": self.ledger.stats(),
            "archive_memory": arch,
            "pathway_nodes": len(r.graph.nodes) if r else 0,
            "domain_count": len(DOMAIN_PARAMS),
            "lexicon_size": len(self.pflt.pul_terms),
            "refinements": [
                "english_mode",
                "archive_first_science",
                "domain_priority",
                "unknown_gate",
                "archive_dedup",
                "english_pass_temple",
                "teach_panel",
                "observer_densify",
                "certified_math",
                "ledger_hygiene",
            ],
        }


def main() -> None:
    ap = argparse.ArgumentParser(description="Protofluid Language Translator — converse")
    ap.add_argument("text", nargs="?", default="", help="Utterance to translate & relay")
    ap.add_argument("--domain", default=None, help="Force FSOT domain context")
    ap.add_argument("--status", action="store_true", help="Print law + ledger status")
    ap.add_argument("--repl", action="store_true", help="Interactive multi-turn loop")
    args = ap.parse_args()

    pt = ProtofluidTranslator()
    if args.status:
        print(json.dumps(pt.status(), indent=2))
        return

    if args.repl:
        print("Protofluid Language Translator — type 'quit' to exit, 'status' for law/ledger")
        print(json.dumps(pt.status(), indent=2))
        while True:
            try:
                line = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line.lower() in {"quit", "exit", "q"}:
                break
            if line.lower() == "status":
                print(json.dumps(pt.status(), indent=2))
                continue
            out = pt.converse(line, domain=args.domain)
            print(out["reply"])
            print()
        return

    if not args.text:
        ap.print_help()
        print("\nLaw status:")
        print(json.dumps(law_status(), indent=2))
        return

    out = pt.converse(args.text, domain=args.domain)
    print(out["reply"])
    print("\n--- json ---")
    dump = {k: v for k, v in out.items() if k != "prior_knowledge"}
    dump["prior_knowledge_n"] = len(out.get("prior_knowledge") or [])
    print(json.dumps(dump, indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
