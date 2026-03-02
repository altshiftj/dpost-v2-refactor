"""Separator-context coverage for RMX EIRICH processors."""

from __future__ import annotations

from pathlib import Path

from dpost.device_plugins.rmx_eirich_el1.file_processor import (
    FileProcessorEirich as FileProcessorEirichEL1,
)
from dpost.device_plugins.rmx_eirich_el1.settings import build_config as build_el1_config
from dpost.device_plugins.rmx_eirich_r01.file_processor import (
    FileProcessorEirich as FileProcessorEirichR01,
)
from dpost.device_plugins.rmx_eirich_r01.settings import build_config as build_r01_config


def test_el1_processing_uses_configured_separator_for_unique_filename(
    tmp_path: Path,
) -> None:
    """Use injected separator for EL1 unique filename composition."""
    processor = FileProcessorEirichEL1(build_el1_config())
    processor.configure_runtime_context(id_separator=":")

    src = tmp_path / "Eirich_EL1_TrendFile_001.txt"
    src.write_text("payload", encoding="utf-8")
    record_dir = tmp_path / "record"

    output = processor.device_specific_processing(
        str(src),
        str(record_dir),
        "prefix",
        ".txt",
    )

    assert Path(output.final_path).name == "prefix:01.txt"


def test_r01_processing_uses_configured_separator_for_unique_filename(
    tmp_path: Path,
) -> None:
    """Use injected separator for R01 unique filename composition."""
    processor = FileProcessorEirichR01(build_r01_config())
    processor.configure_runtime_context(id_separator=":")

    src = tmp_path / "Eirich_R01_TrendFile_001.txt"
    src.write_text("payload", encoding="utf-8")
    record_dir = tmp_path / "record"

    output = processor.device_specific_processing(
        str(src),
        str(record_dir),
        "prefix",
        ".txt",
    )

    assert Path(output.final_path).name == "prefix:01.txt"
