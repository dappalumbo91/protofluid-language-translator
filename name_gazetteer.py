#!/usr/bin/env python3
"""
Historical name / place gazetteer for PFLT.

Why names break open-set morphology
------------------------------------
Common words are *types* with paradigms (aqua → aquam → aquarum).
Proper names are mostly *tokens* of unique entities. They:
  - rarely share meaning with orthographic neighbors (Abdera ≉ abdere)
  - use different morphology per language (demonyms -anus/-ensis vs -της/-εύς)
  - carry wiki-style glosses, not short interlingua keys
  - need gazetteers + historical contact maps, not edit-distance gap-fill

Standard practice (NER / digital classics)
------------------------------------------
  1) Closed entity table (gazetteer): form → entity id / English title
  2) Script normalize + transliterate, then lookup
  3) Cross-language historical contacts (Ἀθῆναι = Athenae = Athens)
  4) Demonym peel → place entity
  5) Pass-through / "unknown_entity" when absent — do not invent via MT

This module builds (1–4) from Dictionary pos=name + place glosses, without LLM.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

DATA = Path(__file__).resolve().parent / "data"
DB = Path(r"C:\Users\damia\Desktop\Dictionary\data\dictionary.db")
OUT = DATA / "name_gazetteer.json"
DRIVE = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\name_gazetteer.json")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def grc_to_latin(s: str) -> str:
    f = fold(s)
    for src, dst in (
        ("θ", "th"), ("φ", "ph"), ("χ", "ch"), ("ψ", "ps"), ("ξ", "x"),
        ("η", "e"), ("ω", "o"), ("υ", "y"), ("β", "b"), ("γ", "g"),
        ("δ", "d"), ("ζ", "z"), ("κ", "k"), ("λ", "l"), ("μ", "m"),
        ("ν", "n"), ("π", "p"), ("ρ", "r"), ("σ", "s"), ("ς", "s"),
        ("τ", "t"), ("α", "a"), ("ε", "e"), ("ι", "i"), ("ο", "o"),
    ):
        f = f.replace(src, dst)
    return re.sub(r"[^a-z]", "", f)


def clean_name_gloss(gloss: str) -> Tuple[str, str]:
    """
    Return (short_english_title, kind).
    kind in {person, place, river, ethnonym, month, other, meta}.
    """
    g = (gloss or "").strip()
    g = re.sub(r"\{\{[^}]+\}\}", "", g)
    g = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", g)
    g = g.split(";")[0].split("\n")[0].strip(" .,;")
    low = g.lower()

    if re.match(
        r"^(nominative|genitive|dative|ablative|vocative|singular|plural|"
        r"alternative form|initialism|misspelling)\b",
        low,
    ):
        return "", "meta"

    # Pull leading proper title before parenthesis
    m = re.match(r"^([A-Za-zĀ-ſ\u0370-\u03ff\u1f00-\u1fff][^()]{0,40}?)(?:\s*\(|$)", g)
    title = (m.group(1) if m else g).strip(" ,.-")
    # Prefer English-looking short title
    if len(title.split()) > 5:
        title = " ".join(title.split()[:4])

    kind = "other"
    if re.search(r"\b(river|fluvius|stream)\b", low):
        kind = "river"
    elif re.search(r"\b(city|town|island|region|province|kingdom|sea|mountain|country)\b", low):
        kind = "place"
    elif re.search(r"\b(inhabitant|people of|tribe|nation|demonym)\b", low):
        kind = "ethnonym"
    elif re.search(r"\b(month|december|january)\b", low) or title.lower() in {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    }:
        kind = "month"
    elif re.search(r"\b(god|goddess|king|emperor|person|hero|saint)\b", low):
        kind = "person"
    elif re.match(r"^[A-Z]", title) and len(title.split()) <= 3:
        kind = "place" if any(x in low for x in ("city", "island", "ancient")) else "person"

    # Normalize to meaning_key-ish
    mk = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    # strip article wrappers from key
    mk = re.sub(r"^(a|an|the)_", "", mk)
    return mk or title.lower(), kind


# Demonym endings → peel to place stem
_DEMONYM = (
    "ιώτης", "ιώτου", "ίτης", "ίτου", "εύς", "έως", "αίος", "αῖος",
    "ensis", "enses", "anus", "ana", "ani", "anum", "icus", "ica", "icum",
    "ites", "itae", "iotai",
)

# Classical historical contact seeds (curriculum — not eval leakage)
_SEED_PERSONS = {
    "zeus", "apollo", "poseidon", "hades", "hera", "athena", "aphrodite",
    "ares", "hermes", "artemis", "dionysus", "hercules", "odysseus",
    "achilles", "homeros", "plato", "aristotle", "socrates", "alexander", "caesar",
}
_SEED_CONTACTS = [
    ("athens", [("grc", "ἀθῆναι"), ("grc", "αθηναι"), ("la", "athenae"), ("en", "athens")]),
    ("rome", [("la", "roma"), ("grc", "ῥώμη"), ("grc", "ρωμη"), ("en", "rome")]),
    ("egypt", [("la", "aegyptus"), ("grc", "αἴγυπτος"), ("grc", "αιγυπτος"), ("en", "egypt")]),
    ("sparta", [("la", "sparta"), ("grc", "σπάρτη"), ("grc", "σπαρτη"), ("en", "sparta")]),
    ("troy", [("la", "troia"), ("grc", "τροία"), ("grc", "τροια"), ("en", "troy")]),
    ("carthage", [("la", "carthago"), ("grc", "καρχηδών"), ("en", "carthage")]),
    ("jerusalem", [("la", "hierosolyma"), ("grc", "ἱερουσαλήμ"), ("en", "jerusalem")]),
    ("babylon", [("la", "babylon"), ("grc", "βαβυλών"), ("en", "babylon")]),
    ("persepolis", [("la", "persepolis"), ("grc", "περσέπολις"), ("en", "persepolis")]),
    ("alexandria", [("la", "alexandria"), ("grc", "ἀλεξάνδρεια"), ("en", "alexandria")]),
    ("zeus", [("grc", "ζεύς"), ("grc", "ζευς"), ("la", "iuppiter"), ("la", "jupiter"), ("en", "zeus")]),
    ("apollo", [("grc", "ἀπόλλων"), ("la", "apollo"), ("en", "apollo")]),
    ("poseidon", [("grc", "ποσειδῶν"), ("la", "neptunus"), ("en", "poseidon")]),
    ("hades", [("grc", "ᾅδης"), ("la", "pluto"), ("en", "hades")]),
    ("hera", [("grc", "ἥρα"), ("la", "iuno"), ("en", "hera")]),
    ("athena", [("grc", "ἀθηνᾶ"), ("la", "minerva"), ("en", "athena")]),
    ("aphrodite", [("grc", "ἀφροδίτη"), ("la", "venus"), ("en", "aphrodite")]),
    ("ares", [("grc", "ἄρης"), ("la", "mars"), ("en", "ares")]),
    ("hermes", [("grc", "ἑρμῆς"), ("la", "mercurius"), ("en", "hermes")]),
    ("artemis", [("grc", "ἄρτεμις"), ("la", "diana"), ("en", "artemis")]),
    ("dionysus", [("grc", "διόνυσος"), ("la", "bacchus"), ("en", "dionysus")]),
    ("hercules", [("la", "hercules"), ("grc", "ἡρακλῆς"), ("en", "heracles")]),
    ("odysseus", [("grc", "ὀδυσσεύς"), ("la", "ulixes"), ("en", "odysseus")]),
    ("achilles", [("grc", "ἀχιλλεύς"), ("la", "achilles"), ("en", "achilles")]),
    ("homeros", [("grc", "ὅμηρος"), ("la", "homerus"), ("en", "homer")]),
    ("plato", [("grc", "πλάτων"), ("la", "plato"), ("en", "plato")]),
    ("aristotle", [("grc", "ἀριστοτέλης"), ("la", "aristoteles"), ("en", "aristotle")]),
    ("socrates", [("grc", "σωκράτης"), ("la", "socrates"), ("en", "socrates")]),
    ("alexander", [("grc", "ἀλέξανδρος"), ("la", "alexander"), ("en", "alexander")]),
    ("caesar", [("la", "caesar"), ("grc", "καῖσαρ"), ("en", "caesar")]),
    ("nile", [("la", "nilus"), ("grc", "νεῖλος"), ("en", "nile")]),
    ("danube", [("la", "danubius"), ("grc", "ἴστρος"), ("en", "danube")]),
    ("mediterranean", [("la", "mare nostrum"), ("en", "mediterranean")]),
    ("aegean", [("la", "aegaeum"), ("grc", "αἰγαῖον"), ("en", "aegean")]),
    ("crete", [("la", "creta"), ("grc", "κρήτη"), ("en", "crete")]),
    ("cyprus", [("la", "cyprus"), ("grc", "κύπρος"), ("en", "cyprus")]),
    ("sicily", [("la", "sicilia"), ("grc", "σικελία"), ("en", "sicily")]),
    ("macedonia", [("la", "macedonia"), ("grc", "μακεδονία"), ("en", "macedonia")]),
    ("thrace", [("la", "thracia"), ("grc", "θρᾴκη"), ("en", "thrace")]),
    ("persia", [("la", "persia"), ("grc", "περσίς"), ("en", "persia")]),
]


@dataclass
class NameHit:
    meaning: str
    kind: str
    method: str
    score: float
    donor: str


class NameGazetteer:
    def __init__(self, path: Optional[Path] = None, *, load: bool = True) -> None:
        self.by_form: Dict[str, str] = {}          # folded form → meaning
        self.by_lang_form: Dict[str, str] = {}      # lang|fold → meaning
        self.by_title: Dict[str, List[str]] = defaultdict(list)  # meaning → forms
        self.kind: Dict[str, str] = {}              # meaning → kind
        self.translit: Dict[str, str] = {}          # latinized greek → meaning
        if load:
            path = path or OUT
            if path.exists():
                self.load(path)

    def load(self, path: Path) -> None:
        blob = json.loads(path.read_text(encoding="utf-8"))
        self.by_form = blob.get("by_form") or {}
        self.by_lang_form = blob.get("by_lang_form") or {}
        self.by_title = {k: list(v) for k, v in (blob.get("by_title") or {}).items()}
        self.kind = blob.get("kind") or {}
        self.translit = blob.get("translit") or {}

    def add_form(self, form: str, meaning: str, lang: str = "", kind: str = "other") -> None:
        if not form or not meaning:
            return
        nf = fold(form)
        mk = re.sub(r"[^a-z0-9]+", "_", meaning.lower()).strip("_") or meaning.lower()
        self.by_form[nf] = mk
        if lang:
            self.by_lang_form[f"{lang}|{nf}"] = mk
            self.by_title[mk].append(f"{lang}|{nf}")
        else:
            self.by_title[mk].append(nf)
        self.kind.setdefault(mk, kind)
        self.by_form.setdefault(mk, mk)
        if re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", form) or (lang in {"grc", "el"}):
            lat = grc_to_latin(form)
            if len(lat) >= 3:
                self.translit.setdefault(lat, mk)
                self.by_form.setdefault(lat, mk)

    def apply_seed_contacts(self) -> int:
        """Classical historical contact seeds (not train leakage — fixed curriculum)."""
        n = 0
        for title, pairs in _SEED_CONTACTS:
            kind = "person" if title in _SEED_PERSONS else "place"
            self.kind.setdefault(title, kind)
            self.by_form[title] = title
            for lang, form in pairs:
                self.add_form(form, title, lang=lang, kind=kind)
                n += 1
        return n

    @classmethod
    def from_gold_rows(
        cls,
        rows: List[Any],
        *,
        include_seeds: bool = True,
        names_only: bool = True,
        include_pleiades: bool = True,
    ) -> "NameGazetteer":
        """
        Build gazetteer from train rows only (honest open-set).
        Production path continues to use full dictionary JSON on disk.
        Pleiades contacts (external curriculum) may be merged for historical aliases.
        """
        g = cls(load=False)
        for r in rows:
            is_n = bool(r.get("is_name"))
            st = r.get("source_title") or ""
            tw = r.get("target_word") or ""
            if names_only and not is_n:
                if "names_places" not in st and not re.search(
                    r"\b(city|river|island|kingdom|inhabitant|people of)\b",
                    tw,
                    re.I,
                ):
                    continue
            mk, kind = clean_name_gloss(tw or r.get("meaning_key") or "")
            if not mk or kind == "meta":
                mk = re.sub(
                    r"[^a-z0-9]+", "_", (r.get("meaning_key") or tw).lower()
                ).strip("_")
                kind = "other"
            if not mk:
                continue
            g.add_form(
                r.get("source_word") or "",
                mk,
                lang=(r.get("source_lang") or "").lower(),
                kind=kind,
            )
        if include_seeds:
            g.apply_seed_contacts()
        if include_pleiades:
            g.merge_pleiades_contacts()
        return g

    def merge_pleiades_contacts(self, path: Optional[Path] = None) -> int:
        """Merge external Pleiades multi-form contacts (curriculum gazetteer)."""
        path = path or (DATA / "pleiades_contacts.json")
        if not path.exists():
            alt = Path(r"D:\training data\pflt_linguistics\08_rosetta_fsot\pleiades_contacts.json")
            path = alt if alt.exists() else path
        if not path.exists():
            return 0
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return 0
        n = 0
        for k, title in (blob.get("by_lang_form") or {}).items():
            if "|" not in k:
                continue
            lang, form = k.split("|", 1)
            self.add_form(form, title, lang=lang, kind="place")
            n += 1
        for form, title in (blob.get("by_form") or {}).items():
            self.by_form.setdefault(fold(form), title)
            self.kind.setdefault(title, "place")
        return n

    @property
    def ready(self) -> bool:
        return bool(self.by_form) or bool(self.by_lang_form)

    def resolve(self, form: str, lang: str = "la") -> Optional[NameHit]:
        if not form or not self.ready:
            return None
        nf = fold(form)
        lang = (lang or "la").lower()
        if lang == "lat":
            lang = "la"

        # 1) exact lang-qualified
        k = f"{lang}|{nf}"
        if k in self.by_lang_form:
            m = self.by_lang_form[k]
            return NameHit(m, self.kind.get(m, "other"), "name_lang_exact", 0.98, k)

        # 2) any-lang form
        if nf in self.by_form:
            m = self.by_form[nf]
            return NameHit(m, self.kind.get(m, "other"), "name_form_exact", 0.95, nf)

        # 3) greek transliteration bridge
        if lang in {"grc", "el"} or re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", form):
            lat = grc_to_latin(form)
            if lat in self.translit:
                m = self.translit[lat]
                return NameHit(m, self.kind.get(m, "other"), "name_translit", 0.90, lat)
            if lat in self.by_form:
                m = self.by_form[lat]
                return NameHit(m, self.kind.get(m, "other"), "name_translit_form", 0.88, lat)

        # 4) demonym peel → place title already in gazetteer
        for suf in sorted(_DEMONYM, key=len, reverse=True):
            sf = fold(suf)
            if nf.endswith(sf) and len(nf) - len(sf) >= 3:
                stem = nf[: -len(sf)]
                # probe stem as place
                for cand in (stem, stem + "a", stem + "os", stem + "us", stem + "on", stem + "um"):
                    if cand in self.by_form:
                        m = self.by_form[cand]
                        return NameHit(m, "ethnonym", "name_demonym_peel", 0.84, cand)
                    kk = f"{lang}|{cand}"
                    if kk in self.by_lang_form:
                        m = self.by_lang_form[kk]
                        return NameHit(m, "ethnonym", "name_demonym_peel", 0.84, cand)
                # translit stem for greek
                if lang in {"grc", "el"}:
                    lat = grc_to_latin(stem)
                    if lat in self.by_form or lat in self.translit:
                        m = self.by_form.get(lat) or self.translit.get(lat)
                        if m:
                            return NameHit(m, "ethnonym", "name_demonym_translit", 0.82, lat)

        # 5) historical contact: form's translit matches an English title key
        lat = grc_to_latin(form) if re.search(r"[\u0370-\u03ff]", form) else nf
        if lat and lat in self.by_title:
            # by_title maps meaning→forms; reverse: title string as form of itself
            pass
        if lat and lat in self.by_form:
            m = self.by_form[lat]
            return NameHit(m, self.kind.get(m, "other"), "name_contact_title", 0.80, lat)

        return None


def build_from_dictionary(db: Path = DB, max_per_lang: int = 12000) -> Dict:
    """Mine pos=name + place-pattern glosses into a clean gazetteer."""
    if not db.exists():
        raise FileNotFoundError(db)
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    by_form: Dict[str, str] = {}
    by_lang_form: Dict[str, str] = {}
    by_title: Dict[str, List[str]] = defaultdict(list)
    kind_map: Dict[str, str] = {}
    translit: Dict[str, str] = {}
    stats: Dict[str, int] = defaultdict(int)

    for lang in ("la", "grc", "ang", "en"):
        rows = cur.execute(
            """
            SELECT w.word, w.pos, d.gloss
            FROM words w
            JOIN definitions d ON d.word_id = w.id
            WHERE w.lang_code = ?
              AND d.gloss_lang = 'en'
              AND (
                w.pos = 'name' OR w.pos LIKE '%name%'
                OR d.gloss LIKE '%city%' OR d.gloss LIKE '%river%'
                OR d.gloss LIKE '%island%' OR d.gloss LIKE '%kingdom%'
                OR d.gloss LIKE '%ancient %' OR d.gloss LIKE '%inhabitant%'
              )
              AND length(w.word) BETWEEN 2 AND 45
              AND length(d.gloss) BETWEEN 2 AND 120
            LIMIT ?
            """,
            (lang, max_per_lang * 4),
        ).fetchall()

        best: Dict[str, Tuple[float, str, str]] = {}  # fold → (score, meaning, kind)
        for word, pos, gloss in rows:
            mk, kind = clean_name_gloss(gloss or "")
            if not mk or kind == "meta" or len(mk) < 2:
                stats["skipped_meta"] += 1
                continue
            score = 1.0
            if (pos or "").lower() in {"name", "proper"}:
                score += 0.6
            if kind in {"place", "river", "person", "month"}:
                score += 0.3
            if len(mk) <= 24:
                score += 0.2
            nf = fold(word)
            prev = best.get(nf)
            if prev is None or score > prev[0]:
                best[nf] = (score, mk, kind)

        # take top
        items = sorted(best.items(), key=lambda kv: -kv[1][0])[:max_per_lang]
        for nf, (sc, mk, kind) in items:
            by_form[nf] = mk
            by_lang_form[f"{lang}|{nf}"] = mk
            by_title[mk].append(f"{lang}|{nf}")
            kind_map[mk] = kind
            # historical contact: English title as lookup form
            by_form.setdefault(mk, mk)
            by_form.setdefault(mk.replace("_", ""), mk)
            if lang in {"grc", "el"} or re.search(r"[\u0370-\u03ff]", nf):
                # nf may already be folded greek letters
                pass
            stats[f"n_{lang}"] = stats.get(f"n_{lang}", 0) + 1

        # translit map for greek source words
        if lang == "grc":
            for word, pos, gloss in rows:
                mk, kind = clean_name_gloss(gloss or "")
                if not mk or kind == "meta":
                    continue
                lat = grc_to_latin(word)
                if len(lat) >= 3:
                    translit.setdefault(lat, mk)
                    by_form.setdefault(lat, mk)

    conn.close()

    # Enrich contacts from Rosetta form index when EN title matches
    rosetta_fi = DATA / "rosetta_form_index.json"
    rosetta_ce = DATA / "rosetta_concept_to_en.json"
    if rosetta_fi.exists() and rosetta_ce.exists():
        try:
            fi = json.loads(rosetta_fi.read_text(encoding="utf-8"))
            ce = json.loads(rosetta_ce.read_text(encoding="utf-8"))
            for k, concept in fi.items():
                if "|" not in k:
                    continue
                lang, form = k.split("|", 1)
                en = ce.get(concept) or ""
                mk, kind = clean_name_gloss(en)
                if not mk or kind == "meta":
                    mk = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")
                if not mk or len(mk) < 2:
                    continue
                nf = fold(form)
                by_form.setdefault(nf, mk)
                by_lang_form.setdefault(f"{lang}|{nf}", mk)
                by_title[mk].append(f"{lang}|{nf}")
                kind_map.setdefault(mk, kind if kind != "meta" else "other")
                if lang in {"grc", "el"} or re.search(r"[\u0370-\u03ff]", form):
                    lat = grc_to_latin(form)
                    if len(lat) >= 3:
                        translit.setdefault(lat, mk)
                        by_form.setdefault(lat, mk)
                stats["rosetta_name_links"] = stats.get("rosetta_name_links", 0) + 1
        except Exception:
            stats["rosetta_enrich_error"] = 1

    # Apply shared classical seed graph
    gtmp = NameGazetteer(load=False)
    gtmp.by_form = by_form
    gtmp.by_lang_form = by_lang_form
    gtmp.by_title = by_title
    gtmp.kind = kind_map
    gtmp.translit = translit
    stats["seed_contacts"] = gtmp.apply_seed_contacts()
    by_form, by_lang_form = gtmp.by_form, gtmp.by_lang_form
    by_title, kind_map, translit = gtmp.by_title, gtmp.kind, gtmp.translit

    # Historical contacts: forms sharing same English title link as one entity
    contacts = {t: forms[:20] for t, forms in by_title.items() if len(forms) >= 2}
    stats["n_forms"] = len(by_form)
    stats["n_titles"] = len(by_title)
    stats["n_contacts_multi"] = len(contacts)
    stats["n_translit"] = len(translit)

    blob = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "Gazetteer-first for proper names; morphology gap-fill is for common vocabulary. "
            "Historical contacts = multiple language forms → same English title "
            "(Dictionary + Rosetta + classical seed graph)."
        ),
        "by_form": by_form,
        "by_lang_form": by_lang_form,
        "by_title": {k: v for k, v in list(by_title.items())[:50000]},
        "kind": kind_map,
        "translit": translit,
        "contacts_sample": dict(list(contacts.items())[:40]),
        "stats": dict(stats),
    }
    OUT.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    DRIVE.parent.mkdir(parents=True, exist_ok=True)
    DRIVE.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    return blob


def main() -> None:
    blob = build_from_dictionary()
    print("stats", blob["stats"])
    print("contacts sample", list(blob.get("contacts_sample", {}).items())[:8])
    g = NameGazetteer()
    for form, lang in (
        ("Κύπρος", "grc"),
        ("Lesbos", "en"),
        ("Λέσβος", "grc"),
        ("Zeus", "en"),
        ("Ζεύς", "grc"),
        ("Roma", "la"),
        ("Abdera", "la"),
    ):
        print(form, lang, g.resolve(form, lang))


if __name__ == "__main__":
    main()
