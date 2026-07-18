#!/usr/bin/env python3
"""
Minimal vision stub for PFLT hieroglyph path.

Pipeline (student → teacher):
  image path
    → detect/classify placeholder (or explicit --gardiner / JSON labels)
    → Gardiner / Unicode IDs
    → Unikemet/PFLT lexicon meanings
    → FSOT-modulated narrative via PFLT

This is intentionally NOT a trained U-Net yet. It defines the contract a real
vision student must satisfy so we can benchmark detection later (top-1 Gardiner,
IoU) separately from meaning accuracy (lexicon + S gates).

Usage:
  python vision_stub.py --image wall.jpg --gardiner A1 D21 N5
  python vision_stub.py --labels labels.json
  python vision_stub.py --demo
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PFLT_FSOT_2_1_aligned import PFLT


@dataclass
class GlyphHypothesis:
    """One detected/classified sign (student output contract)."""
    gardiner: Optional[str] = None
    unicode_char: Optional[str] = None
    bbox: Optional[List[float]] = None  # [x,y,w,h] normalized 0-1
    confidence: float = 0.0
    source: str = "manual"  # manual | stub_detector | unet (future)


@dataclass
class VisionTranslateResult:
    image_path: Optional[str]
    hypotheses: List[GlyphHypothesis]
    pflt: Dict[str, Any]
    pipeline: List[str] = field(default_factory=list)
    note: str = ""
    # Optional link to FSOT color-field representation (not grayscale)
    color_field_note: str = (
        "Preferred vision tensor is FSOT multi-layer stack "
        "(L0 gray + L1 VIS RGB + L2 UV + L3 NIR + L4 S/coherence); "
        "see fsot_multilayer_vision.py. Gray and color together; machine bands beyond human eye."
    )


def load_labels_json(path: Path) -> List[GlyphHypothesis]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("glyphs") or raw.get("labels") or []
    out: List[GlyphHypothesis] = []
    for it in items:
        out.append(
            GlyphHypothesis(
                gardiner=it.get("gardiner") or it.get("jsesh") or it.get("code"),
                unicode_char=it.get("char") or it.get("unicode_char"),
                bbox=it.get("bbox"),
                confidence=float(it.get("confidence", 1.0)),
                source=it.get("source", "labels_json"),
            )
        )
    return out


def stub_detect_from_image(image_path: Path) -> List[GlyphHypothesis]:
    """
    Placeholder detector.

    Real U-Net student will replace this. For now:
      - If sidecar labels exist (image.json / image.labels.json), load them
      - Else return empty with explicit note (no hallucinated glyphs)
    """
    for side in (
        image_path.with_suffix(".labels.json"),
        image_path.with_suffix(".json"),
        image_path.parent / f"{image_path.stem}_labels.json",
    ):
        if side.exists():
            hyps = load_labels_json(side)
            for h in hyps:
                h.source = f"sidecar:{side.name}"
            return hyps
    return []


def hypotheses_to_input(hyps: List[GlyphHypothesis]) -> str:
    parts: List[str] = []
    for h in hyps:
        if h.gardiner:
            parts.append(str(h.gardiner).strip())
        elif h.unicode_char:
            parts.append(str(h.unicode_char))
    return " ".join(parts)


def vision_translate(
    *,
    image_path: Optional[Path] = None,
    gardiner: Optional[List[str]] = None,
    labels_path: Optional[Path] = None,
    pflt: Optional[PFLT] = None,
    target_lang: str = "english",
) -> VisionTranslateResult:
    pipeline = ["vision_stub.v0"]
    hyps: List[GlyphHypothesis] = []

    if labels_path:
        hyps = load_labels_json(labels_path)
        pipeline.append("load_labels_json")
    if gardiner:
        hyps.extend(
            GlyphHypothesis(gardiner=g, confidence=1.0, source="cli") for g in gardiner
        )
        pipeline.append("cli_gardiner")
    if image_path is not None:
        pipeline.append("image_path_received")
        if not hyps:
            hyps = stub_detect_from_image(image_path)
            pipeline.append("stub_detect_or_sidecar")
        # record that image existed / missing without reading pixels if no labels
        if not image_path.exists():
            pipeline.append("warn_image_missing")

    if not hyps:
        return VisionTranslateResult(
            image_path=str(image_path) if image_path else None,
            hypotheses=[],
            pflt={
                "translation": "",
                "meanings": [],
                "error": "no_glyph_hypotheses",
            },
            pipeline=pipeline,
            note=(
                "No glyphs provided. Pass --gardiner, --labels, or a sidecar "
                "*.labels.json next to the image. U-Net student will fill this later."
            ),
        )

    text = hypotheses_to_input(hyps)
    pipeline.append("hypotheses_to_token_string")
    engine = pflt or PFLT(load_historical=True, load_hieroglyphs=True)
    pipeline.append("pflt_fsot_translate")
    result = engine.translate(text, context="hieroglyphic", target_lang=target_lang)

    return VisionTranslateResult(
        image_path=str(image_path) if image_path else None,
        hypotheses=hyps,
        pflt=result,
        pipeline=pipeline,
        note=(
            "Vision student is stub/manual; meaning layer is Unikemet+FSOT. "
            "Benchmark detection and meaning separately."
        ),
    )


def result_to_dict(r: VisionTranslateResult) -> Dict[str, Any]:
    return {
        "image_path": r.image_path,
        "hypotheses": [asdict(h) for h in r.hypotheses],
        "pflt": r.pflt,
        "pipeline": r.pipeline,
        "note": r.note,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="PFLT vision stub (hieroglyph path)")
    ap.add_argument("--image", type=Path, default=None, help="Image path (optional)")
    ap.add_argument("--gardiner", nargs="*", default=None, help="Gardiner codes e.g. A1 D21 N5")
    ap.add_argument("--labels", type=Path, default=None, help="JSON labels file")
    ap.add_argument("--target", default="english", help="PFLT target_lang")
    ap.add_argument("--demo", action="store_true", help="Run built-in demo without image")
    ap.add_argument("--out", type=Path, default=None, help="Write JSON result")
    args = ap.parse_args()

    if args.demo:
        # Classic demo sequence: man / mouth(r) / owl(m) / sun / ankh
        args.gardiner = ["A1", "D21", "G17", "N5", "S34"]
        print("DEMO gardiner:", " ".join(args.gardiner))

    r = vision_translate(
        image_path=args.image,
        gardiner=args.gardiner,
        labels_path=args.labels,
        target_lang=args.target,
    )
    payload = result_to_dict(r)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print("wrote", args.out)
    return 0 if r.hypotheses else 2


if __name__ == "__main__":
    raise SystemExit(main())
