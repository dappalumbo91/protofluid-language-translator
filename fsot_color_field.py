#!/usr/bin/env python3
"""
FSOT color-field pixel grid — spectrum emergence → RGB display map.

This is the vision representation PFLT should use instead of grayscale stubs.

Physical idea (FSOT-aligned, seed-only constants):
  - Visible band is a slice of continuum wave structure.
  - Fundamental wavelength scale ties to λ_eff = π (FSOT standing-wave motif).
  - Local pixel state is NOT a single gray intensity; it is a small spectral
    field sampled at seed-derived probe wavelengths, then observer-coupled
    via quirk_mod / S when observed=True.
  - Display RGB is a derived projection for screens/files — the working tensor
    keeps multi-band + phase + coherence channels.

Working pixel tensor (float32 conceptually):
  bands[k]     — spectral amplitude at probe λ_k
  phase[k]     — phase at probe
  coherence    — local field coherence (from panel)
  S            — local scalar (optional micro-modulation)
  rgb[3]       — display projection only

No free-fit color calibration curves: probe wavelengths and weights come from
π, e, φ, γ, G only.
"""
from __future__ import annotations

import json
import math
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from mpmath import mp, mpf, sqrt, sin, cos, exp, ln, pi as MP_PI, e as MP_E

mp.dps = 40

# --- Seeds (same spine as PFLT / NeuroLab) ---------------------------------
PI = MP_PI
E = MP_E
PHI = (1 + sqrt(5)) / 2
GAMMA = mpf("0.5772156649015328606")
G_CAT = mpf("0.9159655941772190150")

# Layer-1/2 pieces used for spectrum probes
PSI_CON = 1 - 1 / E
ETA_EFF = 1 / (PI - 1)
THETA_S = sin(PSI_CON * ETA_EFF)
P_VAR = -cos(THETA_S + PI)
C_EFF = (1 - exp((-ln(PI) / E) / (ETA_EFF * ln(PHI))) * sin(THETA_S)) * (
    1 + mpf("0.01") * G_CAT / (PI * PHI)
)
P_NEW = (GAMMA / E) * sqrt(2)
C_FACTOR = C_EFF * P_NEW
K = PHI * (GAMMA / E) * sqrt(2) / ln(PI) * mpf("0.99")

# Visible window in nm (physical anchor; mapping into it is seed-derived)
VISIBLE_LO = 380.0
VISIBLE_HI = 750.0

OUT_ROOT = Path(r"D:\training data\pflt_linguistics\10_visual_scripts\hieroglyph_egyptian\images\fsot_color")


def seed_probe_wavelengths(n: int = 7) -> List[float]:
    """
    n probe wavelengths across the visible band.
    Spacing uses golden-ratio fractions of the band (no free bins).
    """
    span = VISIBLE_HI - VISIBLE_LO
    probes = []
    # φ-spaced sampling of [0,1], folded
    x = float(1 / PHI)
    for i in range(n):
        # irrational rotation by 1/φ
        x = (x + float(1 / PHI)) % 1.0
        # slight π-modulation of sample density
        u = (x + float(sin(PI * (i + 1) / n)) * 0.05) % 1.0
        lam = VISIBLE_LO + u * span
        probes.append(lam)
    probes.sort()
    return probes


def wavelength_to_rgb_display(lam_nm: float, intensity: float = 1.0) -> Tuple[float, float, float]:
    """
    Approximate CIE-like display map (standard engineering projection).
    Used only for PNG preview — not the FSOT state itself.
    Based on a classic piecewise approx of spectral locus → sRGB-ish.
    """
    lam = lam_nm
    if lam < 380 or lam > 780:
        return (0.0, 0.0, 0.0)
    if lam < 440:
        r = -(lam - 440) / (440 - 380)
        g = 0.0
        b = 1.0
    elif lam < 490:
        r = 0.0
        g = (lam - 440) / (490 - 440)
        b = 1.0
    elif lam < 510:
        r = 0.0
        g = 1.0
        b = -(lam - 510) / (510 - 490)
    elif lam < 580:
        r = (lam - 510) / (580 - 510)
        g = 1.0
        b = 0.0
    elif lam < 645:
        r = 1.0
        g = -(lam - 645) / (645 - 580)
        b = 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0

    # intensity falloff at edges of vision
    if lam < 420:
        factor = 0.3 + 0.7 * (lam - 380) / (420 - 380)
    elif lam > 700:
        factor = 0.3 + 0.7 * (780 - lam) / (780 - 700)
    else:
        factor = 1.0
    factor *= max(0.0, min(1.0, intensity))
    return (r * factor, g * factor, b * factor)


