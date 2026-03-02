from __future__ import annotations

from pathlib import Path

from dpost.domain.records.local_record import LocalRecord
from dpost.device_plugins.extr_haake.file_processor import (
    FileProcessorEXTRHaake,
)
from dpost.device_plugins.extr_haake.settings import build_config


def test_build_config_basics():
    config = build_config()

    assert config.identifier == "extr_haake"
    assert ".xlsx" in config.files.allowed_extensions
    assert ".xls" in config.files.allowed_extensions
    assert config.session.timeout_seconds == 900
    # Be a bit more patient for Excel safe-save sequences
    assert config.watcher.stable_cycles >= 2
    assert getattr(config.watcher, "reappear_window_seconds", 0.0) >= 5.0


def test_file_processor_moves_excel(tmp_path, config_service):
    config = build_config()
    processor = FileProcessorEXTRHaake(config)

    src = tmp_path / "sample.xlsx"
    src.write_text("sheet data")
    record_dir = tmp_path / "records"

    probe = processor.probe_file(str(src))
    assert probe.is_match()

    output = processor.device_specific_processing(
        str(src),
        str(record_dir),
        "user-blb-sample01",
        ".xlsx",
    )

    assert not src.exists()
    destination = Path(output.final_path)
    assert destination.exists()
    assert destination.suffix == ".xlsx"
    assert processor.matches_file(str(destination))
    assert output.datatype == "tabular"
    assert processor.is_appendable(LocalRecord(), "user-blb-sample01", ".xlsx")


def test_file_processor_probe_rejects_unsupported_extension(tmp_path):
    config = build_config()
    processor = FileProcessorEXTRHaake(config)
    src = tmp_path / "sample.csv"
    src.write_text("sheet data", encoding="utf-8")

    probe = processor.probe_file(str(src))

    assert probe.is_mismatch()


def test_configure_runtime_context_sets_missing_separator_only() -> None:
    """Apply injected separator once and preserve explicit overrides."""
    processor = FileProcessorEXTRHaake(build_config())
    processor.configure_runtime_context(id_separator=":")
    assert processor._id_separator == ":"  # noqa: SLF001

    processor._id_separator = "-"  # noqa: SLF001
    processor.configure_runtime_context(id_separator="|")
    assert processor._id_separator == "-"  # noqa: SLF001
