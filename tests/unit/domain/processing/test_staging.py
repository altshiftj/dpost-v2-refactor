"""Unit coverage for domain staging reconstruction and stale detection."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import dpost.domain.processing.staging as staging_module
from dpost.domain.processing.staging import (
    find_stale_stage_dirs,
    reconstruct_pairs_from_stage,
)


def _touch(path: Path, mtime: float) -> None:
    """Set deterministic modification time for stable policy ordering checks."""
    os.utime(path, (mtime, mtime))


def test_reconstruct_pairs_from_stage_prefers_stem_matches_then_fallback(
    local_tmp_path: Path,
) -> None:
    """Pair by stem first, then zip unmatched leftovers in mtime order."""
    stage_dir = local_tmp_path / "Batch.__staged__1"
    stage_dir.mkdir()

    left_a = stage_dir / "a.csv"
    left_b = stage_dir / "b.csv"
    right_a = stage_dir / "a.ngb"
    right_c = stage_dir / "c.ngb"

    for path in (left_a, left_b):
        path.write_text("left", encoding="utf-8")
    for path in (right_a, right_c):
        path.write_bytes(b"right")

    _touch(left_a, 10.0)
    _touch(left_b, 20.0)
    _touch(right_a, 30.0)
    _touch(right_c, 40.0)

    prefix, pairs = reconstruct_pairs_from_stage(
        stage_dir=stage_dir,
        left_filter=lambda path: path.suffix == ".csv",
        right_filter=lambda path: path.suffix == ".ngb",
    )

    assert prefix == "Batch"
    assert len(pairs) == 2
    assert pairs[0] == (left_a, right_a)
    assert pairs[1] == (left_b, right_c)


def test_reconstruct_pairs_from_stage_raises_when_expected_side_missing(
    local_tmp_path: Path,
) -> None:
    """Fail fast when staged folder has no left or no right candidates."""
    stage_dir = local_tmp_path / "Sample.__staged__5"
    stage_dir.mkdir()
    (stage_dir / "only.csv").write_text("left", encoding="utf-8")

    with pytest.raises(RuntimeError, match="missing expected files"):
        reconstruct_pairs_from_stage(
            stage_dir=stage_dir,
            left_filter=lambda path: path.suffix == ".csv",
            right_filter=lambda path: path.suffix == ".ngb",
        )


def test_reconstruct_pairs_from_stage_raises_when_no_pairs_constructed(
    local_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise explicit no-pairs error when fallback pairing yields no results."""
    stage_dir = local_tmp_path / "Sample.__staged__6"
    stage_dir.mkdir()
    (stage_dir / "left.csv").write_text("left", encoding="utf-8")
    (stage_dir / "right.ngb").write_bytes(b"right")

    monkeypatch.setattr(staging_module, "zip", lambda *_: iter(()), raising=False)

    with pytest.raises(RuntimeError, match="No left/right pairs found"):
        reconstruct_pairs_from_stage(
            stage_dir=stage_dir,
            left_filter=lambda path: path.suffix == ".csv",
            right_filter=lambda path: path.suffix == ".ngb",
        )


def test_find_stale_stage_dirs_skips_active_and_fresh_entries(
    local_tmp_path: Path,
) -> None:
    """Return only stale marker directories that are not currently active."""
    parent = local_tmp_path / "watch"
    parent.mkdir()

    stale = parent / "old.__staged__1"
    active = parent / "active.__staged__1"
    fresh = parent / "fresh.__staged__1"
    normal = parent / "ordinary"
    for path in (stale, active, fresh, normal):
        path.mkdir()

    now = 100.0
    _touch(stale, now - 30.0)
    _touch(active, now - 30.0)
    _touch(fresh, now - 2.0)
    _touch(normal, now - 30.0)

    stale_dirs = find_stale_stage_dirs(
        parent=parent,
        marker=".__staged__",
        ttl_seconds=10.0,
        now=now,
        active=[str(active)],
    )

    assert stale_dirs == [stale]


def test_find_stale_stage_dirs_treats_stat_errors_as_stale(
    local_tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Conservatively treat unreadable stage directory metadata as stale."""
    parent = local_tmp_path / "watch"
    parent.mkdir()
    broken = parent / "broken.__staged__1"
    broken.mkdir()

    real_stat = Path.stat
    broken_stat_calls = 0

    def _fake_stat(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal broken_stat_calls
        if self == broken:
            broken_stat_calls += 1
            if broken_stat_calls > 1:
                raise OSError("simulated stat failure")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", _fake_stat)

    stale_dirs = find_stale_stage_dirs(
        parent=parent,
        marker=".__staged__",
        ttl_seconds=10.0,
        now=50.0,
    )

    assert stale_dirs == [broken]
