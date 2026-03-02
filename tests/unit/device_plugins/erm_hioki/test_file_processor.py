from __future__ import annotations

from pathlib import Path

from dpost.device_plugins.erm_hioki.file_processor import FileProcessorHioki
from dpost.device_plugins.erm_hioki.settings import build_config
from dpost.infrastructure.storage.filesystem_utils import get_unique_filename


def test_preprocessing_normalizes_measurement_name(tmp_path: Path) -> None:
    config = build_config()
    processor = FileProcessorHioki(config)

    measurement = tmp_path / "usr-ipat-sample_20251222132219.csv"
    measurement.write_text("measurement")

    normalized = processor.device_specific_preprocessing(str(measurement))
    assert normalized is not None

    assert normalized.effective_path == str(measurement)
    assert normalized.prefix_override == "usr-ipat-sample"


def test_processing_moves_measurement_and_forces_cc_aggregate(
    tmp_path: Path,
    config_service,
) -> None:
    config = build_config()
    processor = FileProcessorHioki(config)

    measurement = tmp_path / "usr-ipat-sample_20251222132219.csv"
    measurement.write_text("measurement")
    cc_file = tmp_path / "CC_usr-ipat-sample.csv"
    cc_file.write_text("cc-data")
    aggregate = tmp_path / "usr-ipat-sample.csv"
    aggregate.write_text("agg-data")

    record_dir = tmp_path / "records"
    file_id = "ERM-sample"
    expected_measurement = get_unique_filename(
        str(record_dir),
        file_id,
        ".csv",
        id_separator="-",
    )

    output = processor.device_specific_processing(
        str(measurement),
        str(record_dir),
        file_id,
        ".csv",
    )

    assert output.final_path == expected_measurement
    assert Path(expected_measurement).exists()
    assert not measurement.exists()

    cc_dest = record_dir / f"{file_id}-cc.csv"
    agg_dest = record_dir / f"{file_id}-results.csv"

    assert cc_dest.exists()
    assert agg_dest.exists()
    assert cc_dest.read_text() == "cc-data"
    assert agg_dest.read_text() == "agg-data"
    assert cc_file.exists()
    assert aggregate.exists()

    assert set(output.force_paths) == {str(cc_dest), str(agg_dest)}


def test_should_queue_modified_only_for_cc_and_aggregate(config_service) -> None:
    config = build_config()
    processor = FileProcessorHioki(config)
    processor.configure_runtime_context(
        id_separator=config_service.current.id_separator,
        filename_pattern=config_service.current.filename_pattern,
    )

    assert processor.should_queue_modified("CC_usr-ipat-sample.csv") is True
    assert processor.should_queue_modified("usr-ipat-sample.csv") is True
    assert (
        processor.should_queue_modified("usr-ipat-sample_20251222132219.csv") is False
    )
    assert processor.should_queue_modified("usr-ipat-sample.xlsx") is False
    assert processor.should_queue_modified("random.csv") is False
    assert processor.should_queue_modified("CC_random.csv") is False


def test_should_queue_modified_requires_explicit_runtime_naming_context() -> None:
    """Avoid ambient naming policy fallback when runtime context is not injected."""
    processor = FileProcessorHioki(build_config())

    assert processor.should_queue_modified("CC_usr-ipat-sample.csv") is False
    assert processor.should_queue_modified("usr-ipat-sample.csv") is False


def test_processing_uses_configured_separator_for_unique_filename(tmp_path: Path) -> None:
    """Use injected runtime separator when creating unique output filenames."""
    config = build_config()
    processor = FileProcessorHioki(config, id_separator=":")

    source = tmp_path / "sample.xlsx"
    source.write_text("sheet data", encoding="utf-8")
    record_dir = tmp_path / "records"

    output = processor.device_specific_processing(
        str(source),
        str(record_dir),
        "ERM-sample",
        ".xlsx",
    )

    assert Path(output.final_path).name == "ERM-sample:01.xlsx"
