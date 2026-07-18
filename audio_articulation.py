#!/usr/bin/env python3
"""
Articulation layer for PFLT multimodal AI — IPA / phonology / FSOT proxies.

Waveform synthesis is intentionally NOT the target (suboptimal for this stack).
We articulate via:
  - IPA strings (lexicon / G2P)
  - articulatory feature vectors derived from IPA (place/manner/voice)
  - FSOT S → tempo_proxy + energy_proxy (seed scalar, not free TTS knobs)

Optional later: *link* to external clips if present — never require waveforms.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from PFLT_FSOT_2_1_aligned import DOMAIN_PARAMS, compute_S_D_chaotic

PHOIBLE = Path(
    r"D:\training data\pflt_linguistics\05_phonology_vocal\phoible\phoible.csv"
)
OUT = Path(r"D:\training data\pflt_linguistics\05_phonology_vocal")
PFLT_DATA = Path(r"C:\Users\damia\Desktop\pflt\data")

STARTER_G2P: Dict[str, Dict[str, str]] = {
    "en": {
        "water": "ˈwɔːtər",
        "language": "ˈlæŋɡwɪdʒ",
        "law": "lɔː",
        "king": "kɪŋ",
        "sun": "sʌn",
        "life": "laɪf",
        "start": "stɑːrt",
        "stop": "stɒp",
        "energy": "ˈɛnərdʒi",
        "structure": "ˈstrʌktʃər",
        "transfer": "ˈtrænsfər",
        "action": "ˈækʃən",
        "human": "ˈhjuːmən",
        "sky": "skaɪ",
        "earth": "ɜːrθ",
        "flow": "floʊ",
        "field": "fiːld",
    },
    "la": {
        "aqua": "ˈa.kʷa",
        "lingua": "ˈlin.ɡwa",
        "ius": "juːs",
        "rex": "rɛks",
        "lux": "luːks",
    },
    "es": {
        "agua": "ˈa.ɣwa",
        "lengua": "ˈlen.ɡwa",
        "ley": "lej",
        "rey": "rej",
        "sol": "sol",
    },
    "fr": {
        "eau": "o",
        "langue": "lɑ̃ɡ",
        "loi": "lwa",
        "roi": "ʁwa",
        "soleil": "sɔ.lɛj",
    },
    "de": {
        "wasser": "ˈvasɐ",
        "sprache": "ˈʃpʁaːxə",
        "gesetz": "ɡəˈzɛts",
        "könig": "ˈkøːnɪç",
    },
}


# Rough IPA feature tags (articulatory — not waveform)
def ipa_features(ipa: str) -> Dict[str, float]:
    if not ipa:
        return {"voicing": 0.0, "nasality": 0.0, "frontness": 0.5, "openness": 0.5, "length": 0.0}
    s = ipa
    return {
        "voicing": 1.0 if re.search(r"[bdɡzvðʒmnŋlrwjaeiouɑɔɛɪʊəæ]", s) else 0.3,
        "nasality": 1.0 if re.search(r"[mnŋãẽĩõũ]", s) else 0.0,
        "frontness": 0.8 if re.search(r"[iɪeɛæyø]", s) else (0.2 if re.search(r"[uʊoɔɑ]", s) else 0.5),
        "openness": 0.8 if re.search(r"[aɑæɔ]", s) else (0.2 if re.search(r"[iuɪʊ]", s) else 0.5),
        "length": 1.0 if "ː" in s or ":" in s else 0.0,
        "stress": 1.0 if "ˈ" in s or "ˌ" in s else 0.0,
        "n_segments": float(len(re.findall(r"[^\sˈˌ\.ː͡]", s))),
    }


@dataclass
class Articulation:
    text: str
    lang: str
    ipa: Optional[str]
    features: Dict[str, float] = field(default_factory=dict)
    phoneme_notes: List[str] = field(default_factory=list)
    fsot_S: float = 0.0
    tempo_proxy: float = 1.0
    energy_proxy: float = 1.0
    source: str = "missing"
    tier: str = "C"
    representation: str = "ipa_articulatory_fsot_waveform"
    waveform_path: Optional[str] = None
    waveform_engine: Optional[str] = None


_DICT_IPA: Optional[Dict[str, str]] = None


def _load_dictionary_ipa() -> Dict[str, str]:
    global _DICT_IPA
    if _DICT_IPA is not None:
        return _DICT_IPA
    paths = [
        Path(r"C:\Users\damia\Desktop\pflt\data\dictionary_ipa_lexicon.json"),
        Path(r"D:\training data\pflt_linguistics\05_phonology_vocal\dictionary_ipa_lexicon.json"),
    ]
    for p in paths:
        if p.exists():
            try:
                _DICT_IPA = json.loads(p.read_text(encoding="utf-8"))
                return _DICT_IPA
            except Exception:
                pass
    _DICT_IPA = {}
    return _DICT_IPA


def articulate(
    text: str,
    lang: str = "en",
    context: str = "linguistic",
    *,
    write_waveform: bool = True,
    wav_dir: Optional[Path] = None,
) -> Articulation:
    word = text.strip().split()[0] if text.strip() else ""
    key = word.lower()
    g2p = STARTER_G2P.get(lang, {})
    ipa = g2p.get(key)
    notes: List[str] = []
    # Dictionary-mined IPA (Desktop Dictionary pronunciations)
    if not ipa:
        dipa = _load_dictionary_ipa()
        ipa = dipa.get(f"{lang}|{key}") or dipa.get(key)
        if ipa:
            notes.append("dictionary_ipa")
    if ipa and "dictionary_ipa" in notes:
        source, tier = "dictionary_db", "A"
    elif ipa:
        source, tier = "starter_g2p", "B"
        notes.append("lexicon_ipa")
    else:
        # letter→rough IPA fallback for Latin alphabet only (honest low tier)
        if re.fullmatch(r"[a-zA-Z]+", word):
            ipa = "".join(c for c in key)
            source, tier = "orthographic_fallback", "C"
            notes.append("orthographic_fallback_not_true_ipa")
        else:
            ipa = None
            source, tier = "missing", "C"
            notes.append("no_g2p_entry")

    p = DOMAIN_PARAMS.get(context, DOMAIN_PARAMS.get("linguistic", {
        "D_eff": 12, "observed": True, "delta_psi": 0.8, "delta_theta": 1.0
    }))
    panel = compute_S_D_chaotic(
        D_eff=float(p["D_eff"]),
        observed=bool(p["observed"]),
        delta_psi=float(p.get("delta_psi", 0.8)),
        delta_theta=float(p.get("delta_theta", 1.0)),
    )
    S = float(panel.S)
    energy = max(0.2, min(1.5, 0.6 + abs(S) * 0.4))
    tempo = max(0.5, min(1.5, 0.9 + (0.2 if S > 0 else -0.15)))
    feats = ipa_features(ipa or "")
    feats["fsot_energy"] = energy
    feats["fsot_tempo"] = tempo

    wav_path = None
    wav_engine = None
    if write_waveform and word:
        try:
            from waveform_synth import synthesize_waveform

            out_dir = wav_dir or Path(
                r"D:\training data\pflt_linguistics\05_phonology_vocal\waveforms"
            )
            # Keep ASCII-safe filenames; transliterate Greek so paths aren't grc__.wav
            try:
                from open_set_boost import grc_to_latin

                key_safe = grc_to_latin(key) if re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", key) else key
            except Exception:
                key_safe = key
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", f"{lang}_{key_safe}")[:60] or f"{lang}_tok"
            dest = out_dir / f"{safe}.wav"
            # SAPI speaks surface English/Latin better than IPA symbols
            speak_text = word if re.fullmatch(r"[A-Za-z\-']+", word) else (ipa or word)
            dest, wav_engine = synthesize_waveform(
                text=speak_text,
                ipa=ipa,
                path=dest,
                tempo=tempo,
                energy=energy,
                prefer_sapi=True,
            )
            wav_path = str(dest)
            notes.append(f"waveform:{wav_engine}")
        except Exception as e:
            notes.append(f"waveform_error:{type(e).__name__}")

    return Articulation(
        text=word,
        lang=lang,
        ipa=ipa,
        features=feats,
        phoneme_notes=notes,
        fsot_S=S,
        tempo_proxy=tempo,
        energy_proxy=energy,
        source=source,
        tier=tier,
        waveform_path=wav_path,
        waveform_engine=wav_engine,
    )


def articulate_translation(
    input_data: str,
    context: str = "historical",
    speak_lang: str = "en",
) -> Dict[str, Any]:
    from PFLT_FSOT_2_1_aligned import PFLT

    pflt = PFLT()
    tr = pflt.translate(input_data, context=context, target_lang="english")
    arts = []
    for meaning in tr["meanings"]:
        core = meaning.split("_")[0]
        arts.append(asdict(articulate(core, lang=speak_lang, context=context)))
    return {
        "translation": tr,
        "articulations": arts,
        "audio_policy": "ipa_articulatory_fsot_plus_waveform",
        "waveform_paths": [a.get("waveform_path") for a in arts if a.get("waveform_path")],
        "note": "IPA + articulatory features + FSOT proxies + WAV (SAPI preferred, IPA formant fallback).",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    demos = [
        ("aqua", "la", "historical"),
        ("water", "en", "linguistic"),
        ("king", "en", "mythological"),
        ("start", "en", "genomic"),
        ("soleil", "fr", "linguistic"),
    ]
    rows = [asdict(articulate(t, lang=l, context=c)) for t, l, c in demos]
    for r in rows:
        print(
            f"{r['lang']}:{r['text']} ipa={r['ipa']} "
            f"voicing={r['features'].get('voicing')} S={r['fsot_S']:.3f} tier={r['tier']}"
        )
    full = articulate_translation("aqua lingua ius", context="historical", speak_lang="en")
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "waveform": "enabled (SAPI preferred, IPA formant fallback)",
            "primary": "IPA + articulatory features + FSOT tempo/energy + WAV",
            "optional_external_clips": "Common Voice folders if user drops files",
        },
        "phoible_present": PHOIBLE.exists(),
        "demos": rows,
        "translation_sample": full,
        "waveform_paths": [r.get("waveform_path") for r in rows if r.get("waveform_path")],
    }
    path = OUT / "audio_articulation_scaffold.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (PFLT_DATA / "audio_articulation_scaffold.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("wrote", path)


if __name__ == "__main__":
    main()
