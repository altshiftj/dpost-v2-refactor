from __future__ import annotations

from pathlib import Path

import pytest

from dpost.domain.records.local_record import LocalRecord
from dpost.device_plugins.rmx_eirich_el1.file_processor import (
    FileProcessorEirich as FileProcessorEirichEL1,
)
from dpost.device_plugins.rmx_eirich_r01.file_processor import (
    FileProcessorEirich as FileProcessorEirichR01,
)
from dpost.device_plugins.rmx_eirich_el1.settings import (
    build_config as build_el1_config,
)
from dpost.device_plugins.rmx_eirich_r01.settings import (
    build_config as build_r01_config,
)


@pytest.mark.parametrize(
    ("config_builder", "device_abbr", "pattern", "identifier"),
    [
        (build_el1_config, "RMX_01", "Eirich_EL1_TrendFile_*", "rmx_eirich_el1"),
        (build_r01_config, "RMX_02", "Eirich_R01_TrendFile_*", "rmx_eirich_r01"),
    ],
)
def test_build_config_maps_variant_metadata(
    config_builder,
    device_abbr: str,
    pattern: str,
    identifier: str,
) -> None:
    config = config_builder()

    assert config.identifier == identifier
    assert config.metadata.device_abbr == device_abbr
    assert pattern in config.files.filename_patterns


@pytest.mark.parametrize(
    ("config_builder", "processor_cls", "filename"),
    [
        (build_el1_config, FileProcessorEirichEL1, "Eirich_EL1_TrendFile_20250924_095653.txt"),
        (build_r01_config, FileProcessorEirichR01, "Eirich_R01_TrendFile_20250731_103330.txt"),
    ],
)
def test_probe_file_matches_variant_filename(
    tmp_path: Path,
    config_builder,
    processor_cls,
    filename: str,
) -> None:
    config = config_builder()
    processor = processor_cls(config)
    target = tmp_path / filename
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_match()
    assert result.confidence >= 0.9


@pytest.mark.parametrize(
    ("config_builder", "processor_cls", "filename"),
    [
        (build_el1_config, FileProcessorEirichEL1, "Eirich_R01_TrendFile_20250731_103330.txt"),
        (build_r01_config, FileProcessorEirichR01, "Eirich_EL1_TrendFile_20250924_095653.txt"),
    ],
)
def test_probe_file_mismatch_when_variant_does_not_match(
    tmp_path: Path,
    config_builder,
    processor_cls,
    filename: str,
) -> None:
    config = config_builder()
    processor = processor_cls(config)
    target = tmp_path / filename
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()


@pytest.mark.parametrize(
    ("config_builder", "processor_cls"),
    [
        (build_el1_config, FileProcessorEirichEL1),
        (build_r01_config, FileProcessorEirichR01),
    ],
)
def test_probe_file_mismatch_for_non_eirich_filename(
    tmp_path: Path,
    config_builder,
    processor_cls,
) -> None:
    config = config_builder()
    processor = processor_cls(config)
    target = tmp_path / "generic_file.txt"
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()


@pytest.mark.parametrize(
    ("config_builder", "processor_cls", "filename"),
    [
        (build_el1_config, FileProcessorEirichEL1, "Eirich_EL1_TrendFile_20250924_095653.csv"),
        (build_r01_config, FileProcessorEirichR01, "Eirich_R01_TrendFile_20250731_103330.csv"),
    ],
)
def test_probe_file_rejects_non_txt_extension(
    tmp_path: Path,
    config_builder,
    processor_cls,
    filename: str,
) -> None:
    config = config_builder()
    processor = processor_cls(config)
    target = tmp_path / filename
    target.write_text("payload", encoding="utf-8")

    result = processor.probe_file(str(target))

    assert result.is_mismatch()


@pytest.mark.parametrize(
    ("config_builder", "processor_cls", "expected_device_id"),
    [
        (build_el1_config, FileProcessorEirichEL1, "rmx_eirich_el1"),
        (build_r01_config, FileProcessorEirichR01, "rmx_eirich_r01"),
    ],
)
def test_processing_defaults_and_device_specific_processing(
    tmp_path: Path,
    config_service,
    config_builder,
    processor_cls,
    expected_device_id: str,
) -> None:
    config = config_builder()
    processor = processor_cls(config)
    processor.configure_runtime_context(id_separator="-")
    src = tmp_path / "Eirich_export.txt"
    src.write_text("payload", encoding="utf-8")
    record_dir = tmp_path / "records"

    preprocessed = processor.device_specific_preprocessing(str(src))
    output = processor.device_specific_processing(
        src_path=str(src),
        record_path=str(record_dir),
        file_id="user-sample",
        extension=".txt",
    )

    assert preprocessed is not None
    assert preprocessed.effective_path == str(src)
    assert processor.is_appendable(LocalRecord(), "user-sample", ".txt") is True
    assert processor.get_device_id() == expected_device_id
    assert output.datatype == "tabular"
    assert Path(output.final_path).exists()
    assert not src.exists()


@pytest.mark.parametrize(
    ("config_builder", "processor_cls"),
    [
        (build_el1_config, FileProcessorEirichEL1),
        (build_r01_config, FileProcessorEirichR01),
    ],
)
def test_processing_requires_explicit_separator_context(
    tmp_path: Path,
    config_builder,
    processor_cls,
) -> None:
    """Reject processing when runtime separator context was not configured."""
    processor = processor_cls(config_builder())
    src = tmp_path / "Eirich_export.txt"
    src.write_text("payload", encoding="utf-8")

    with pytest.raises(RuntimeError, match="id_separator runtime context"):
        processor.device_specific_processing(
            src_path=str(src),
            record_path=str(tmp_path / "records"),
            file_id="user-sample",
            extension=".txt",
        )
