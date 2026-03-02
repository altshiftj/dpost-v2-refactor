"""Unit coverage for reference test-device file processor behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

import dpost.device_plugins.test_device.file_processor as processor_module
from dpost.device_plugins.test_device.file_processor import (
    TestFileProcessor as ReferenceTestFileProcessor,
)
from dpost.device_plugins.test_device.settings import build_config
from dpost.domain.records.local_record import LocalRecord


def test_test_device_processor_moves_file_and_returns_output(tmp_path: Path) -> None:
    """Move source file into resolved destination and return processing metadata."""
    src = tmp_path / "source.txt"
    src.write_text("payload", encoding="utf-8")
    destination = tmp_path / "dest" / "file.txt"

    original_unique = processor_module.get_unique_filename
    original_move = processor_module.move_item
    processor_module.get_unique_filename = lambda *_args, **_kwargs: str(destination)
    processor_module.move_item = lambda source, target: Path(target).parent.mkdir(
        parents=True, exist_ok=True
    ) or Path(source).replace(Path(target))
    try:
        processor = ReferenceTestFileProcessor(build_config())
        processor.configure_runtime_context(id_separator="-")
        result = processor.device_specific_processing(
            src_path=str(src),
            record_path=str(tmp_path / "dest"),
            file_id="record-id",
            extension=".txt",
        )
    finally:
        processor_module.get_unique_filename = original_unique
        processor_module.move_item = original_move

    assert not src.exists()
    assert destination.exists()
    assert result.final_path == str(destination)
    assert result.datatype == "test"


def test_test_device_processor_reports_appendability_and_matching_rules() -> None:
    """Accept appends and match only supported reference extensions."""
    processor = ReferenceTestFileProcessor(build_config())
    record = LocalRecord(identifier="dev-usr-ipat-sample")

    assert processor.is_appendable(record, "usr-ipat-sample", ".txt") is True
    assert processor.get_device_id() == "test_device"
    assert processor.matches_file("C:/raw/sample.tif") is True
    assert processor.matches_file("C:/raw/sample.txt") is True
    assert processor.matches_file("C:/raw/sample.csv") is False


def test_test_device_processor_runtime_separator_configuration() -> None:
    """Apply runtime separator once and preserve explicit overrides."""
    processor = ReferenceTestFileProcessor(build_config())
    processor.configure_runtime_context(id_separator=":")
    assert processor._id_separator == ":"  # noqa: SLF001

    processor._id_separator = "-"  # noqa: SLF001
    processor.configure_runtime_context(id_separator="|")
    assert processor._id_separator == "-"  # noqa: SLF001


def test_test_device_processor_requires_explicit_separator_context(
    tmp_path: Path,
) -> None:
    """Reject processing when runtime separator context was not configured."""
    processor = ReferenceTestFileProcessor(build_config())
    src = tmp_path / "source.txt"
    src.write_text("payload", encoding="utf-8")

    with pytest.raises(RuntimeError, match="id_separator runtime context"):
        processor.device_specific_processing(
            src_path=str(src),
            record_path=str(tmp_path / "dest"),
            file_id="record-id",
            extension=".txt",
        )
