"""Unit coverage for force-path resolution and unsynced target expansion."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.force_path_policy import (
    iter_force_unsynced_targets,
    resolve_force_paths,
)


def test_resolve_force_paths_skips_blank_and_resolves_relative(tmp_path: Path) -> None:
    """Resolve record-relative entries and preserve missing-path status."""
    record_dir = tmp_path / "record"
    record_dir.mkdir()

    relative_existing = record_dir / "relative.csv"
    relative_existing.write_text("ok")
    absolute_existing = record_dir / "absolute.csv"
    absolute_existing.write_text("ok")

    resolved = resolve_force_paths(
        (
            "",
            "relative.csv",
            str(absolute_existing),
            "missing.csv",
        ),
        str(record_dir),
    )

    assert [item.raw_path for item in resolved] == [
        "relative.csv",
        str(absolute_existing),
        "missing.csv",
    ]
    assert resolved[0].resolved_path == relative_existing
    assert resolved[0].exists is True
    assert resolved[1].resolved_path == absolute_existing
    assert resolved[1].exists is True
    assert resolved[2].resolved_path == record_dir / "missing.csv"
    assert resolved[2].exists is False


def test_iter_force_unsynced_targets_yields_files_for_directory(tmp_path: Path) -> None:
    """Yield every file for directory inputs, including nested files."""
    force_dir = tmp_path / "force"
    nested = force_dir / "nested"
    nested.mkdir(parents=True)
    first = force_dir / "a.csv"
    second = nested / "b.csv"
    first.write_text("a")
    second.write_text("b")

    yielded = {
        path.relative_to(force_dir).as_posix()
        for path in iter_force_unsynced_targets(force_dir)
    }

    assert yielded == {"a.csv", "nested/b.csv"}


def test_iter_force_unsynced_targets_yields_file_path_for_single_file(
    tmp_path: Path,
) -> None:
    """Yield the input path itself when the force target is already a file."""
    file_path = tmp_path / "single.csv"
    file_path.write_text("x")

    yielded = tuple(iter_force_unsynced_targets(file_path))

    assert yielded == (file_path,)