@dataclass
class FSOTPixel:
    """One grid cell of the FSOT color field."""
    bands: List[float]       # spectral amplitudes
    phases: List[float]      # phases at probes
    coherence: float
    S: float
    rgb: Tuple[float, float, float]  # display only


def fsot_spectrum_at(
    *,
    x: float,
    y: float,
    width: int,
    height: int,
    probes: Sequence[float],
    material: str = "ink_on_stone",
    glyph_mask: float = 1.0,
    observed: bool = True,
) -> FSOTPixel:
    """
    Solve a local FSOT-ish spectrum at normalized coords (x,y) in [0,1].

    material: rough domain of the surface (ink, ochre, papyrus, stone)
    glyph_mask: 1 = full mark, 0 = background substrate
    """
    # Spatial phase field using λ_eff = π motif
    # wave numbers from seeds
    kx = float(PI * PHI)
    ky = float(PI / PHI)
    phase0 = float(THETA_S) + float(PI) * x + float(E) * y

    # Material modulates effective dimension / absorption (domain routing, not free fit)
    mat = {
        "ink_on_stone": {"D": 18.0, "abs": 0.85, "bias": 0.15},
        "ochre_rock": {"D": 20.0, "abs": 0.55, "bias": 0.35},  # cave pigment
        "papyrus_ink": {"D": 16.0, "abs": 0.75, "bias": 0.25},
        "plain_stone": {"D": 18.0, "abs": 0.20, "bias": 0.70},
    }.get(material, {"D": 18.0, "abs": 0.7, "bias": 0.3})

    # Local scalar-like amplitude (simplified S structure, seed constants only)
    base = (1.0 / math.sqrt(mat["D"])) * math.cos(phase0 / float(ETA_EFF))
    growth = math.exp(float(ln(PI) / (E * PHI**13)) * float(GAMMA / PHI))
    amp = base * (1.0 + 0.1 * growth)

    if observed:
        qm = math.exp(float(C_FACTOR) * float(P_VAR)) * math.cos(phase0 + float(P_VAR))
        amp *= qm

    S = float(K) * (amp + 0.5)  # mild offset so display stays finite

    bands: List[float] = []
    phases: List[float] = []
    for i, lam in enumerate(probes):
        # Spectral envelope: π-spaced peaks; material absorption shapes band
        # Normalized wavelength coordinate
        u = (lam - VISIBLE_LO) / (VISIBLE_HI - VISIBLE_LO)
        # Standing-wave spectral modulation λ_eff ~ π
        spectral = 0.5 + 0.5 * math.sin(float(PI) * (u * float(PHI) + i / len(probes)))
        # Glyph mark deepens short-wave absorption for ink; ochre boosts long-wave
        if material == "ochre_rock":
            tint = 0.4 + 0.6 * u  # red-yellow lean
        elif material == "ink_on_stone":
            tint = 0.7 - 0.3 * u  # darker cooler ink
        else:
            tint = 0.5 + 0.2 * math.sin(float(PI) * u)

        mark = mat["bias"] + mat["abs"] * glyph_mask * tint
        b = max(0.0, min(1.5, abs(amp) * spectral * mark + 0.05 * (1.0 - glyph_mask)))
        ph = phase0 + float(PI) * u + float(THETA_S) * i
        bands.append(b)
        phases.append(ph)

    coherence = max(0.0, min(1.0, abs(math.cos(phase0)) * float(C_EFF)))

    # Display RGB: energy-weighted sum of probe colors
    r = g = b = 0.0
    wsum = 1e-9
    for lam, intensity in zip(probes, bands):
        pr, pg, pb = wavelength_to_rgb_display(lam, intensity)
        r += pr
        g += pg
        b += pb
        wsum += intensity
    r, g, b = r / wsum, g / wsum, b / wsum
    # mild S-driven brightness (emergence vs damping)
    scale = 0.55 + 0.45 * (1.0 / (1.0 + math.exp(-S)))
    r, g, b = r * scale, g * scale, b * scale
    # clamp
    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))

    return FSOTPixel(bands=bands, phases=phases, coherence=coherence, S=S, rgb=(r, g, b))


