"""Unit tests for processing candidate metadata derivation helpers."""

from __future__ import annotations

from pathlib import Path

from dpost.application.processing.candidate_metadata import derive_candidate_metadata
from dpost.application.processing.file_processor_abstract import PreprocessingResult


def _parse_filename(path_like: str) -> tuple[str, str]:
    """Simple parser used by tests to avoid global config dependencies."""

    path = Path(path_like)
    return path.stem, path.suffix


def _strip_stage_suffix(path: Path) -> Path:
    """Remove internal staged marker used by preprocessing helpers."""

    return path.with_name(path.name.replace(".__staged__", ""))


def test_derive_candidate_metadata_prefers_overrides_when_path_exists(
    tmp_path: Path,
) -> None:
    """Prefix and extension overrides should win when effective path exists."""

    source = tmp_path / "source.txt"
    source.write_text("data")
    staged = tmp_path / "sample.__staged__.csv"
    staged.write_text("prepared")

    preprocessed = PreprocessingResult(
        effective_path=str(staged),
        prefix_override="manual-prefix",
        extension_override=".dat",
    )

    metadata = derive_candidate_metadata(
        source,
        preprocessed,
        strip_internal_stage_suffix=_strip_stage_suffix,
        parse_filename_fn=_parse_filename,
    )

    assert metadata.prefix == "manual-prefix"
    assert metadata.extension == ".dat"
    assert metadata.effective_path == staged
    assert metadata.preprocessed_path is None


def test_derive_candidate_metadata_falls_back_to_source_when_effective_path_missing(
    tmp_path: Path,
) -> None:
    """Missing prepared paths should reset metadata to the true source path."""

    source = tmp_path / "source.txt"
    source.write_text("data")
    missing = tmp_path / "prepared.xlsx"

    preprocessed = PreprocessingResult(
        effective_path=str(missing),
        prefix_override="ignored-on-fallback",
        extension_override=".bin",
    )

    metadata = derive_candidate_metadata(
        source,
        preprocessed,
        strip_internal_stage_suffix=_strip_stage_suffix,
        parse_filename_fn=_parse_filename,
    )

    assert metadata.prefix == "source"
    assert metadata.extension == ".txt"
    assert metadata.effective_path == source
    assert metadata.preprocessed_path is None


def test_derive_candidate_metadata_tracks_preprocessed_path_on_race_reappearance(
    tmp_path: Path, monkeypatch
) -> None:
    """If prepared path reappears after fallback decision, retain it for cleanup."""

    source = tmp_path / "source.txt"
    source.write_text("data")
    prepared = tmp_path / "prepared.csv"
    prepared.write_text("data")

    calls = {"prepared": 0}
    original_exists = Path.exists

    def _exists(self: Path) -> bool:
        if self == prepared:
            calls["prepared"] += 1
            # First check: path looks missing (triggers fallback)
            # Second check: path appears again (captures preprocessed_path)
            return calls["prepared"] > 1
        if self == source:
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", _exists)

    preprocessed = PreprocessingResult(effective_path=str(prepared))
    metadata = derive_candidate_metadata(
        source,
        preprocessed,
        strip_internal_stage_suffix=_strip_stage_suffix,
        parse_filename_fn=_parse_filename,
    )

    assert metadata.effective_path == source
    assert metadata.preprocessed_path == prepared


def test_derive_candidate_metadata_applies_stage_strip_for_parse_targets(
    tmp_path: Path,
) -> None:
    """Stage-suffix stripping should be applied before parsing path metadata."""

    source = tmp_path / "source.txt"
    source.write_text("data")
    staged = tmp_path / "alpha.__staged__.csv"
    staged.write_text("prepared")
    strip_inputs: list[Path] = []

    def _strip_and_record(path: Path) -> Path:
        strip_inputs.append(path)
        return _strip_stage_suffix(path)

    metadata = derive_candidate_metadata(
        source,
        PreprocessingResult(effective_path=str(staged)),
        strip_internal_stage_suffix=_strip_and_record,
        parse_filename_fn=_parse_filename,
    )

    assert metadata.prefix == "alpha"
    assert metadata.extension == ".csv"
    assert strip_inputs == [staged]
