#!/usr/bin/env python3
"""
Waveform generation for PFLT articulation layer.

Primary: Windows SAPI (win32com) → real spoken WAV
Fallback: pure-Python formant-ish WAV from IPA/text (always available)

Waveforms are part of the multimodal stack (with IPA + FSOT proxies), not left out.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import List, Optional, Tuple


def _write_wav_mono(path: Path, samples: List[float], rate: int = 22050) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for s in samples:
            v = max(-1.0, min(1.0, s))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))
    return path


def synth_from_ipa(
    ipa_or_text: str,
    path: Path,
    *,
    rate: int = 22050,
    tempo: float = 1.0,
    energy: float = 1.0,
) -> Path:
    """
    Lightweight articulatory-ish synthesizer:
    each character/segment → short tone burst with formant-like harmonics.
    Enough to *run* audio path offline without external TTS models.
    """
    text = (ipa_or_text or "?").strip() or "?"
    # strip IPA prosody marks for segment stream
    segs = [c for c in text if c not in "ˈˌ./[]()| ‖"]
    if not segs:
        segs = list(text[:8]) or ["a"]

    samples: List[float] = []
    base_dur = max(0.04, 0.09 / max(0.5, tempo))
    amp = 0.22 * max(0.3, min(1.5, energy))

    for i, ch in enumerate(segs):
        # map char code to f0 / formants
        code = ord(ch)
        f0 = 120.0 + (code % 40) * 3.5
        f1 = 400.0 + (code * 17) % 500
        f2 = 1200.0 + (code * 31) % 900
        # vowels longer
        is_vowel = ch.lower() in "aeiouɑɔɛɪʊəæøyʌɒɐ" or ch in "aeiou"
        dur = base_dur * (1.35 if is_vowel else 0.7)
        n = int(rate * dur)
        for t in range(n):
            x = t / rate
            env = min(1.0, t / (0.01 * rate)) * min(1.0, (n - t) / (0.015 * rate))
            s = (
                0.55 * math.sin(2 * math.pi * f0 * x)
                + 0.30 * math.sin(2 * math.pi * f1 * x)
                + 0.15 * math.sin(2 * math.pi * f2 * x)
            )
            samples.append(amp * env * s)
        # tiny gap
        samples.extend([0.0] * int(rate * 0.012))

    return _write_wav_mono(path, samples, rate=rate)


def synth_sapi(text: str, path: Path, *, rate_bias: int = 0) -> Optional[Path]:
    """Windows SAPI file output if win32com available."""
    try:
        import win32com.client  # type: ignore
    except Exception:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # remove existing
        if path.exists():
            path.unlink()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        # SSFMCreateForWrite = 3
        stream.Open(str(path), 3)
        voice.AudioOutputStream = stream
        try:
            voice.Rate = max(-10, min(10, rate_bias))
        except Exception:
            pass
        # Prefer speaking plain text (IPA often misread); caller can pass gloss
        voice.Speak(str(text))
        stream.Close()
        if path.exists() and path.stat().st_size > 44:
            return path
    except Exception:
        try:
            stream.Close()
        except Exception:
            pass
        return None
    return None


def synthesize_waveform(
    *,
    text: str,
    ipa: Optional[str],
    path: Path,
    tempo: float = 1.0,
    energy: float = 1.0,
    prefer_sapi: bool = True,
) -> Tuple[Path, str]:
    """
    Returns (path, engine_name).
    SAPI uses text (better prosody); fallback uses IPA for segment tones.
    """
    rate_bias = int((tempo - 1.0) * 6)
    if prefer_sapi:
        out = synth_sapi(text or (ipa or "tone"), path, rate_bias=rate_bias)
        if out is not None:
            return out, "sapi_wav"
    # IPA preferred for offline articulatory path
    src = ipa or text or "a"
    return synth_from_ipa(src, path, tempo=tempo, energy=energy), "ipa_formant_wav"
