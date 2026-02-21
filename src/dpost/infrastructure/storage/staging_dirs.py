"""Filesystem helpers for staged preprocessor directory management."""

from __future__ import annotations

from pathlib import Path


def create_unique_stage_dir(
    base_dir: Path,
    prefix: str,
    *,
    marker: str = ".__staged__",
    max_index: int = 1000,
) -> Path:
    """Create a unique staging directory named '<prefix><marker><n>'."""
    for idx in range(1, max_index):
        name = f"{prefix}{marker}{idx}"
        candidate = base_dir / name
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
    candidate = base_dir / f"{prefix}{marker}"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate
