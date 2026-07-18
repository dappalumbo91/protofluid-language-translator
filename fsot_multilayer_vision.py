#!/usr/bin/env python3
"""
FSOT multi-layer vision stack — best of both worlds.

Layers (all seed-derived continuum samples; no free color knobs):

  L0 GRAY   — luminance / intensity (B&W TV era, OCR heritage, robust edge path)
  L1 VIS    — human-visible spectrum → display RGB (what the eye can use)
  L2 UV     — near-UV band (cameras / sensors can register; eye mostly cannot)
  L3 NIR    — near-infrared (silicon sensors, security cams; eye cannot)
  L4 META   — S, coherence, phase summary (FSOT field state, not a camera band)

Why multi-layer:
  - Gray alone loses material/spectral structure
  - Visible color alone misses machine bands (ink binders, underdrawings, heat-adjacent)
  - Machine-only bands alone are not human-native
  Together: gray for structure, VIS for human color, UV/NIR for beyond-eye scene content

Working tensor per pixel (conceptual float stack):
  gray, rgb[3], uv, nir, bands_full[n], phases[n], S, coherence

Display:
  - gray PNG, VIS RGB PNG
  - UV/NIR false-color PNGs (map amplitude → heat/ice palette for humans)
  Real student training should use the full stack, not only RGB.
"""
from __future__ import annotations

import json
import math
import struct
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from mpmath import mp, mpf, sqrt, sin, cos, exp, ln, pi as MP_PI, e as MP_E

mp.dps = 40

PI = MP_PI
E = MP_E
PHI = (1 + sqrt(5)) / 2
GAMMA = mpf("0.5772156649015328606")
G_CAT = mpf("0.9159655941772190150")
PSI_CON = 1 - 1 / E
ETA_EFF = 1 / (PI - 1)
THETA_S = sin(PSI_CON * ETA_EFF)
P_VAR = -cos(THETA_S + PI)
POOF = exp((-ln(PI) / E) / (ETA_EFF * ln(PHI)))
C_EFF = (1 - POOF * sin(THETA_S)) * (1 + mpf("0.01") * G_CAT / (PI * PHI))
P_NEW = (GAMMA / E) * sqrt(2)
C_FACTOR = C_EFF * P_NEW
K = PHI * (GAMMA / E) * sqrt(2) / ln(PI) * mpf("0.99")

# Physical band anchors (nm) — continuum slices machines/humans actually use
UV_LO, UV_HI = 200.0, 380.0          # near-UV (solar-blind / UV cameras ~300–400)
VIS_LO, VIS_HI = 380.0, 750.0        # human visible
NIR_LO, NIR_HI = 750.0, 1400.0       # near-IR (common silicon + InGaAs edge)

OUT = Path(
    r"D:\training data\pflt_linguistics\10_visual_scripts"
    r"\hieroglyph_egyptian\images\fsot_multilayer"
)


def phi_samples(lo: float, hi: float, n: int) -> List[float]:
    """φ-spaced probes on [lo, hi] with mild π density modulation."""
    span = hi - lo
    x = float(1 / PHI)
    pts = []
    for i in range(n):
        x = (x + float(1 / PHI)) % 1.0
        u = (x + float(sin(PI * (i + 1) / max(1, n))) * 0.04) % 1.0
        pts.append(lo + u * span)
    pts.sort()
    return pts


def full_probe_set() -> Dict[str, List[float]]:
    return {
        "uv": phi_samples(UV_LO, UV_HI, 4),
        "vis": phi_samples(VIS_LO, VIS_HI, 7),
        "nir": phi_samples(NIR_LO, NIR_HI, 5),
    }


def wavelength_to_rgb_display(lam_nm: float, intensity: float = 1.0) -> Tuple[float, float, float]:
    """Display projection for VIS only (engineering spectral locus approx)."""
    lam = lam_nm
    if lam < 380 or lam > 780:
        return (0.0, 0.0, 0.0)
    if lam < 440:
        r, g, b = -(lam - 440) / (440 - 380), 0.0, 1.0
    elif lam < 490:
        r, g, b = 0.0, (lam - 440) / (490 - 440), 1.0
    elif lam < 510:
        r, g, b = 0.0, 1.0, -(lam - 510) / (510 - 490)
    elif lam < 580:
        r, g, b = (lam - 510) / (580 - 510), 1.0, 0.0
    elif lam < 645:
        r, g, b = 1.0, -(lam - 645) / (645 - 580), 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    if lam < 420:
        factor = 0.3 + 0.7 * (lam - 380) / (420 - 380)
    elif lam > 700:
        factor = 0.3 + 0.7 * (780 - lam) / (780 - 700)
    else:
        factor = 1.0
    factor *= max(0.0, min(1.0, intensity))
    return (r * factor, g * factor, b * factor)


