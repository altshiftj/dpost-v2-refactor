import datetime
from unittest.mock import MagicMock, patch

import pytest

from dpost.domain.records.local_record import LocalRecord
from dpost.application.records.record_manager import RecordManager

pytestmark = pytest.mark.usefixtures("config_service")


@pytest.fixture
def record_manager(fake_sync, tmp_settings):
    with patch(
        "dpost.application.records.record_manager.load_persisted_records",
        return_value={},
    ):
        return RecordManager(sync_manager=fake_sync)


@pytest.fixture
def sample_record():
    return LocalRecord(identifier="dev-usr-ipat-sample", sample_name="sample", date="20240101")


def test_create_record_generates_proper_id_and_sample(record_manager):
    with patch(
        "dpost.application.records.record_manager.generate_record_id",
        return_value="dev-usr-ipat-sample_a",
    ):
        record = record_manager.create_record("usr-ipat-sample_A")

    assert isinstance(record, LocalRecord)
    assert record.identifier == "dev-usr-ipat-sample_a"
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

    record = LocalRecord(identifier="dev-usr-ipat-samplex", sample_name="sampleX", date="20240101")
    with patch(
        "dpost.application.records.record_manager.save_persisted_records"
    ) as mock_save:
        record_manager.add_item_to_record(str(file_path), record)

    resolved_path = str(file_path.resolve())
    assert resolved_path in record.files_uploaded
    assert not record.files_uploaded[resolved_path]
    mock_save.assert_called_once()


def test_remove_item_from_record_persists_state(tmp_path, record_manager):
    file_path = tmp_path / "f1.txt"
    file_path.write_text("faux")

    record = LocalRecord(identifier="dev-usr-ipat-samplex")
    record.files_uploaded = {str(file_path): False, "f2.txt": False}
    record_manager._persist_records_dict = {record.identifier: record}

    with patch(
        "dpost.application.records.record_manager.save_persisted_records"
    ) as mock_save:
        removed = record_manager.remove_item_from_record(str(file_path), record)

    mock_save.assert_called_once()
    assert removed == 1
    assert str(file_path.resolve()) not in record.files_uploaded


def test_remove_item_from_record_clears_force_flag(tmp_path, record_manager):
    file_path = tmp_path / "f1.txt"
    file_path.write_text("faux")

    resolved = str(file_path.resolve())
    record = LocalRecord(identifier="dev-usr-ipat-samplex")
    record.files_uploaded = {resolved: False, "f2.txt": False}
    record.files_require_force = {resolved}
    record_manager._persist_records_dict = {record.identifier: record}

    with patch(
        "dpost.application.records.record_manager.save_persisted_records"
    ) as mock_save:
        removed = record_manager.remove_item_from_record(str(file_path), record)

    mock_save.assert_called_once()
    assert removed == 1
    assert resolved not in record.files_uploaded
    assert resolved not in record.files_require_force


def test_remove_item_from_record_removes_directory_tracked_children(
    tmp_path,
    record_manager,
):
    record_dir = tmp_path / "record_dir"
    nested_dir = record_dir / "nested"
    nested_dir.mkdir(parents=True)
    child = nested_dir / "child.txt"
    child.write_text("payload", encoding="utf-8")

    normalized_dir = str(record_dir.resolve())
    normalized_child = str(child.resolve())
    record = LocalRecord(identifier="dev-usr-ipat-samplex")
    record.files_uploaded = {normalized_dir: False, normalized_child: False}
    record_manager._persist_records_dict = {record.identifier: record}

    with patch(
        "dpost.application.records.record_manager.save_persisted_records"
    ) as mock_save:
        removed = record_manager.remove_item_from_record(str(record_dir), record)

    mock_save.assert_called_once()
    assert removed == 2
    assert record.files_uploaded == {}


def test_get_record_by_id_case_insensitive(record_manager):
    record = LocalRecord(identifier="rem-usr-ipat-sampleZ")
    record_manager._persist_records_dict = {"rem-usr-ipat-samplez": record}
    assert record_manager.get_record_by_id("REM-usr-IPAT-SampleZ") == record


