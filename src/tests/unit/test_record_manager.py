import pytest
import datetime
from unittest.mock import MagicMock, patch
from core.records.record_manager import RecordManager
from core.records.local_record import LocalRecord


@pytest.fixture
def mock_sync_manager():
    return MagicMock()


@pytest.fixture
def record_manager(mock_sync_manager):
    with patch(
        "src.records.record_persistence.load_persisted_records", return_value={}
    ):
        return RecordManager(sync_manager=mock_sync_manager)


def test_create_record_generates_proper_id_and_sample(record_manager):
    with patch(
        "src.records.id_generator.IdGenerator.generate_record_id",
        return_value="dev-usr-ipat-sample_A",
    ):
        record = record_manager.create_record("usr-ipat-sample_A")

    assert isinstance(record, LocalRecord)
    assert record.identifier == "dev-usr-ipat-sample_A"
    assert record.sample_name == "sample_A"
    assert record.user == "usr"
    assert record.institute == "ipat"
    assert record.date == datetime.datetime.now().strftime("%Y%m%d")
    assert record.is_in_db is False
    assert record.files_uploaded == {}
    assert record.identifier in record_manager.get_all_records()


def test_add_item_to_record_saves_it(tmp_path, record_manager):
    file_path = tmp_path / "file.tif"
    file_path.write_text("fake content")

    record = LocalRecord(
        identifier="dev-usr-ipat-sampleX", sample_name="sampleX", date="20240101"
    )
    with patch("src.records.record_persistence.save_persisted_records") as mock_save:
        record_manager.add_item_to_record(str(file_path), record)

    assert str(file_path.resolve()) in record.files_uploaded
    assert not record.files_uploaded[str(file_path.resolve())]
    mock_save.assert_called_once()


def test_get_record_by_id_case_insensitive(record_manager):
    record = LocalRecord(identifier="rem-usr-ipat-sampleZ")
    record_manager._persist_records_dict = {"rem-usr-ipat-samplez": record}

    fetched = record_manager.get_record_by_id("REM-usr-IPAT-SampleZ")
    assert fetched == record


def test_all_records_uploaded_true(record_manager):
    record = LocalRecord(identifier="r1")
    record.files_uploaded = {"f1": True, "f2": True}
    record_manager._persist_records_dict = {"r1": record}

    assert record_manager.all_records_uploaded()


def test_all_records_uploaded_false(record_manager):
    record = LocalRecord(identifier="r2")
    record.files_uploaded = {"f1": True, "f2": False}
    record_manager._persist_records_dict = {"r2": record}

    assert not record_manager.all_records_uploaded()


def test_sync_records_to_database_skips_non_ipat(record_manager):
    record = LocalRecord(identifier="dev-usr-other-sample")
    record.files_uploaded = {"f": False}
    record_manager._persist_records_dict = {"r": record}

    record_manager.sync_records_to_database()
    record_manager.sync.sync_record_to_database.assert_not_called()


def test_sync_records_to_database_uploads_ipat(record_manager):
    record = LocalRecord(identifier="dev-usr-ipat-sample")
    record.files_uploaded = {"f": False}
    record_manager._persist_records_dict = {"r": record}

    with patch("src.records.record_persistence.save_persisted_records"):
        record_manager.sync_records_to_database()

    record_manager.sync.sync_record_to_database.assert_called_once_with(record)


def test_persist_records_dict_lazy_loads_once(mock_sync_manager):
    with patch(
        "src.records.record_persistence.load_persisted_records",
        return_value={"x": LocalRecord(identifier="x")},
    ) as mock_load:
        manager = RecordManager(sync_manager=mock_sync_manager)

        # First access: triggers load
        _ = manager.persist_records_dict
        # Second access: uses cached value
        _ = manager.persist_records_dict

        mock_load.assert_called_once()


def test_sync_record_deletes_if_no_files_remain(record_manager):
    record = LocalRecord(identifier="dev-usr-ipat-sample")
    record.files_uploaded = {"dummy_path": False}
    record_manager._persist_records_dict = {"dev-usr-ipat-sample": record}

    record_manager.sync.sync_record_to_database = MagicMock(return_value=False)

    with patch("src.records.record_persistence.save_persisted_records") as mock_save:
        record_manager._sync_record(record)

    assert "dev-usr-ipat-sample" not in record_manager._persist_records_dict
    mock_save.assert_called_once()