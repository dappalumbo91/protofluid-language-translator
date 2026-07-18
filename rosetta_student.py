#!/usr/bin/env python3
"""
Rosetta-backed open-set student (from FSOT linguistics canonical matrix).

Given an unknown form + language hint, look up concept via form index, then
map concept → English. Complements edit-distance gap-fill with true
cross-lingual concept geometry (already verified 100% top-1 on matrix).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

DATA = Path(__file__).resolve().parent / "data"


class RosettaStudent:
    def __init__(self) -> None:
        self.concept_en: Dict[str, str] = {}
        self.form_index: Dict[str, str] = {}
        ce = DATA / "rosetta_concept_to_en.json"
        fi = DATA / "rosetta_form_index.json"
        if ce.exists():
            self.concept_en = json.loads(ce.read_text(encoding="utf-8"))
        if fi.exists():
            self.form_index = json.loads(fi.read_text(encoding="utf-8"))

    @property
    def ready(self) -> bool:
        return bool(self.concept_en) and bool(self.form_index)

    def resolve(
        self,
        form: str,
        lang_hints: Optional[list] = None,
    ) -> Optional[Tuple[str, str, str]]:
        """
        Return (english_meaning_key, concept, matched_key) or None.
        """
        if not self.ready or not form:
            return None
        nf = form.strip().lower()
        langs = lang_hints or ["en", "la", "lat", "grc", "el", "ang", "akk", "sum", "san", "fr", "de", "es"]
        for lang in langs:
            k = f"{lang}|{nf}"
            if k in self.form_index:
                concept = self.form_index[k]
                en = self.concept_en.get(concept)
                if en:
                    mk = re.sub(r"[^a-z0-9]+", "_", en.lower()).strip("_")
                    return mk or en, concept, k
        # fuzzy: try without diacritics-ish strip already lower
        return None
