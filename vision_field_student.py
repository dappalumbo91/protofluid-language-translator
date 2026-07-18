#!/usr/bin/env python3
"""
Lightweight multilayer vision student (no U-Net weights required).

Uses FSOT multilayer pixel tensors (gray/VIS/UV/NIR/S) to classify scene
structure and emit PFLT-facing labels. This closes the vision-student
contract without waiting for deep training.

Waveform audio is out of scope here (and not preferred for speech either).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fsot_multilayer_vision import (
    circle_mask,
    fsot_multilayer_at,
    full_probe_set,
    render_scene,
    underdrawing_mask,
)
from PFLT_FSOT_2_1_aligned import PFLT

OUT = Path(r"D:\training data\pflt_linguistics\10_visual_scripts\hieroglyph_egyptian\images\fsot_multilayer")
PFLT_DATA = Path(r"C:\Users\damia\Desktop\pflt\data")


@dataclass
class VisionReadout:
    scene_class: str
    confidence: float
    mean_gray: float
    mean_uv: float
    mean_nir: float
    mean_S: float
    has_hidden_machine_band: bool
    pflt_tokens: List[str]
    pflt_translation: str
    notes: List[str]


def aggregate_field(pack: Dict[str, Any]) -> Dict[str, float]:
    """Use means + peaks so thin underdrawings aren't washed out by background."""
    pixels = pack["pixels"]
    n = max(1, len(pixels))
    grays = [p.gray for p in pixels]
    uvs = [p.uv for p in pixels]
    nirs = [p.nir for p in pixels]
    rs = [p.rgb[0] for p in pixels]
    # top-decile means for machine bands (localized structure)
    def top_mean(vals: List[float], frac: float = 0.1) -> float:
        k = max(1, int(len(vals) * frac))
        return sum(sorted(vals, reverse=True)[:k]) / k

    return {
        "mean_gray": sum(grays) / n,
        "mean_uv": sum(uvs) / n,
        "mean_nir": sum(nirs) / n,
        "mean_S": sum(p.S for p in pixels) / n,
        "mean_r": sum(rs) / n,
        "peak_uv": top_mean(uvs, 0.08),
        "peak_nir": top_mean(nirs, 0.08),
        "peak_gray": top_mean(grays, 0.08),
        "peak_r": top_mean(rs, 0.08),
        "uv_nir_ratio": (sum(uvs) + sum(nirs)) / max(1e-6, sum(grays) * 2),
    }


def classify_scene(stats: Dict[str, float]) -> tuple[str, float, List[str], List[str]]:
    """Rule student on multilayer stats → class + PFLT token hints."""
    notes: List[str] = []
    g = stats["mean_gray"]
    r = stats["mean_r"]
    puv, pnir, pgray = stats["peak_uv"], stats["peak_nir"], stats["peak_gray"]
    ratio = stats["uv_nir_ratio"]
    # Hidden / machine content: peaks in UV/NIR high vs gray peaks
    machine_peak = (puv > 0.14 and pnir > 0.12) or (puv + pnir > 1.35 * max(pgray, 0.05))
    weak_visible = pgray < 0.12 and g < 0.085
    tokens: List[str] = []

    if machine_peak and weak_visible:
        cls, conf = "machine_only_underdrawing", 0.88
        tokens = ["hidden_structure", "uv_band", "nir_band"]
        notes.append("Peak UV/NIR with weak gray peaks → beyond-eye content")
    elif machine_peak and (puv > stats["mean_uv"] * 1.15):
        cls, conf = "visible_mark_plus_hidden", 0.82
        tokens = ["surface_mark", "hidden_structure", "uv_band"]
        notes.append("Localized UV/NIR peaks on surface mark")
    elif stats["peak_r"] > 0.40 and pnir >= puv * 0.9:
        cls, conf = "ochre_like_pigment", 0.78
        tokens = ["ochre", "pigment", "nir_band"]
        notes.append("Red-lean VIS + NIR → ochre-like")
    elif pgray > 0.10 or g > 0.075:
        cls, conf = "ink_or_surface_mark", 0.72
        tokens = ["surface_mark", "ink"]
        notes.append("Gray structure dominant")
    else:
        cls, conf = "plain_substrate", 0.65
        tokens = ["substrate", "stone"]
        notes.append("Low structure across bands")

    notes.append(f"peak_uv={puv:.3f} peak_nir={pnir:.3f} peak_gray={pgray:.3f} ratio={ratio:.3f}")
    return cls, conf, tokens, notes


