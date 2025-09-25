from pathlib import Path
from unittest.mock import patch
import time
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
        datatype="xlsx",
        date="20250405",
    )

# ---------------------------------------------------------------------------
# Pre-processing staging behavior
# ---------------------------------------------------------------------------

def test_preprocessing_stages_until_pair_complete(tmp_path, processor):
    # first arrival → hold
    zs2 = tmp_path / "sample_a.zs2"
    xlsx = tmp_path / "sample_a.xlsx"
    zs2.write_text("raw")
    xlsx.write_text("sheet")

    r1 = processor.device_specific_preprocessing(str(zs2))
    assert r1 is None

    # second arrival with same prefix → release
    r2 = processor.device_specific_preprocessing(str(xlsx))
    assert r2 == str(xlsx)


def test_preprocessing_accepts_either_order(tmp_path, processor):
    zs2 = tmp_path / "s01.zs2"
    xlsx = tmp_path / "s01.xlsx"
    zs2.write_text("raw")
    xlsx.write_text("sheet")

    r1 = processor.device_specific_preprocessing(str(xlsx))
    assert r1 is None

    r2 = processor.device_specific_preprocessing(str(zs2))
    assert r2 == str(zs2)

# ---------------------------------------------------------------------------
# Processing flow
# ---------------------------------------------------------------------------

def test_device_specific_processing_happy_path(tmp_path, processor):
    # Stage both artefacts via preprocessing to populate the internal buffer
    zs2 = tmp_path / "r123.zs2"
    xlsx = tmp_path / "r123.xlsx"
    zs2.write_text("raw-bytes")
    xlsx.write_text("excel-content")

    processor.device_specific_preprocessing(str(zs2))
    processor.device_specific_preprocessing(str(xlsx))

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    unique_xlsx = record_dir / "prefix.xlsx"

    with patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.get_unique_filename",
        return_value=str(unique_xlsx),
    ) as mock_unique, patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.move_item"
    ) as mock_move, patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.shutil.make_archive"
    ) as mock_archive:

        mock_archive.return_value = str(record_dir / "prefix.zs2.zip")

        # Trigger processing once both are present
        output = processor.device_specific_processing(
            str(xlsx), str(record_dir), "prefix", ".xlsx"
        )

        # returns folder path and declared datatype
        assert Path(output.final_path) == record_dir
        assert output.datatype == "xlsx"

        # archiving call builds from the raw .zs2
        expected_base = str((record_dir / "prefix.zs2.zip").with_suffix(""))
        mock_archive.assert_called_once_with(
            base_name=expected_base,
            format="zip",
            root_dir=str(zs2.parent),
            base_dir=zs2.name,
        )

        # source .zs2 is deleted after archiving
        assert not zs2.exists()

        # xlsx gets a unique name and is moved into record dir
        mock_unique.assert_called_once_with(str(record_dir), "prefix", ".xlsx")
        mock_move.assert_called_once_with(xlsx, str(unique_xlsx))


def test_device_specific_processing_raises_without_staging(tmp_path, processor):
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    with pytest.raises(KeyError):
        processor.device_specific_processing(
            str(tmp_path / "ghost.xlsx"), str(record_dir), "prefix", ".xlsx"
        )


# ---------------------------------------------------------------------------
# Series aggregation (.txt + .csv) new workflow
# ---------------------------------------------------------------------------

def test_series_aggregation_with_multiple_txt_and_csv(tmp_path, processor):
    # Speed up finalization by disabling delay
    processor.csv_finalize_delay_seconds = 0

    # Create artefacts
    zs2 = tmp_path / "seriesA.zs2"
    txt = tmp_path / "seriesA.txt"  # instrument would overwrite; we simulate new snapshots
    csv = tmp_path / "seriesA.csv"

    zs2.write_text("raw-increment-1")
    assert processor.device_specific_preprocessing(str(zs2)) is None

    # first txt snapshot
    txt.write_text("t1 data")
    assert processor.device_specific_preprocessing(str(txt)) is None

    # second txt snapshot (overwrite same filename; processor still snapshots)
    txt.write_text("t2 data")
    assert processor.device_specific_preprocessing(str(txt)) is None

    # final csv triggers processing
    csv.write_text("final results")
    trigger = processor.device_specific_preprocessing(str(csv))
    assert trigger == str(csv)

    record_dir = tmp_path / "record_series"
    record_dir.mkdir()

    unique_csv = record_dir / "seriesA.csv"

    from unittest.mock import patch
    with patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.get_unique_filename",
        return_value=str(unique_csv),
    ) as mock_unique, patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.move_item"
    ) as mock_move, patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.shutil.make_archive"
    ) as mock_archive:
        mock_archive.return_value = str(record_dir / "seriesA.zs2.zip")

        output = processor.device_specific_processing(
            str(csv), str(record_dir), "seriesA", ".csv"
        )

        assert output.datatype == "csv"
        assert Path(output.final_path) == record_dir
        mock_unique.assert_called_once()
        mock_move.assert_called_once()
        mock_archive.assert_called_once()

    # Check snapshot folder content
    from ipat_watchdog.device_plugins.utm_zwick.file_processor import _series_snapshot_dir_name
    snapshots_dir = record_dir / _series_snapshot_dir_name("seriesA")
    assert snapshots_dir.exists(), "Snapshots folder missing"
    snaps = list(snapshots_dir.glob("*.txt"))
    assert len(snaps) == 2, f"Expected 2 txt snapshots, got {len(snaps)}"


# ---------------------------------------------------------------------------
# Orphan purging
# ---------------------------------------------------------------------------

def test_purge_orphans_moves_files(tmp_path, processor):
    # Simulate an old staged entry with a real file on disk
    old = tmp_path / "old.zs2"
    old.write_text("data")

    processor._pending = {
        "old": {"t": time.time() - 1000, "zs2": old}
    }

    # Force TTL small so entry is considered orphaned
    processor.device_config.batch.ttl_seconds = 0

    with patch(
        "ipat_watchdog.device_plugins.utm_zwick.file_processor.move_to_exception_folder"
    ) as mock_exc:
        processor._purge_orphans()
        mock_exc.assert_called_once()
        # buffer cleared
        assert processor._pending == {}
