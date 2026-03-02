"""Unit coverage for abstract file processor default helper behavior."""

from __future__ import annotations

from dpost.application.processing.file_processor_abstract import (
    FileProbeResult,
    FileProcessorABS,
    PreprocessingResult,
    ProcessingOutput,
)
from dpost.domain.records.local_record import LocalRecord


class _MinimalProcessor(FileProcessorABS):
    """Minimal concrete processor exposing base-class default behavior."""

    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        file_id: str,
        extension: str,
    ) -> ProcessingOutput:
        """Return deterministic output for base-class behavior testing."""
        return ProcessingOutput(final_path=src_path, datatype="dummy")


def test_preprocessing_result_constructors_cover_prefix_and_extension_helpers() -> None:
    """Construct preprocessing helpers for passthrough/prefix/extension variants."""
    passthrough = PreprocessingResult.passthrough("C:/raw/file.txt")
    with_prefix = PreprocessingResult.with_prefix("C:/raw/file.txt", "new-prefix")
    with_extension = PreprocessingResult.with_extension("C:/raw/file.txt", ".csv")

    assert passthrough.effective_path == "C:/raw/file.txt"
    assert passthrough.prefix_override is None
    assert with_prefix.prefix_override == "new-prefix"
    assert with_extension.extension_override == ".csv"


def test_file_processor_defaults_cover_probe_and_modified_event_behavior() -> None:
    """Exercise default preprocessing, appendability, probe, and modified-event hooks."""
    processor = _MinimalProcessor(device_config=object())
    record = LocalRecord(identifier="dev-usr-ipat-sample", id_separator="-")

    preprocessing = processor.device_specific_preprocessing("C:/raw/input.dat")
    probe = processor.probe_file("C:/raw/input.dat")

    assert preprocessing == PreprocessingResult.passthrough("C:/raw/input.dat")
    assert processor.matches_file("C:/raw/input.dat") is True
    assert processor.is_appendable(record, "usr-ipat-sample", ".dat") is True
    assert probe == FileProbeResult.unknown()
    assert processor.should_queue_modified("C:/raw/input.dat") is False
