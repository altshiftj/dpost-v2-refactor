from pathlib import Path
from unittest.mock import patch, call
import pytest

from ipat_watchdog.device_plugins.utm_zwick.file_processor import FileProcessorUTMZwick
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.device_plugins.utm_zwick.settings import build_config


# ---------------------------------------------------------------------------
# Fixtures & boilerplate
# ---------------------------------------------------------------------------
@pytest.fixture
def processor():
    config = build_config()
    return FileProcessorUTMZwick(device_config=config)


@pytest.fixture
def dummy_record():
    return LocalRecord(
        identifier="utm-zwick-ipat-sample_a",
        sample_name="sample_a",
        datatype="csv",
        date="20250405",
    )

# ---------------------------------------------------------------------------
# Pre-processing behavior (series keyed by base prefix, CSV triggers finalize)
# ---------------------------------------------------------------------------

def test_preprocessing_stages_until_csv(tmp_path, processor):
    # first arrival → hold
    zs2 = tmp_path / "sample_a.zs2"
    csv = tmp_path / "sample_a.csv"
    zs2.write_text("raw")
    csv.write_text("results")

    r1 = processor.device_specific_preprocessing(str(zs2))
    assert r1 is None

    # csv arrival with same prefix → release
    r2 = processor.device_specific_preprocessing(str(csv))
    assert r2 == str(csv)


def test_preprocessing_accepts_either_order(tmp_path, processor):
    # CSV can arrive first and should trigger immediately
    csv = tmp_path / "s01.csv"
    csv.write_text("results")

    r1 = processor.device_specific_preprocessing(str(csv))
    assert r1 == str(csv)

# ---------------------------------------------------------------------------
# Processing flow (no zipping, zs2 moved as-is, txt snapshots flattened)
# ---------------------------------------------------------------------------

def test_device_specific_processing_happy_path(tmp_path, processor):
    # Stage artefacts via preprocessing to populate internal series buffer
    zs2 = tmp_path / "r123.zs2"
    csv = tmp_path / "r123.csv"
    t1 = tmp_path / "r123-01.txt"
    t2 = tmp_path / "r123-02.txt"

    zs2.write_text("raw-bytes")
    csv.write_text("csv-content")
    t1.write_text("snap-1")
    t2.write_text("snap-2")

    # Order shouldn't matter; include txt snapshots
    processor.device_specific_preprocessing(str(zs2))
    processor.device_specific_preprocessing(str(t1))
    processor.device_specific_preprocessing(str(t2))
    processor.device_specific_preprocessing(str(csv))  # returns str(csv), but we don't need the value here

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    # get_unique_filename is called for: zs2, csv, txt1, txt2 (in that order)
    unique_paths = [
        str(record_dir / "prefix_raw.zs2"),
        str(record_dir / "prefix_results.csv"),
        str(record_dir / "prefix_tests.txt"),
        str(record_dir / "prefix_tests(1).txt"),
    ]

    with patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.get_unique_filename",
        side_effect=unique_paths,
    ) as mock_unique, patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.move_item"
    ) as mock_move:

        # Trigger processing (CSV is the trigger/primary)
        output = processor.device_specific_processing(
            str(csv), str(record_dir), "prefix", ".csv"
        )

        # returns folder path and declared datatype
        assert Path(output.final_path) == record_dir
        assert output.datatype == "csv"

        # get_unique_filename calls (zs2, csv, txt1, txt2)
        assert mock_unique.call_count == 4
        assert mock_unique.call_args_list == [
            call(str(record_dir), "prefix_raw", ".zs2"),
            call(str(record_dir), "prefix_results", ".csv"),
            call(str(record_dir), "prefix_tests", ".txt"),
            call(str(record_dir), "prefix_tests", ".txt"),
        ]

        # move_item calls in order: zs2 -> csv -> txt1 -> txt2
        assert mock_move.call_args_list == [
            call(zs2, unique_paths[0]),
            call(csv, unique_paths[1]),
            call(str(t1), unique_paths[2]),
            call(str(t2), unique_paths[3]),
        ]


def test_device_specific_processing_raises_without_staging(tmp_path, processor):
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    # No prior preprocessing for this prefix -> should raise
    with pytest.raises(KeyError):
        processor.device_specific_processing(
            str(tmp_path / "ghost.csv"), str(record_dir), "prefix", ".csv"
        )
