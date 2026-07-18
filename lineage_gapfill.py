#!/usr/bin/env python3
"""
ASJP lineage graph + FSOT-gated gap-fill proposer.

Idea:
  Same meaning parameter across languages → cognate/lineage neighborhood.
  If language A has form for concept C and language B is missing C,
  propose B's form from nearest neighbors (edit-distance / shared family),
  then accept only if FSOT teacher gates pass.

This is NOT free neural MT. Proposals stay Tier B until multi-source promotion.

Inputs:
  D:\\training data\\pflt_linguistics\\02_cognate_lineage\\asjp\\forms.csv
  D:\\training data\\pflt_linguistics\\02_cognate_lineage\\asjp\\languages.csv
  D:\\training data\\pflt_linguistics\\02_cognate_lineage\\asjp\\parameters.csv
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from PFLT_FSOT_2_1_aligned import compute_S_D_chaotic

ASJP = Path(r"D:\training data\pflt_linguistics\02_cognate_lineage\asjp")
OUT = Path(r"D:\training data\pflt_linguistics\09_ml_checkpoints\lineage")
PFLT_OUT = Path(r"C:\Users\damia\Desktop\pflt\data")


def norm_form(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-zʒʃŋɲʧʣʦʰʷː\-~]", "", s)
    return s


def edit_sim(a: str, b: str) -> float:
    """1 - normalized Levenshtein."""
    a, b = norm_form(a), norm_form(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cur = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = cur
    return 1.0 - dp[m] / max(n, m)


@dataclass
class Proposal:
    concept_id: str
    concept_name: str
    target_lang: str
    proposed_form: str
    donor_lang: str
    donor_form: str
    form_similarity: float
    support_neighbors: int
    fsot_S: float
    accepted: bool
    reason: str
    tier: str = "B"


def load_asjp(limit_forms: int = 0) -> Tuple[Dict, Dict, Dict]:
    langs = {}
    with (ASJP / "languages.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lid = row.get("ID") or row.get("Language_ID") or row.get("id")
            if not lid:
                # try first column
                lid = list(row.values())[0]
            langs[lid] = row

    params = {}
    with (ASJP / "parameters.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            pid = row.get("ID") or row.get("Parameter_ID") or list(row.values())[0]
            params[pid] = row

    # forms: Language_ID, Parameter_ID, Form
    by_lang_concept: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    n = 0
    with (ASJP / "forms.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # normalize field names
        for row in reader:
            n += 1
            if limit_forms and n > limit_forms:
                break
            lang = row.get("Language_ID") or row.get("languageReference") or row.get("Lang_ID")
            concept = row.get("Parameter_ID") or row.get("parameterReference") or row.get("Concept_ID")
            form = row.get("Form") or row.get("Value") or row.get("form")
            if not (lang and concept and form):
                # fallback positional
                vals = list(row.values())
                if len(vals) >= 3:
                    lang, concept, form = vals[0], vals[1], vals[2]
                else:
                    continue
            form = str(form).strip()
            if form and form != "XXX":
                by_lang_concept[lang][concept].append(form)
    return langs, params, by_lang_concept


def concept_name(params: Dict, cid: str) -> str:
    row = params.get(cid) or {}
    return row.get("Name") or row.get("Concept") or row.get("English") or cid


def fsot_gate(similarity: float, support: int, domain: str = "historical") -> Tuple[bool, float, str]:
    """
    Teacher gate: combine form evidence with FSOT scalar health.
    Accept provisional Tier B if:
      - form similarity high enough OR enough neighbors
      - scalar finite and not pathological
    """
    from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS

    p = DOMAIN_PARAMS.get(domain, DOMAIN_PARAMS["linguistic"])
    panel = compute_S_D_chaotic(
        D_eff=float(p["D_eff"]),
        observed=bool(p["observed"]),
        delta_psi=float(p["delta_psi"]),
        delta_theta=float(p["delta_theta"]),
    )
    S = panel.S
    if not (S == S) or abs(S) > 1e3:
        return False, S, "scalar_unhealthy"
    # Evidence thresholds (explicit, not free fit of meaning — structural gates)
    if similarity >= 0.75 and support >= 1:
        return True, S, "high_form_similarity"
    if similarity >= 0.55 and support >= 3:
        return True, S, "moderate_sim_multi_neighbor"
    if support >= 5 and similarity >= 0.40:
        return True, S, "strong_neighborhood_vote"
    return False, S, "below_evidence_threshold"


def propose_gaps(
    by_lang_concept: Dict[str, Dict[str, List[str]]],
    params: Dict,
    max_targets: int = 40,
    max_concepts: int = 30,
) -> List[Proposal]:
    """
    For a sample of languages missing concepts that many others have,
    propose forms from best matching donor among languages that share other concepts.
    """
    # concept frequency
    concept_langs: Dict[str, Set[str]] = defaultdict(set)
    for lang, cmap in by_lang_concept.items():
        for c in cmap:
            concept_langs[c].add(lang)

    # popular concepts (ASJP core meanings)
    popular = sorted(concept_langs.keys(), key=lambda c: -len(concept_langs[c]))[:max_concepts]
    langs = list(by_lang_concept.keys())
    # pick target languages with partial coverage
    scored_langs = []
    for lang in langs:
        cov = sum(1 for c in popular if c in by_lang_concept[lang])
        if 5 <= cov <= max(6, len(popular) - 3):
            scored_langs.append((cov, lang))
    scored_langs.sort()
    targets = [L for _, L in scored_langs[:max_targets]]

    proposals: List[Proposal] = []
    for tlang in targets:
        present = set(by_lang_concept[tlang].keys())
        missing = [c for c in popular if c not in present]
        # donors: languages that share many present concepts
        for concept in missing[:8]:
            donors = []
            for dlang, dcmap in by_lang_concept.items():
                if dlang == tlang or concept not in dcmap:
                    continue
                shared = present.intersection(dcmap.keys())
                if len(shared) < 3:
                    continue
                # average form similarity on shared concepts
                sims = []
                for sc in list(shared)[:12]:
                    tf = by_lang_concept[tlang][sc][0]
                    df = dcmap[sc][0]
                    sims.append(edit_sim(tf, df))
                if not sims:
                    continue
                avg = sum(sims) / len(sims)
                donors.append((avg, len(shared), dlang, dcmap[concept][0]))
            if not donors:
                continue
            donors.sort(reverse=True)
            best_sim, support, dlang, dform = donors[0]
            # neighborhood vote: how many top donors agree roughly on form
            near = [d for d in donors[:5] if edit_sim(d[3], dform) >= 0.5]
            support_n = len(near)
            ok, S, reason = fsot_gate(best_sim, support_n)
            proposals.append(
                Proposal(
                    concept_id=concept,
                    concept_name=concept_name(params, concept),
                    target_lang=tlang,
                    proposed_form=dform,
                    donor_lang=dlang,
                    donor_form=dform,
                    form_similarity=round(best_sim, 4),
                    support_neighbors=support_n,
                    fsot_S=round(S, 6),
                    accepted=ok,
                    reason=reason,
                    tier="B" if ok else "reject",
                )
            )
    return proposals


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PFLT_OUT.mkdir(parents=True, exist_ok=True)
    print("Loading ASJP (this can take a minute)...")
    langs, params, by_lc = load_asjp(limit_forms=0)
    print(f"languages_with_forms={len(by_lc)} params={len(params)}")

    props = propose_gaps(by_lc, params)
    accepted = [p for p in props if p.accepted]
    rejected = [p for p in props if not p.accepted]

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_proposals": len(props),
        "n_accepted_tier_B": len(accepted),
        "n_rejected": len(rejected),
        "accept_rate": len(accepted) / max(1, len(props)),
        "policy": {
            "tier_on_accept": "B",
            "promotion_to_A": "requires multi-source or human adjudication",
            "teacher": "FSOT scalar health + form-neighborhood evidence gates",
        },
        "accepted_sample": [asdict(p) for p in accepted[:30]],
        "rejected_sample": [asdict(p) for p in rejected[:15]],
    }
    out_json = OUT / "asjp_lineage_gapfill_report.json"
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (PFLT_OUT / "asjp_lineage_gapfill_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Tier B proposals file for later promotion workflow
    tierb = OUT / "tierB_lineage_proposals.jsonl"
    with tierb.open("w", encoding="utf-8") as f:
        for p in accepted:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")

    print(json.dumps({k: report[k] for k in report if "sample" not in k}, indent=2))
    print("accepted_sample:")
    for p in accepted[:8]:
        print(
            f"  {p.target_lang} missing {p.concept_name}: "
            f"propose '{p.proposed_form}' from {p.donor_lang} "
            f"sim={p.form_similarity} supp={p.support_neighbors} [{p.reason}]"
        )


if __name__ == "__main__":
    main()
