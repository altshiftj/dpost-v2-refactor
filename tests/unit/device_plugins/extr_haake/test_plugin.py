from __future__ import annotations

from pathlib import Path

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.device_plugins.extr_haake.file_processor import (
    FileProcessorEXTRHaake,
)
from ipat_watchdog.device_plugins.extr_haake.settings import build_config


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