def readout_from_pack(pack: Dict[str, Any], pflt: Optional[PFLT] = None) -> VisionReadout:
    stats = aggregate_field(pack)
    cls, conf, tokens, notes = classify_scene(stats)
    engine = pflt or PFLT(load_classical=False, load_hieroglyphs=True)
    # Map tokens through linguistic/visual context
    text = " ".join(tokens)
    # inject temporary process words if missing
    for t in tokens:
        engine.pul_terms.setdefault(t, t)
        engine.pul_terms.setdefault(t.replace("_", " "), t)
    engine._keys_sorted = sorted(
        list(engine.pul_terms.keys()) + list(engine.hieroglyph_terms.keys()),
        key=len,
        reverse=True,
    )
    tr = engine.translate(text, context="visual_script")
    return VisionReadout(
        scene_class=cls,
        confidence=conf,
        mean_gray=stats["mean_gray"],
        mean_uv=stats.get("peak_uv", stats["mean_uv"]),
        mean_nir=stats.get("peak_nir", stats["mean_nir"]),
        mean_S=stats["mean_S"],
        has_hidden_machine_band=cls.startswith("machine") or "hidden" in cls,
        pflt_tokens=tr["tokens"],
        pflt_translation=tr["translation"],
        notes=notes,
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scenes = {
        "ink_visible": render_scene(
            material="ink_on_stone",
            mask=circle_mask(64, 64, 0.5, 0.5, 0.28),
        ),
        "ochre": render_scene(
            material="ochre_rock",
            mask=circle_mask(64, 64, 0.48, 0.52, 0.3),
        ),
        "ink_plus_hidden": render_scene(
            material="ink_on_stone",
            mask=circle_mask(64, 64, 0.5, 0.5, 0.26),
            hidden=underdrawing_mask(64, 64),
        ),
        "machine_only": render_scene(
            material="underdrawing",
            mask=[0.05] * (64 * 64),
            hidden=underdrawing_mask(64, 64),
        ),
    }
    pflt = PFLT(load_classical=False)
    results = []
    for name, pack in scenes.items():
        ro = readout_from_pack(pack, pflt=pflt)
        results.append({"scene": name, **asdict(ro)})
        print(
            f"{name:18s} -> {ro.scene_class:28s} conf={ro.confidence:.2f} "
            f"uv={ro.mean_uv:.3f} nir={ro.mean_nir:.3f}"
        )
        print(f"  PFLT: {ro.pflt_translation[:100]}")

    # sanity checks for closure
    by = {r["scene"]: r for r in results}
    checks = {
        "machine_only_detected": "machine" in by["machine_only"]["scene_class"],
        "hidden_boost_class": "hidden" in by["ink_plus_hidden"]["scene_class"],
        "ochre_not_plain": by["ochre"]["scene_class"] != "plain_substrate",
        "ink_has_structure": by["ink_visible"]["scene_class"] != "plain_substrate",
    }
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "student": "rule_probe_on_fsot_multilayer_tensor",
        "waveform": "not_used",
        "checks": checks,
        "ok": all(checks.values()),
        "results": results,
    }
    path = OUT / "vision_field_student_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (PFLT_DATA / "vision_field_student_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("checks", checks, "ok", report["ok"])
    print("wrote", path)


if __name__ == "__main__":
    main()