def false_color_amplitude(a: float, mode: str = "uv") -> Tuple[float, float, float]:
    """Map non-visible amplitude to a human-viewable false color."""
    a = max(0.0, min(1.0, a))
    if mode == "uv":
        # violet–cyan ice
        return (0.35 * a, 0.15 + 0.55 * a, 0.55 + 0.45 * a)
    # nir: amber–crimson heat
    return (0.45 + 0.55 * a, 0.25 * a, 0.08 * (1.0 - a))


@dataclass
class MultiLayerPixel:
    gray: float
    rgb: Tuple[float, float, float]
    uv: float
    nir: float
    bands: Dict[str, List[float]] = field(default_factory=dict)
    phases: Dict[str, List[float]] = field(default_factory=dict)
    S: float = 0.0
    coherence: float = 0.0

    def as_tensor_flat(self) -> List[float]:
        """Fixed-order flat vector for student nets."""
        v = [self.gray, self.rgb[0], self.rgb[1], self.rgb[2], self.uv, self.nir]
        for key in ("uv", "vis", "nir"):
            v.extend(self.bands.get(key, []))
        v.extend([self.S, self.coherence])
        return v


def material_profile(material: str) -> Dict[str, float]:
    """
    Relative response by band family (physical intuition, fixed table).
    ink absorbs VIS strongly; some binders fluoresce/absorb UV;
    organic/ochre often strong NIR contrast vs stone.
    """
    profiles = {
        "ink_on_stone": {"uv": 0.9, "vis": 0.85, "nir": 0.55, "D": 18.0},
        "ochre_rock": {"uv": 0.45, "vis": 0.7, "nir": 0.85, "D": 20.0},
        "papyrus_ink": {"uv": 0.8, "vis": 0.75, "nir": 0.5, "D": 16.0},
        "plain_stone": {"uv": 0.35, "vis": 0.4, "nir": 0.4, "D": 18.0},
        "underdrawing": {"uv": 1.0, "vis": 0.25, "nir": 0.9, "D": 17.0},  # machine-revealed
    }
    return profiles.get(material, profiles["ink_on_stone"])