@pytest.mark.parametrize(
    "uploaded_map, expected",
    [
        ({"f1": True, "f2": True}, True),
        ({"f1": True, "f2": False}, False),
    ],
)
def test_all_records_uploaded(record_manager, uploaded_map, expected):
    record = LocalRecord(identifier="r1")
    record.files_uploaded = uploaded_map
    record_manager._persist_records_dict = {record.identifier: record}

    assert record_manager.all_records_uploaded() is expected


def test_sync_records_to_database_skips_non_ipat(record_manager):
    record = LocalRecord(identifier="dev-usr-other-sample")
    record.files_uploaded = {"f": False}
    record_manager._persist_records_dict = {"r": record}

    with patch.object(record_manager.sync, "sync_record_to_database") as mock_sync:
        record_manager.sync_records_to_database()
        mock_sync.assert_not_called()


def test_sync_records_to_database_uploads_ipat(record_manager):
    record = LocalRecord(identifier="dev-usr-ipat-sample")
    record.files_uploaded = {"f": False}
    record_manager._persist_records_dict = {record.identifier: record}

    with patch("dpost.application.records.record_manager.save_persisted_records"):
        with patch.object(record_manager.sync, "sync_record_to_database", return_value=False) as mock_sync:
            record_manager.sync_records_to_database()
            mock_sync.assert_called_once_with(record)


def test_sync_records_to_database_skips_already_uploaded_ipat_record(record_manager):
    record = LocalRecord(identifier="dev-usr-ipat-sample")
    record.files_uploaded = {"f": True}
    record_manager._persist_records_dict = {record.identifier: record}

    with patch.object(record_manager.sync, "sync_record_to_database") as mock_sync:
        record_manager.sync_records_to_database()
        mock_sync.assert_not_called()


def test_persist_records_dict_lazy_loads_once(fake_sync):
    with patch(
        "dpost.application.records.record_manager.load_persisted_records",
        return_value={"x": LocalRecord(identifier="x")},
    ) as mock_load:
        manager = RecordManager(sync_manager=fake_sync)
        _ = manager.persist_records_dict
        _ = manager.persist_records_dict
        mock_load.assert_called_once()


@pytest.mark.skip(reason="Deactivated pending review of sync record deletion logic.")
def test_sync_record_deletes_if_no_files_remain(record_manager):
    record = LocalRecord(identifier="dev-usr-ipat-sample")
    record.files_uploaded = {"dummy_path": False}
    record_manager._persist_records_dict = {"dev-usr-ipat-sample": record}
    record_manager.sync.sync_record_to_database = MagicMock(return_value=False)

    with patch(
        "dpost.application.records.record_manager.save_persisted_records"
    ) as mock_save:
        record_manager._sync_record(record)

    assert "dev-usr-ipat-sample" not in record_manager._persist_records_dict
    assert mock_save.call_count == 2


def test_get_num_records_counts_loaded(record_manager):
    record_manager._persist_records_dict = {
        "r1": LocalRecord(identifier="r1"),
        "r2": LocalRecord(identifier="r2"),
    }

    assert record_manager.get_num_records() == 2


def test_reload_records_refreshes_cache(fake_sync):
    with patch(
        "dpost.application.records.record_manager.load_persisted_records",
        return_value={"initial": LocalRecord(identifier="initial")},
    ):
        manager = RecordManager(sync_manager=fake_sync)
        assert set(manager.persist_records_dict) == {"initial"}

    with patch(
        "dpost.application.records.record_manager.load_persisted_records",
        return_value={"fresh": LocalRecord(identifier="fresh")},
    ):
        manager.reload_records()

    assert set(manager.persist_records_dict) == {"fresh"}


def test_infer_id_separator_defaults_to_dash_for_alnum_prefix(record_manager):
    assert record_manager._infer_id_separator("sample123") == "-"  # noqa: SLF001
