from __future__ import annotations

from pathlib import Path

import pytest

from ipat_watchdog.device_plugins.mix_eirich.file_processor import FileProcessorEirich
from ipat_watchdog.device_plugins.mix_eirich.settings import build_config


@pytest.mark.parametrize(
    ("variant", "device_abbr", "pattern", "identifier"),
    [
        ("EL1", "RMX_01", "Eirich_EL1_TrendFile_*", "rmx_eirich_el1"),
        ("R01", "RMX_02", "Eirich_R01_TrendFile_*", "rmx_eirich_r01"),
    ],
)
def test_build_config_maps_variant_metadata(
    variant: str,
    device_abbr: str,
    pattern: str,
    identifier: str,
) -> None:
    config = build_config(variant)

    assert config.identifier == identifier
    assert config.metadata.device_abbr == device_abbr
    assert pattern in config.files.filename_patterns


@pytest.mark.parametrize(
    ("variant", "filename"),
    [
        ("EL1", "Eirich_EL1_TrendFile_20250924_095653.txt"),
        ("R01", "Eirich_R01_TrendFile_20250731_103330.txt"),
    ],
)
def test_probe_file_matches_variant_filename(tmp_path: Path, variant: str, filename: str) -> None:
    config = build_config(variant)
    processor = FileProcessorEirich(config)
    target = tmp_path / filename
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_match()
    assert result.confidence >= 0.9


def test_probe_file_mismatch_when_variant_does_not_match(tmp_path: Path) -> None:
    config = build_config("EL1")
    processor = FileProcessorEirich(config)
    target = tmp_path / "Eirich_R01_TrendFile_20250731_103330.txt"
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()


def test_probe_file_mismatch_for_non_eirich_filename(tmp_path: Path) -> None:
    config = build_config("R01")
    processor = FileProcessorEirich(config)
    target = tmp_path / "generic_file.txt"
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()


def test_probe_file_rejects_non_txt_extension(tmp_path: Path) -> None:
    config = build_config("EL1")
    processor = FileProcessorEirich(config)
    target = tmp_path / "Eirich_EL1_TrendFile_20250924_095653.csv"
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()
