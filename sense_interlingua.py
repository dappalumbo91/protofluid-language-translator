#!/usr/bin/env python3
"""
Sense interlingua — the Protofluid translation spine.

Mission (vision lock):
  PFLT maps *meaning symbols* across languages. Surface forms are labels.
  "aqua" and "water" and "ὕδωρ" and "Wasser" are one sense: SENSE_water.
  A cat is a cat; a cell is a cell. FSOT law frames the act; it is not NMT.

Authority:
  I:\\FSOT-Physical-Archive\\02_FSOT-2.1-Lean-Full\\vendor\\fsot_compute.py
  pin D1D38A — read-only via fsot_law_bridge. No free scalar knobs.

This module does NOT:
  - Fine-tune LLMs / QLoRA / beam-score NMT products
  - Replace S=K(T1+T2+T3) with ad-hoc rankers

This module DOES:
  - Maintain stable sense_id ↔ form(lang) bindings
  - Resolve form → sense → target form (direct meaning)
  - Certify each act with archive-pinned FSOT panel (linguistic D_eff)
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Canonical sense IDs (English head as key; identity is the ID, not the string)
# ---------------------------------------------------------------------------
# Built from core curriculum + multi-lang surface labels. Expand only with
# explicit form↔sense pairs — never free generation.


def _sense_id(gloss: str) -> str:
    g = re.sub(r"[^a-z0-9]+", "_", (gloss or "").strip().lower()).strip("_")
    return f"SENSE_{g}" if g else "SENSE_unknown"


# Extra multi-language labels for universal referents (meaning identity demos).
# Format: sense_gloss_en → {lang: [forms...]}
UNIVERSAL_LABELS: Dict[str, Dict[str, List[str]]] = {
    "water": {
        "en": ["water"],
        "la": ["aqua", "aquae", "aquam", "aquarum"],
        "grc": ["ὕδωρ", "υδωρ"],
        "de": ["wasser", "Wasser"],
        "fr": ["eau"],
        "es": ["agua"],
        "it": ["acqua"],
        "pt": ["água", "agua"],
        "nl": ["water"],
        "sv": ["vatten"],
        "pl": ["woda"],
        "ru": ["вода"],
        "ar": ["ماء"],
        "zh": ["水"],
        "ja": ["水", "みず"],
        "he": ["מים"],
    },
    "cat": {
        "en": ["cat", "cats"],
        "la": ["feles", "felis", "cattus"],
        "grc": ["αἴλουρος", "αιλουρος"],
        "de": ["katze", "Katze", "katzen"],
        "fr": ["chat", "chats", "chatte"],
        "es": ["gato", "gatos"],
        "it": ["gatto", "gatti"],
        "pt": ["gato", "gatos"],
        "nl": ["kat", "katten"],
        "sv": ["katt"],
        "pl": ["kot"],
        "ru": ["кот", "кошка"],
        "zh": ["猫"],
        "ja": ["猫", "ねこ"],
        "ar": ["قط", "قطة"],
    },
    "cell": {
        "en": ["cell", "cells"],
        "la": ["cella"],
        "de": ["zelle", "Zelle"],
        "fr": ["cellule"],
        "es": ["célula", "celula"],
        "it": ["cellula"],
        "pt": ["célula", "celula"],
        "nl": ["cel"],
        "sv": ["cell"],
        "pl": ["komórka", "komorka"],
        "ru": ["клетка"],
        "zh": ["细胞"],
        "ja": ["細胞", "さいぼう"],
    },
    "hand": {
        "en": ["hand", "hands"],
        "la": ["manus", "manum", "manibus"],
        "grc": ["χείρ", "χειρ"],
        "de": ["hand", "Hand", "hände"],
        "fr": ["main", "mains"],
        "es": ["mano", "manos"],
        "it": ["mano", "mani"],
    },
    "sun": {
        "en": ["sun"],
        "la": ["sol", "solem"],
        "grc": ["ἥλιος", "ηλιος"],
        "de": ["sonne", "Sonne"],
        "fr": ["soleil"],
        "es": ["sol"],
        "it": ["sole"],
    },
    "fire": {
        "en": ["fire"],
        "la": ["ignis", "ignem"],
        "grc": ["πῦρ", "πυρ"],
        "de": ["feuer", "Feuer"],
        "fr": ["feu"],
        "es": ["fuego"],
        "it": ["fuoco"],
    },
    "life": {
        "en": ["life"],
        "la": ["vita", "vitam"],
        "grc": ["βίος", "ζωή", "βιος", "ζωη"],
        "de": ["leben", "Leben"],
        "fr": ["vie"],
        "es": ["vida"],
        "it": ["vita"],
    },
    "word": {
        "en": ["word", "words"],
        "la": ["verbum", "verba"],
        "grc": ["λόγος", "λογος"],
        "de": ["wort", "Wort"],
        "fr": ["mot", "mots"],
        "es": ["palabra"],
        "it": ["parola"],
    },
    "language": {
        "en": ["language", "tongue"],
        "la": ["lingua", "linguam"],
        "grc": ["γλῶσσα", "γλωσσα"],
        "de": ["sprache", "Sprache"],
        "fr": ["langue", "langage"],
        "es": ["lengua", "idioma"],
        "it": ["lingua"],
    },
    "house": {
        "en": ["house", "home"],
        "la": ["domus", "casa"],
        "grc": ["οἶκος", "οικος"],
        "de": ["haus", "Haus"],
        "fr": ["maison"],
        "es": ["casa"],
        "it": ["casa"],
    },
    "mountain": {
        "en": ["mountain"],
        "la": ["mons", "montem"],
        "grc": ["ὄρος", "ορος"],
        "de": ["berg", "Berg"],
        "fr": ["montagne"],
        "es": ["montaña", "montana"],
    },
    "day": {
        "en": ["day"],
        "la": ["dies"],
        "grc": ["ἡμέρα", "ημερα"],
        "de": ["tag", "Tag"],
        "fr": ["jour"],
        "es": ["día", "dia"],
    },
    "night": {
        "en": ["night"],
        "la": ["nox", "noctem"],
        "grc": ["νύξ", "νυξ"],
        "de": ["nacht", "Nacht"],
        "fr": ["nuit"],
        "es": ["noche"],
    },
    "year": {
        "en": ["year"],
        "la": ["annus"],
        "grc": ["ἔτος", "ετος"],
        "de": ["jahr", "Jahr"],
        "fr": ["année", "annee", "an"],
        "es": ["año", "ano"],
    },
    "boy": {
        "en": ["boy"],
        "la": ["puer"],
        "de": ["junge", "Junge"],
        "fr": ["garçon", "garcon"],
        "es": ["niño", "nino"],
    },
    "friend": {
        "en": ["friend"],
        "la": ["amicus"],
        "grc": ["φίλος", "φιλος"],
        "de": ["freund", "Freund"],
        "fr": ["ami"],
        "es": ["amigo"],
    },
    "enemy": {
        "en": ["enemy"],
        "la": ["hostis"],
        "grc": ["ἐχθρός", "εχθρος"],
        "de": ["feind", "Feind"],
        "fr": ["ennemi"],
        "es": ["enemigo"],
    },
    "people": {
        "en": ["people"],
        "la": ["populus"],
        "grc": ["λαός", "λαος"],
        "de": ["volk", "Volk"],
        "fr": ["peuple"],
        "es": ["pueblo"],
    },
}


@dataclass
class SenseNode:
    sense_id: str
    canonical_en: str
    forms: Dict[str, List[str]] = field(default_factory=dict)  # lang → forms

    def add_form(self, lang: str, form: str) -> None:
        if not form:
            return
        lang = (lang or "en").lower()
        bucket = self.forms.setdefault(lang, [])
        # preserve first casing for display; index lower separately
        if form not in bucket and form.lower() not in {x.lower() for x in bucket}:
            bucket.append(form)

    def labels(self, lang: str) -> List[str]:
        return list(self.forms.get((lang or "en").lower(), []))

    def primary(self, lang: str) -> Optional[str]:
        labs = self.labels(lang)
        return labs[0] if labs else None


@dataclass
class SenseHit:
    sense_id: str
    canonical_en: str
    source_lang: str
    source_form: str
    method: str  # exact | fold | seed
    confidence: float


@dataclass
class SenseTranslateResult:
    input_text: str
    source_lang: str
    target_lang: str
    tokens: List[str]
    senses: List[Optional[str]]  # sense_id or None
    meanings_en: List[str]
    target_forms: List[str]
    resolution: List[str]
    exact_rate: float
    fsot: Dict[str, Any]
    elapsed_ms: float
    authority_ok: bool
    note: str


class SenseInterlingua:
    """
    Form → sense_id → form. Identity of meaning across languages.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, SenseNode] = {}
        # (lang, folded_form) → sense_id
        self.index: Dict[Tuple[str, str], str] = {}
        # folded_form → sense_id (lang-agnostic fallback when form is unique)
        self.global_form: Dict[str, str] = {}
        self._build()

    @staticmethod
    def fold(s: str) -> str:
        t = (s or "").strip().lower()
        # light classical fold
        t = (
            t.replace("ἀ", "α")
            .replace("ἁ", "α")
            .replace("ά", "α")
            .replace("ὰ", "α")
            .replace("ᾶ", "α")
            .replace("ἐ", "ε")
            .replace("ἑ", "ε")
            .replace("έ", "ε")
            .replace("ὴ", "η")
            .replace("ή", "η")
            .replace("ἰ", "ι")
            .replace("ί", "ι")
            .replace("ῖ", "ι")
            .replace("ὀ", "ο")
            .replace("ό", "ο")
            .replace("ὐ", "υ")
            .replace("ύ", "υ")
            .replace("ῶ", "ω")
            .replace("ώ", "ω")
        )
        return t

    def _ensure(self, gloss_en: str) -> SenseNode:
        sid = _sense_id(gloss_en)
        if sid not in self.nodes:
            self.nodes[sid] = SenseNode(sense_id=sid, canonical_en=gloss_en.strip().lower())
            # always bind English head
            self.nodes[sid].add_form("en", gloss_en.strip().lower())
            self._index_form("en", gloss_en, sid)
        return self.nodes[sid]

    def _index_form(self, lang: str, form: str, sense_id: str) -> None:
        lang = (lang or "en").lower()
        f = self.fold(form)
        if not f:
            return
        self.index[(lang, f)] = sense_id
        # global: only set if empty or same sense (avoid collisions)
        prev = self.global_form.get(f)
        if prev is None or prev == sense_id:
            self.global_form[f] = sense_id

    def bind(self, lang: str, form: str, gloss_en: str) -> str:
        node = self._ensure(gloss_en)
        node.add_form(lang, form)
        self._index_form(lang, form, node.sense_id)
        return node.sense_id

    def _build(self) -> None:
        # 1) core lemma seeds (la/grc → en)
        try:
            from core_lemma_seeds import CORE_SEEDS

            for lang, form, gloss in CORE_SEEDS:
                self.bind(lang, form, gloss)
                self.bind("en", gloss, gloss)
        except Exception:
            pass

        # 2) universal multi-lang labels
        for gloss, by_lang in UNIVERSAL_LABELS.items():
            self._ensure(gloss)
            for lang, forms in by_lang.items():
                for form in forms:
                    self.bind(lang, form, gloss)

        # 3) lang_tables form_sense_prefer (la/en/…)
        try:
            from pathlib import Path
            import json

            tables = Path(__file__).resolve().parent / "data" / "lang_tables"
            if tables.is_dir():
                for p in tables.glob("*.json"):
                    if p.name.startswith("_"):
                        continue
                    data = json.loads(p.read_text(encoding="utf-8"))
                    lang = data.get("lang") or p.stem
                    prefer = data.get("form_sense_prefer") or {}
                    for form, senses in prefer.items():
                        if isinstance(senses, list) and senses:
                            self.bind(lang, form, str(senses[0]))
                    for seed in data.get("seeds") or []:
                        if isinstance(seed, dict) and seed.get("form") and seed.get("gloss"):
                            self.bind(lang, seed["form"], seed["gloss"])
        except Exception:
            pass

        # 4) Curated modern multi-lang core labels (language second brain)
        try:
            from pathlib import Path
            import json

            modern = (
                Path(__file__).resolve().parent
                / "data"
                / "language_brain"
                / "modern_core_labels.json"
            )
            if modern.is_file():
                data = json.loads(modern.read_text(encoding="utf-8"))
                for gloss, by_lang in data.items():
                    if gloss.startswith("_") or not isinstance(by_lang, dict):
                        continue
                    self._ensure(gloss)
                    for lang, forms in by_lang.items():
                        if not isinstance(forms, list):
                            continue
                        for form in forms:
                            self.bind(lang, form, gloss)
        except Exception:
            pass

        # 5) Language second brain extra bindings (gold climb — form↔sense only)
        try:
            from pathlib import Path
            import json

            extra = (
                Path(__file__).resolve().parent
                / "data"
                / "language_brain"
                / "extra_bindings.jsonl"
            )
            if extra.is_file():
                for line in extra.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        b = json.loads(line)
                    except Exception:
                        continue
                    form = (b.get("form") or "").strip()
                    gloss = (b.get("gloss") or "").strip()
                    lang = (b.get("lang") or "unk").strip()
                    if not form or not gloss or " " in form.strip():
                        continue
                    if lang == "en" and form.lower() != gloss.lower():
                        continue
                    self.bind(lang, form, gloss)
        except Exception:
            pass

    def resolve_form(
        self, form: str, source_lang: Optional[str] = None
    ) -> Optional[SenseHit]:
        f = self.fold(form)
        if not f:
            return None
        if source_lang:
            sid = self.index.get((source_lang.lower(), f))
            if sid and sid in self.nodes:
                n = self.nodes[sid]
                return SenseHit(
                    sense_id=sid,
                    canonical_en=n.canonical_en,
                    source_lang=source_lang.lower(),
                    source_form=form,
                    method="exact",
                    confidence=1.0,
                )
        # any-lang exact
        sid = self.global_form.get(f)
        if sid and sid in self.nodes:
            n = self.nodes[sid]
            return SenseHit(
                sense_id=sid,
                canonical_en=n.canonical_en,
                source_lang=source_lang or "?",
                source_form=form,
                method="global",
                confidence=0.95,
            )
        return None

    def render_sense(self, sense_id: str, target_lang: str) -> Optional[str]:
        n = self.nodes.get(sense_id)
        if not n:
            return None
        primary = n.primary(target_lang)
        if primary:
            return primary
        # fallback chain: en → any
        if target_lang != "en":
            primary = n.primary("en")
            if primary:
                return primary
        for lang, forms in n.forms.items():
            if forms:
                return forms[0]
        return n.canonical_en

    def law_panel(self, domain: str = "linguistic") -> Dict[str, Any]:
        """Archive-pinned FSOT panel for the translation act (read-only law)."""
        try:
            from fsot_law_bridge import compute_law_scalar, verify_authority

            auth = verify_authority()
            # Linguistics domain in archive tables often D_eff≈12 (Biology/ling cluster)
            ls = compute_law_scalar(
                domain=domain,
                D_eff=12.0,
                observed=True,
                delta_psi=0.8,
                delta_theta=1.0,
                recent_hits=0.0,
            )
            return {
                "S": ls.S,
                "T1": ls.T1,
                "T2": ls.T2,
                "T3": ls.T3,
                "K": ls.K,
                "D_eff": ls.D_eff,
                "observed": ls.observed,
                "formula": ls.formula,
                "authority": ls.authority,
                "authority_ok": bool(auth.get("ok") and ls.authority_ok),
                "authority_path": auth.get("path"),
                "pin": (auth.get("sha256") or "")[:12] + "…",
            }
        except Exception as e:
            return {"error": str(e), "authority_ok": False}

    def translate(
        self,
        text: str,
        *,
        source_lang: str = "la",
        target_lang: str = "en",
        domain: str = "linguistic",
    ) -> SenseTranslateResult:
        t0 = time.perf_counter()
        # tokenize: whitespace + keep unicode words
        tokens = re.findall(r"\S+", text.strip()) if text.strip() else []
        senses: List[Optional[str]] = []
        meanings: List[str] = []
        targets: List[str] = []
        resolution: List[str] = []
        exact = 0
        for tok in tokens:
            # strip light punctuation
            core = tok.strip(".,;:!?\"'()[]")
            hit = self.resolve_form(core, source_lang)
            if hit is None and source_lang != "en":
                hit = self.resolve_form(core, "en")
            if hit is None:
                hit = self.resolve_form(core, None)
            if hit is not None:
                exact += 1
                senses.append(hit.sense_id)
                meanings.append(hit.canonical_en)
                out = self.render_sense(hit.sense_id, target_lang) or hit.canonical_en
                targets.append(out)
                resolution.append(
                    f"{core} → {hit.sense_id} → {out} [{hit.method}]"
                )
            else:
                senses.append(None)
                meanings.append("unresolved")
                targets.append(core)  # honest: keep form, do not invent
                resolution.append(f"{core} → unresolved (no sense binding)")
        panel = self.law_panel(domain)
        n = len(tokens) or 1
        return SenseTranslateResult(
            input_text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            tokens=tokens,
            senses=senses,
            meanings_en=meanings,
            target_forms=targets,
            resolution=resolution,
            exact_rate=exact / n,
            fsot=panel,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            authority_ok=bool(panel.get("authority_ok")),
            note=(
                "Sense-identity translate: form→SENSE→form under pinned FSOT. "
                "Not NMT. Unresolved forms are not invented."
            ),
        )

    def stats(self) -> Dict[str, Any]:
        langs = set()
        n_forms = 0
        for n in self.nodes.values():
            for lang, forms in n.forms.items():
                langs.add(lang)
                n_forms += len(forms)
        return {
            "n_senses": len(self.nodes),
            "n_form_bindings": n_forms,
            "n_index_keys": len(self.index),
            "langs": sorted(langs),
        }


