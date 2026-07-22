#!/usr/bin/env python3
"""Build a clean verification source tree for HF / Kaggle (no multi-GB dumps)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "pflt-verify-source"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "obj",
    "bin",
    "alire",
    "proof",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
}
SKIP_NAMES = {
    "train_mass.tsv",
    "densify.tsv",
    "gold_core.tsv",
    "train_cache.pkl",
    "m6_phrase_table.tsv",
    "m6_bigram_table.tsv",
    "ltm_mulling.jsonl",
    "knowledge_ledger_ada.jsonl",
}
SKIP_SUFFIX = {
    ".pdf",
    ".exe",
    ".o",
    ".ali",
    ".pyc",
    ".cswi",
    ".spark",
    ".stderr",
    ".stdout",
    ".bexch",
    ".wav",
    ".mp3",
    ".mp4",
    ".safetensors",
    ".bin",
}
MAX_FILE = 25_000_000  # 25 MB hard cap per file


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(p in SKIP_DIRS for p in rel.parts):
        return True
    if path.name in SKIP_NAMES:
        return True
    if path.suffix.lower() in SKIP_SUFFIX:
        return True
    if path.name.startswith("A Proto-Fluid"):
        return True
    try:
        if path.stat().st_size > MAX_FILE:
            return True
    except OSError:
        return True
    return False


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    n = 0
    bytes_ = 0
    for src in ROOT.rglob("*"):
        if not src.is_file():
            continue
        if should_skip(src):
            continue
        rel = src.relative_to(ROOT)
        dst = OUT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
        bytes_ += src.stat().st_size
    # root pointer for verifiers
    (OUT / "VERIFY_ME_FIRST.md").write_text(
        (ROOT / "docs" / "VERIFICATION.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    print(f"packed {n} files, {bytes_ / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main()
