"""Unit coverage for staged-directory allocation filesystem helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.infrastructure.storage.staging_dirs import create_unique_stage_dir


def test_create_unique_stage_dir_uses_first_available_index(tmp_path: Path) -> None:
    """Create stage directory at the first free index with marker suffix."""
    base_dir = tmp_path / "stage-root"
    base_dir.mkdir()
    (base_dir / "batch.__staged__1").mkdir()

    created = create_unique_stage_dir(base_dir, "batch")

    assert created == base_dir / "batch.__staged__2"
    assert created.exists()
    assert created.is_dir()


def test_create_unique_stage_dir_falls_back_when_index_range_is_exhausted(
    tmp_path: Path,
) -> None:
    """Use marker-only fallback directory when bounded index search is exhausted."""
    base_dir = tmp_path / "stage-root"
    base_dir.mkdir()
    (base_dir / "batch.__staged__1").mkdir()

    created = create_unique_stage_dir(base_dir, "batch", max_index=2)

    assert created == base_dir / "batch.__staged__"
    assert created.exists()
    assert created.is_dir()