def fsot_multilayer_at(
    *,
    x: float,
    y: float,
    probes: Dict[str, List[float]],
    material: str = "ink_on_stone",
    glyph_mask: float = 1.0,
    observed: bool = True,
    hidden_mark: float = 0.0,
) -> MultiLayerPixel:
    """
    Solve multi-band FSOT field at one pixel.

    hidden_mark: extra structure only strong in UV/NIR (underdrawing / machine-only scene).
    """
    mat = material_profile(material)
    phase0 = float(THETA_S) + float(PI) * x + float(E) * y
    base = (1.0 / math.sqrt(mat["D"])) * math.cos(phase0 / float(ETA_EFF))
    alpha = float(ln(PI) / (E * PHI**13))
    growth = math.exp(alpha * float(GAMMA / PHI))
    amp = base * (1.0 + 0.1 * growth)
    if observed:
        qm = math.exp(float(C_FACTOR) * float(P_VAR)) * math.cos(phase0 + float(P_VAR))
        amp *= qm
    S = float(K) * (amp + 0.5)
    coherence = max(0.0, min(1.0, abs(math.cos(phase0)) * float(C_EFF)))

    bands: Dict[str, List[float]] = {}
    phases: Dict[str, List[float]] = {}

    for family, lams in probes.items():
        fam_gain = mat[family]
        bl, pl = [], []
        for i, lam in enumerate(lams):
            # normalize within family
            lo, hi = {
                "uv": (UV_LO, UV_HI),
                "vis": (VIS_LO, VIS_HI),
                "nir": (NIR_LO, NIR_HI),
            }[family]
            u = (lam - lo) / (hi - lo)
            spectral = 0.5 + 0.5 * math.sin(float(PI) * (u * float(PHI) + i / max(1, len(lams))))
            # human-visible mark
            vis_mark = glyph_mask
            # machine-only hidden content (stronger UV/NIR)
            machine_extra = hidden_mark * (1.2 if family != "vis" else 0.15)
            mark = fam_gain * (0.2 + 0.8 * vis_mark) + machine_extra
            # material tint within family
            if family == "vis" and material == "ochre_rock":
                mark *= 0.45 + 0.7 * u
            if family == "vis" and material == "ink_on_stone":
                mark *= 0.75 - 0.25 * u
            b = max(0.0, min(1.5, abs(amp) * spectral * mark + 0.04))
            bl.append(b)
            pl.append(phase0 + float(PI) * u + float(THETA_S) * i)
        bands[family] = bl
        phases[family] = pl

    # Layer aggregates
    uv = sum(bands["uv"]) / max(1, len(bands["uv"]))
    nir = sum(bands["nir"]) / max(1, len(bands["nir"]))
    vis_bands = bands["vis"]
    # gray = energy-like luminance from VIS (B&W path)
    gray = sum(vis_bands) / max(1, len(vis_bands))
    # slight UV/NIR bleed into gray for machine-aware mono path (optional small)
    gray = max(0.0, min(1.0, 0.85 * gray + 0.08 * uv + 0.07 * nir))

    r = g = b = 0.0
    wsum = 1e-9
    for lam, intensity in zip(probes["vis"], vis_bands):
        pr, pg, pb = wavelength_to_rgb_display(lam, intensity)
        r += pr
        g += pg
        b += pb
        wsum += intensity
    r, g, b = r / wsum, g / wsum, b / wsum
    scale = 0.55 + 0.45 * (1.0 / (1.0 + math.exp(-S)))
    r, g, b = [max(0.0, min(1.0, c * scale)) for c in (r, g, b)]

    return MultiLayerPixel(
        gray=gray,
        rgb=(r, g, b),
        uv=max(0.0, min(1.0, uv)),
        nir=max(0.0, min(1.0, nir)),
        bands=bands,
        phases=phases,
        S=S,
        coherence=coherence,
    )


