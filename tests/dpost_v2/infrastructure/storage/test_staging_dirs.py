from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from dpost_v2.infrastructure.storage.staging_dirs import (
    StagingDirsSafetyError,
    StagingDirsTokenError,
    StagingLayout,
    cleanup_candidates,
    derive_staging_layout,
)


def test_layout_derivation_is_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    root = tmp_path / "storage"
    when = date(2026, 3, 4)

    first = derive_staging_layout(
        root=root,
        profile="qa",
        mode="headless",
        processing_date=when,
        device_token="xrd",
    )
    second = derive_staging_layout(
        root=root,
        profile="qa",
        mode="headless",
        processing_date=when,
        device_token="xrd",
    )

    assert first == second
    assert isinstance(first, StagingLayout)


def test_layout_derivation_can_provision_directories(tmp_path: Path) -> None:
    root = tmp_path / "storage"

    layout = derive_staging_layout(
        root=root,
        profile="qa",
        mode="headless",
        processing_date=date(2026, 3, 4),
        device_token="xrd",
        create_on_demand=True,
    )

    assert layout.intake.exists()
    assert layout.staging.exists()
    assert layout.processed.exists()
    assert layout.rejected.exists()
    assert layout.archive.exists()


def test_layout_derivation_rejects_unsafe_tokens(tmp_path: Path) -> None:
    with pytest.raises(StagingDirsTokenError):
        derive_staging_layout(
            root=tmp_path,
            profile="qa",
            mode="headless",
            processing_date=date(2026, 3, 4),
            device_token="../../escape",
        )


def test_layout_safety_guard_blocks_paths_outside_root(tmp_path: Path) -> None:
    with pytest.raises(StagingDirsSafetyError):
        derive_staging_layout(
            root=tmp_path,
            profile="qa",
            mode="headless",
            processing_date=date(2026, 3, 4),
            device_token="xrd",
            archive_override=tmp_path.parent / "outside",
        )


def test_cleanup_candidate_filter_excludes_active_intake_and_staging(
    tmp_path: Path,
) -> None:
    layout = derive_staging_layout(
        root=tmp_path,
        profile="qa",
        mode="headless",
        processing_date=date(2026, 3, 4),
        device_token="xrd",
    )
    candidate_paths = (
        layout.intake,
        layout.staging,
        layout.processed / "2026-03-03",
        layout.archive / "2026-03-01",
    )

    filtered = cleanup_candidates(layout, candidate_paths)

    assert layout.intake not in filtered
    assert layout.staging not in filtered
    assert layout.processed / "2026-03-03" in filtered
    assert layout.archive / "2026-03-01" in filtered


def test_cleanup_candidate_filter_excludes_paths_outside_root_scope(
    tmp_path: Path,
) -> None:
    layout = derive_staging_layout(
        root=tmp_path,
        profile="qa",
        mode="headless",
        processing_date=date(2026, 3, 4),
        device_token="xrd",
    )
    outside = tmp_path.parent / "outside-retention-target"
    inside = layout.processed / "2026-03-03"

    filtered = cleanup_candidates(layout, (outside, inside))

    assert outside not in filtered
    assert inside in filtered
