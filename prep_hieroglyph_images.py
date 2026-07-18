#!/usr/bin/env python3
"""
Prepare hieroglyph image training data for the future U-Net student.

Strategy:
  1) Prefer downloading a public labeled set if available.
  2) Always also generate a **synthetic** Unicode-rendered set from Unikemet
     core signs (Segoe UI Historic / Noto Sans Egyptian Hieroglyphs / fallback).

Outputs under:
  D:\\training data\\pflt_linguistics\\10_visual_scripts\\hieroglyph_egyptian\\images\\
    synthetic/{gardiner_or_codepoint}/*.png
    labels.jsonl  — {path, gardiner, unicode, meaning}
"""
from __future__ import annotations

import json
import random
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"D:\training data\pflt_linguistics\10_visual_scripts\hieroglyph_egyptian")
IMG = ROOT / "images"
SYN = IMG / "synthetic"
LEX = ROOT / "hieroglyph_pflt_lexicon.json"
GOLD = ROOT / "hieroglyph_unikemet_gold.jsonl"
UNIKEMET = Path(r"D:\training data\pflt_linguistics\10_visual_scripts\unicode_refs\Unikemet.txt")


def parse_core_signs(limit: int = 200) -> List[Dict[str, str]]:
    """Pull core Unikemet signs that have JSesh codes + functions."""
    by_cp: Dict[str, Dict[str, str]] = {}
    if not UNIKEMET.exists():
        return []
    for line in UNIKEMET.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        cp, tag, val = parts[0], parts[1], parts[2]
        by_cp.setdefault(cp, {})[tag] = val
    rows = []
    for cp, tags in by_cp.items():
        if tags.get("kEH_Core") != "C":
            continue
        jsesh = tags.get("kEH_JSesh") or tags.get("kEH_HG")
        if not jsesh:
            continue
        try:
            ch = chr(int(cp.replace("U+", ""), 16))
        except Exception:
            continue
        rows.append(
            {
                "unicode": cp,
                "char": ch,
                "gardiner": jsesh,
                "func": tags.get("kEH_Func", ""),
                "desc": tags.get("kEH_Desc", ""),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def write_png_gray(path: Path, width: int, height: int, pixels: List[int]) -> None:
    """Minimal PNG writer (grayscale 8-bit) — no external deps."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(pixels[y * width : (y + 1) * width]) for y in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def render_glyph_bitmap(ch: str, size: int = 64, seed: int = 0) -> List[int]:
    """
    Procedural glyph-like bitmap when font rasterization is unavailable.
    Deterministic pattern from codepoint + seed so classes are separable.
    Not a real hieroglyph drawing — a stand-in for pipeline wiring / smoke training.
    """
    rng = random.Random((ord(ch) << 8) ^ seed)
    px = [240] * (size * size)  # light background
    # ink strokes
    cx, cy = size // 2, size // 2
    for _ in range(18 + (ord(ch) % 12)):
        x0 = rng.randint(4, size - 5)
        y0 = rng.randint(4, size - 5)
        x1 = rng.randint(4, size - 5)
        y1 = rng.randint(4, size - 5)
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for t in range(steps + 1):
            x = x0 + (x1 - x0) * t // steps
            y = y0 + (y1 - y0) * t // steps
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < size and 0 <= yy < size:
                        px[yy * size + xx] = max(0, px[yy * size + xx] - 90)
    # class fingerprint block (helps early classifier learning)
    code = ord(ch)
    for i in range(8):
        if code & (1 << i):
            for y in range(2, 6):
                for x in range(2 + i * 2, 4 + i * 2):
                    if x < size:
                        px[y * size + x] = 20
    return px


def try_pillow_render(ch: str, size: int = 64) -> Optional[List[int]]:
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore
    except Exception:
        return None
    img = Image.new("L", (size, size), 245)
    draw = ImageDraw.Draw(img)
    font = None
    for name in (
        "Segoe UI Historic",
        "Noto Sans Egyptian Hieroglyphs",
        "New Athena Unicode",
        "Arial Unicode MS",
        "DejaVu Sans",
    ):
        try:
            font = ImageFont.truetype(name, size - 10)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    # center roughly
    try:
        bbox = draw.textbbox((0, 0), ch, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        xy = ((size - tw) // 2, (size - th) // 2 - 2)
    except Exception:
        xy = (8, 8)
    draw.text(xy, ch, fill=15, font=font)
    return list(img.getdata())


def main() -> None:
    SYN.mkdir(parents=True, exist_ok=True)
    signs = parse_core_signs(limit=120)
    if not signs:
        raise SystemExit("No Unikemet core signs found — run hieroglyph build first")

    # meanings from gold if present
    meaning_by_g: Dict[str, str] = {}
    if GOLD.exists():
        for line in GOLD.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            g = (r.get("gardiner_jsesh") or "").strip()
            if g:
                meaning_by_g[g] = r.get("target_word") or ""

    labels: List[Dict[str, Any]] = []
    pillow_ok = try_pillow_render("𓀀") is not None
    for s in signs:
        g = s["gardiner"]
        ch = s["char"]
        folder = SYN / g.replace("/", "_")
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(3):  # 3 augment variants
            pixels = try_pillow_render(ch) if pillow_ok else None
            if pixels is None:
                pixels = render_glyph_bitmap(ch, size=64, seed=i)
            else:
                # light noise augment without numpy
                rng = random.Random(i * 17 + ord(ch))
                pixels = [min(255, max(0, p + rng.randint(-8, 8))) for p in pixels]
            fname = folder / f"{g}_{i}.png"
            write_png_gray(fname, 64, 64, pixels)
            labels.append(
                {
                    "path": str(fname.relative_to(IMG)),
                    "gardiner": g,
                    "unicode": s["unicode"],
                    "char": ch,
                    "meaning": meaning_by_g.get(g, s.get("func", "")),
                    "render": "pillow" if pillow_ok else "procedural_stub",
                }
            )

    labels_path = IMG / "labels.jsonl"
    with labels_path.open("w", encoding="utf-8") as f:
        for row in labels:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # also a tiny demo labels file for vision_stub sidecar pattern
    demo = IMG / "demo_wall.labels.json"
    demo.write_text(
        json.dumps(
            {
                "glyphs": [
                    {"gardiner": "A1", "confidence": 1.0, "bbox": [0.1, 0.1, 0.15, 0.2]},
                    {"gardiner": "N5", "confidence": 1.0, "bbox": [0.3, 0.1, 0.15, 0.2]},
                    {"gardiner": "S34", "confidence": 1.0, "bbox": [0.5, 0.1, 0.15, 0.2]},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "n_signs": len(signs),
        "n_images": len(labels),
        "pillow_font_render": pillow_ok,
        "labels": str(labels_path),
        "demo_labels": str(demo),
        "note": (
            "Synthetic set wires the U-Net training path. "
            "Replace/augment with real photo datasets when downloaded; "
            "labels.jsonl schema stays the contract."
        ),
    }
    (IMG / "image_prep_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