def write_png_gray(path: Path, w: int, h: int, pixels: List[int]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    raw = b"".join(b"\x00" + bytes(pixels[y * w : (y + 1) * w]) for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def write_png_rgb(path: Path, w: int, h: int, rgb: List[Tuple[int, int, int]]) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(
            ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
        )

    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b = rgb[y * w + x]
            raw.extend([r, g, b])
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def circle_mask(w: int, h: int, cx: float, cy: float, r: float) -> List[float]:
    m = []
    for y in range(h):
        for x in range(w):
            d = math.hypot(x / w - cx, y / h - cy)
            m.append(1.0 if d < r else 0.05)
    return m


def underdrawing_mask(w: int, h: int) -> List[float]:
    """Hidden structure: diagonal band only strong in machine layers."""
    m = []
    for y in range(h):
        for x in range(w):
            # thin diagonal underdrawing
            v = abs((x / w) - (y / h))
            m.append(1.0 if v < 0.06 else 0.0)
    return m


def render_scene(
    *,
    width: int = 64,
    height: int = 64,
    material: str = "ink_on_stone",
    mask: Optional[List[float]] = None,
    hidden: Optional[List[float]] = None,
    observed: bool = True,
) -> Dict[str, object]:
    probes = full_probe_set()
    pixels: List[MultiLayerPixel] = []
    gray8: List[int] = []
    rgb8: List[Tuple[int, int, int]] = []
    uv_fc: List[Tuple[int, int, int]] = []
    nir_fc: List[Tuple[int, int, int]] = []

    for y in range(height):
        for x in range(width):
            i = y * width + x
            xn, yn = x / max(1, width - 1), y / max(1, height - 1)
            gmask = 1.0 if mask is None else mask[i]
            hmark = 0.0 if hidden is None else hidden[i]
            px = fsot_multilayer_at(
                x=xn,
                y=yn,
                probes=probes,
                material=material,
                glyph_mask=gmask,
                observed=observed,
                hidden_mark=hmark,
            )
            pixels.append(px)
            gray8.append(int(max(0, min(255, px.gray * 255))))
            rgb8.append(
                (
                    int(px.rgb[0] * 255),
                    int(px.rgb[1] * 255),
                    int(px.rgb[2] * 255),
                )
            )
            ur, ug, ub = false_color_amplitude(px.uv, "uv")
            nr, ng, nb = false_color_amplitude(px.nir, "nir")
            uv_fc.append((int(ur * 255), int(ug * 255), int(ub * 255)))
            nir_fc.append((int(nr * 255), int(ng * 255), int(nb * 255)))

    return {
        "pixels": pixels,
        "gray8": gray8,
        "rgb8": rgb8,
        "uv_fc": uv_fc,
        "nir_fc": nir_fc,
        "probes": probes,
        "tensor_dim": len(pixels[0].as_tensor_flat()) if pixels else 0,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = [
        ("ink_visible_only", "ink_on_stone", circle_mask(64, 64, 0.5, 0.5, 0.28), None),
        ("ochre_visible", "ochre_rock", circle_mask(64, 64, 0.48, 0.52, 0.3), None),
        (
            "ink_plus_hidden_underdrawing",
            "ink_on_stone",
            circle_mask(64, 64, 0.5, 0.5, 0.26),
            underdrawing_mask(64, 64),
        ),
        (
            "underdrawing_machine_only",
            "underdrawing",
            [0.05] * (64 * 64),  # almost blank to human VIS
            underdrawing_mask(64, 64),
        ),
    ]

    index = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "layers": [
            {"id": "L0_GRAY", "role": "luminance / B&W / OCR-robust edges"},
            {"id": "L1_VIS", "role": "human-visible FSOT spectrum → RGB display"},
            {"id": "L2_UV", "role": "near-UV machine band (beyond normal human vision)"},
            {"id": "L3_NIR", "role": "near-IR machine band (beyond normal human vision)"},
            {"id": "L4_META", "role": "FSOT S + coherence + phases"},
        ],
        "philosophy": (
            "Like B&W TV before color: gray remains useful. "
            "Color is applied under FSOT. Machine bands add what cameras see "
            "that eyes miss. Best of all worlds."
        ),
        "scenes": [],
    }

    for name, material, mask, hidden in scenes:
        pack = render_scene(material=material, mask=mask, hidden=hidden)
        base = OUT / name
        base.mkdir(parents=True, exist_ok=True)
        write_png_gray(base / "L0_gray.png", 64, 64, pack["gray8"])  # type: ignore
        write_png_rgb(base / "L1_vis_rgb.png", 64, 64, pack["rgb8"])  # type: ignore
        write_png_rgb(base / "L2_uv_falsecolor.png", 64, 64, pack["uv_fc"])  # type: ignore
        write_png_rgb(base / "L3_nir_falsecolor.png", 64, 64, pack["nir_fc"])  # type: ignore

        # center tensor dump
        cx = pack["pixels"][32 * 64 + 32]  # type: ignore
        center = {
            "scene": name,
            "material": material,
            "tensor_flat": cx.as_tensor_flat(),
            "tensor_dim": pack["tensor_dim"],
            "gray": cx.gray,
            "rgb": cx.rgb,
            "uv": cx.uv,
            "nir": cx.nir,
            "S": cx.S,
            "coherence": cx.coherence,
            "has_hidden_layer": hidden is not None,
        }
        (base / "center_tensor.json").write_text(
            json.dumps(center, indent=2), encoding="utf-8"
        )
        index["scenes"].append(
            {
                "name": name,
                "material": material,
                "tensor_dim": pack["tensor_dim"],
                "center_uv": cx.uv,
                "center_nir": cx.nir,
                "center_gray": cx.gray,
                "path": str(base),
            }
        )
        print(
            f"{name}: gray={cx.gray:.3f} uv={cx.uv:.3f} nir={cx.nir:.3f} "
            f"rgb=({cx.rgb[0]:.2f},{cx.rgb[1]:.2f},{cx.rgb[2]:.2f}) dim={pack['tensor_dim']}"
        )

    # tensor layout schema for U-Net student
    schema = {
        "order": [
            "gray",
            "R",
            "G",
            "B",
            "uv_agg",
            "nir_agg",
            "uv_bands[4]",
            "vis_bands[7]",
            "nir_bands[5]",
            "S",
            "coherence",
        ],
        "dim": index["scenes"][0]["tensor_dim"] if index["scenes"] else 0,
        "note": "Train students on this stack; PNGs are human inspection only.",
    }
    index["tensor_schema"] = schema
    man = OUT / "multilayer_manifest.json"
    man.write_text(json.dumps(index, indent=2), encoding="utf-8")
    local = Path(__file__).resolve().parent / "data" / "multilayer_manifest.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print("wrote", man)


if __name__ == "__main__":
    main()