def smoke_identity() -> Dict[str, Any]:
    """Fast battery: aqua/water/cat/cell identity across languages. Seconds, not hours."""
    ix = SenseInterlingua()
    cases = [
        ("aqua", "la", "en", "water"),
        ("water", "en", "la", "aqua"),
        ("ὕδωρ", "grc", "en", "water"),
        ("Wasser", "de", "en", "water"),
        ("eau", "fr", "en", "water"),
        ("cat", "en", "de", "katze"),
        ("Katze", "de", "en", "cat"),
        ("cell", "en", "de", "zelle"),
        ("manus", "la", "en", "hand"),
        ("aqua lingua manus", "la", "en", "water language hand"),
    ]
    results = []
    ok = 0
    for form, src, tgt, expect in cases:
        r = ix.translate(form, source_lang=src, target_lang=tgt)
        got = " ".join(r.target_forms).lower()
        exp = expect.lower()
        # multi-token: check all expected words present as sense renders
        if " " in exp:
            hit = all(w in got for w in exp.split())
        else:
            hit = exp in got or got == exp
        ok += int(hit)
        results.append(
            {
                "in": form,
                "src": src,
                "tgt": tgt,
                "expect": expect,
                "got": got,
                "ok": hit,
                "ms": r.elapsed_ms,
                "S": r.fsot.get("S"),
            }
        )
    panel = ix.law_panel()
    return {
        "passed": ok,
        "total": len(cases),
        "pct": round(100 * ok / len(cases), 1),
        "authority_ok": panel.get("authority_ok"),
        "S_linguistic": panel.get("S"),
        "stats": ix.stats(),
        "cases": results,
        "note": "sense identity battery — must stay near-instant",
    }


if __name__ == "__main__":
    import json

    out = smoke_identity()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"\n{out['passed']}/{out['total']} ({out['pct']}%) authority_ok={out['authority_ok']}")