def write_png_rgb(path: Path, width: int, height: int, rgb_pixels: List[Tuple[int, int, int]]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r, g, b = rgb_pixels[y * width + x]
            raw.extend([r, g, b])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # color type 2 = RGB
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def render_field(
    width: int = 64,
    height: int = 64,
    material: str = "ink_on_stone",
    mask: Optional[List[float]] = None,
    observed: bool = True,
) -> Tuple[List[FSOTPixel], List[Tuple[int, int, int]]]:
    probes = seed_probe_wavelengths(7)
    field: List[FSOTPixel] = []
    rgb8: List[Tuple[int, int, int]] = []
    for y in range(height):
        for x in range(width):
            xn, yn = x / max(1, width - 1), y / max(1, height - 1)
            m = 1.0
            if mask is not None:
                m = mask[y * width + x]
            px = fsot_spectrum_at(
                x=xn,
                y=yn,
                width=width,
                height=height,
                probes=probes,
                material=material,
                glyph_mask=m,
                observed=observed,
            )
            field.append(px)
            rgb8.append(
                (
                    int(px.rgb[0] * 255),
                    int(px.rgb[1] * 255),
                    int(px.rgb[2] * 255),
                )
            )
    return field, rgb8


def circle_mask(width: int, height: int, cx: float, cy: float, r: float) -> List[float]:
    m = []
    for y in range(height):
        for x in range(width):
            xn, yn = x / width, y / height
            d = math.hypot(xn - cx, yn - cy)
            m.append(1.0 if d < r else 0.05)
    return m


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    probes = seed_probe_wavelengths(7)
    demos = [
        ("ink_on_stone", circle_mask(64, 64, 0.5, 0.5, 0.28)),
        ("ochre_rock", circle_mask(64, 64, 0.45, 0.55, 0.32)),
        ("papyrus_ink", circle_mask(64, 64, 0.5, 0.45, 0.25)),
        ("plain_stone", [0.0] * (64 * 64)),
    ]
    manifest = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "probes_nm": probes,
        "lambda_eff_motif": "pi",
        "channels": [
            "bands[7]",
            "phases[7]",
            "coherence",
            "S",
            "rgb_display[3]",
        ],
        "note": (
            "RGB PNGs are display projections only. "
            "Student models should train on multi-band FSOT tensors, not gray."
        ),
        "files": [],
    }
    for material, mask in demos:
        field, rgb8 = render_field(64, 64, material=material, mask=mask, observed=True)
        png = OUT_ROOT / f"fsot_color_{material}.png"
        write_png_rgb(png, 64, 64, rgb8)
        # save a tiny tensor sample (center pixel full state)
        cx = field[32 * 64 + 32]
        sample = {
            "material": material,
            "center_S": cx.S,
            "center_coherence": cx.coherence,
            "center_bands": cx.bands,
            "center_rgb": cx.rgb,
            "png": str(png),
        }
        (OUT_ROOT / f"fsot_color_{material}_center.json").write_text(
            json.dumps(sample, indent=2), encoding="utf-8"
        )
        manifest["files"].append(sample)
        print(f"wrote {png} S_center={cx.S:.4f} rgb={tuple(round(c,3) for c in cx.rgb)}")

    man_path = OUT_ROOT / "fsot_color_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # also mirror under pflt/data
    local = Path(__file__).resolve().parent / "data" / "fsot_color_manifest.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("manifest", man_path)


if __name__ == "__main__":
    main()
