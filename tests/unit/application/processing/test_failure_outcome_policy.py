"""Unit tests for processing-failure move target policy helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.failure_outcome_policy import (
    build_failure_move_targets,
)
from dpost.domain.processing.models import ProcessingCandidate
from tests.helpers.fake_processor import DummyProcessor


def _candidate(
    *,
    source: Path,
    effective_path: Path,
    preprocessed_path: Path | None,
    device,
) -> ProcessingCandidate:
    """Build a minimal candidate for failure policy tests."""
    return ProcessingCandidate(
        original_path=source,
        effective_path=effective_path,
        prefix="abc-ipat-sample",
        extension=".txt",
        processor=DummyProcessor(),
        device=device,
        preprocessed_path=preprocessed_path,
    )


def test_build_failure_move_targets_without_candidate_uses_source_path() -> None:
    """Fallback failure cleanup should target the original source path metadata."""
    path = Path("C:/watch/raw-file.bin")

    targets = build_failure_move_targets(path, candidate=None)

    assert len(targets) == 1
    assert targets[0].path == str(path)
    assert targets[0].prefix == "raw-file"
    assert targets[0].extension == ".bin"


def test_build_failure_move_targets_uses_distinct_preprocessed_artifact(config_service) -> None:
    """Distinct preprocessed artefacts should be included in cleanup targets."""
    source = Path("C:/watch/raw.txt")
    effective = Path("C:/watch/staged/raw.txt")
    preprocessed = Path("C:/watch/staged/raw.__staged__.txt")
    candidate = _candidate(
        source=source,
        effective_path=effective,
        preprocessed_path=preprocessed,
        device=config_service.devices[0],
    )

    targets = build_failure_move_targets(source, candidate)

    assert [target.path for target in targets] == [str(effective), str(preprocessed)]
    assert {target.prefix for target in targets} == {"abc-ipat-sample"}
    assert {target.extension for target in targets} == {".txt"}


def test_build_failure_move_targets_skips_duplicate_preprocessed_path(config_service) -> None:
    """Cleanup should not duplicate moves when preprocessed and effective paths match."""
    source = Path("C:/watch/raw.txt")
    effective = Path("C:/watch/staged/raw.txt")
    candidate = _candidate(
        source=source,
        effective_path=effective,
        preprocessed_path=effective,
        device=config_service.devices[0],
    )

    targets = build_failure_move_targets(source, candidate)

    assert [target.path for target in targets] == [str(effective)]
