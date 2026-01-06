from __future__ import annotations

from pathlib import Path

import pytest

from ipat_watchdog.device_plugins.mix_eirich.file_processor import FileProcessorEirich
from ipat_watchdog.device_plugins.mix_eirich.settings import build_config


@pytest.fixture
def processor() -> FileProcessorEirich:
    return FileProcessorEirich(build_config())


def test_read_text_prefix_truncates_to_limit(tmp_path: Path, processor: FileProcessorEirich) -> None:
    target = tmp_path / "large.txt"
    target.write_text("A" * 8192, encoding="utf-8")

    snippet = processor._read_text_prefix(target, bytes_limit=1024)

    assert snippet == "A" * 1024


def test_read_text_prefix_decodes_cp1252(tmp_path: Path, processor: FileProcessorEirich) -> None:
    target = tmp_path / "cp1252.txt"
    payload = ("Temperature " + chr(176) + "C").encode("cp1252")
    target.write_bytes(payload)

    snippet = processor._read_text_prefix(target)

    assert "Temperature" in snippet
    assert chr(176) in snippet
    assert snippet.strip().endswith("C")


def test_device_config_includes_content_markers(processor: FileProcessorEirich) -> None:
    config = processor.device_config
    
    assert hasattr(config, "markers")
    assert hasattr(config.markers, "positive")
    assert hasattr(config.markers, "filename_patterns")


def test_config_positive_markers_match_expected_set(processor: FileProcessorEirich) -> None:
    expected = frozenset({
        "rotorrev",
        "rotorpower",
        "mixingpanrev",
        "mixingpanpower",
        "rotorspeed",
        "mixingpanspeed",
    })
    
    assert processor.device_config.markers.positive == expected


def test_config_filename_patterns_include_eirich_patterns(processor: FileProcessorEirich) -> None:
    patterns = processor.device_config.markers.filename_patterns
    
    assert "Eirich_*" in patterns
    assert "*_TrendFile_*" in patterns


def test_matches_eirich_prefix_pattern(processor: FileProcessorEirich) -> None:
    assert processor._matches_filename_pattern("Eirich_EL1_TrendFile_20250924_095653.txt") is True
    assert processor._matches_filename_pattern("Eirich_M5_Data.txt") is True


def test_matches_trendfile_pattern(processor: FileProcessorEirich) -> None:
    assert processor._matches_filename_pattern("SomeMachine_TrendFile_20250101.txt") is True


def test_does_not_match_generic_filename(processor: FileProcessorEirich) -> None:
    assert processor._matches_filename_pattern("generic_file.txt") is False
    assert processor._matches_filename_pattern("dissolver_export.txt") is False


def test_filename_matching_is_case_insensitive(processor: FileProcessorEirich) -> None:
    assert processor._matches_filename_pattern("eirich_test.txt") is True
    assert processor._matches_filename_pattern("EIRICH_TEST.txt") is True
    assert processor._matches_filename_pattern("file_TRENDFILE_data.txt") is True


def test_probe_file_rejects_non_txt_extension(tmp_path: Path, processor: FileProcessorEirich) -> None:
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("some data", encoding="utf-8")
    
    result = processor.probe_file(str(csv_file))
    
    assert result.is_mismatch()
    assert "unsupported extension" in result.reason.lower()


def test_probe_file_unknown_when_file_unreadable(tmp_path: Path, processor: FileProcessorEirich) -> None:
    missing_file = tmp_path / "missing.txt"
    
    result = processor.probe_file(str(missing_file))
    
    assert result.decision.name == "UNKNOWN"
    assert result.confidence == 0.0


def test_probe_file_unknown_when_no_markers_found(tmp_path: Path, processor: FileProcessorEirich) -> None:
    generic_file = tmp_path / "generic.txt"
    generic_file.write_text("Just some random text\nwith no Eirich markers", encoding="utf-8")
    
    result = processor.probe_file(str(generic_file))
    
    assert result.decision.name == "UNKNOWN"
    assert result.confidence == 0.0


def test_probe_file_filename_only_gives_modest_confidence(tmp_path: Path, processor: FileProcessorEirich) -> None:
    eirich_named_file = tmp_path / "Eirich_EL1_TrendFile_20250924.txt"
    eirich_named_file.write_text("Generic content\nNo markers here", encoding="utf-8")
    
    result = processor.probe_file(str(eirich_named_file))
    
    assert result.is_match()
    assert result.confidence == pytest.approx(0.70, abs=1e-9)  # base 0.55 + 0.15*1


def test_probe_file_full_eirich_file_high_confidence(tmp_path: Path, processor: FileProcessorEirich) -> None:
    eirich_file = tmp_path / "Eirich_EL1_TrendFile_20250924_095653.txt"
    header = "Date [yyyy-MM-dd]\tTime [hh:mm:ss]\tRotorRev [1/min]\tRotorSpeed [m/s]\tRotorPower [W]\tMixingPanRev [1/min]\tMixingPanSpeed [m/s]\tMixingPanPower [W]\tStopWatch [s]\tTemperature [°C]\n"
    data = "2025-09-24\t09:56:55\t-2245\t-9.4\t15.7\t0\t0.0\t1.0\t2\t21\n"
    eirich_file.write_text(header + data, encoding="utf-8")
    
    result = processor.probe_file(str(eirich_file))
    
    assert result.is_match()
    assert result.confidence == 0.95  # 6 markers + 1 filename = 7 hits, capped at 0.95


def test_probe_file_content_only_high_confidence(tmp_path: Path, processor: FileProcessorEirich) -> None:
    no_name_match = tmp_path / "export.txt"
    header = "RotorRev [1/min]\tRotorPower [W]\tMixingPanRev [1/min]\tMixingPanPower [W]\tRotorSpeed [m/s]\tMixingPanSpeed [m/s]\n"
    no_name_match.write_text(header, encoding="utf-8")
    
    result = processor.probe_file(str(no_name_match))
    
    assert result.is_match()
    assert result.confidence == 0.95  # 6 markers, no filename bonus


def test_probe_file_partial_markers_moderate_confidence(tmp_path: Path, processor: FileProcessorEirich) -> None:
    partial_file = tmp_path / "data.txt"
    partial_file.write_text("RotorRev [1/min]\tRotorPower [W]\tSomeOtherColumn\n", encoding="utf-8")
    
    result = processor.probe_file(str(partial_file))
    
    assert result.is_match()
    assert result.confidence == pytest.approx(0.85, abs=1e-9)  # base 0.55 + 0.15*2


def test_probe_file_rejects_dsv_horiba_content(tmp_path: Path, processor: FileProcessorEirich) -> None:
    """Validate that DSV Horiba .txt files don't match Eirich fingerprint."""
    horiba_file = tmp_path / "dissolution_data.txt"
    horiba_content = "Time [min]\tDissolution [%]\tRelease [%]\tpH\tTemperature [°C]\n"
    horiba_file.write_text(horiba_content, encoding="utf-8")
    
    result = processor.probe_file(str(horiba_file))
    
    assert result.decision.name == "UNKNOWN"
    assert result.confidence == 0.0
    assert "no eirich markers" in result.reason.lower()
