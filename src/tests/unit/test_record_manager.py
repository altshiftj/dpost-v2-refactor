import pytest
import datetime
from unittest.mock import MagicMock, patch
from src.records.record_manager import RecordManager


@pytest.fixture
def mock_sync_manager():
    return MagicMock()


@pytest.fixture
def mock_record():
    mock = MagicMock()
    mock.identifier = "rem-usr-ipat-sampleA"
    mock.name = "sampleA"
    mock.all_files_uploaded.return_value = True
    mock.files_uploaded = {}
    return mock


@pytest.fixture
def record_manager(mock_sync_manager):
    with patch('src.records.record_persistence.load_persisted_records', return_value={}), \
         patch('src.records.local_record.LocalRecord') as MockRecord:
        return RecordManager(sync_manager=mock_sync_manager)


def test_create_record_with_mock(record_manager):
    with patch('src.records.id_generator.IdGenerator.generate_record_id', return_value="rem-usr-ipat-sampleA"), \
         patch('src.records.local_record.LocalRecord', autospec=True) as MockRecord:

        instance = MockRecord.return_value
        instance.identifier = "rem-usr-inst-sampleA"
        instance.user = "usr"
        instance.institute = "inst"
        instance.sample_name = "sampleA"
        instance.datatype = "null"
        instance.date = datetime.datetime.now().strftime('%Y%m%d')
        instance.is_in_db = False
        instance.files_uploaded = {}

        record = record_manager.create_record("usr-inst-sampleA")

        assert record == instance
        assert "rem-usr-inst-sampleA" in record_manager.get_all_records()


def test_add_item_to_record_with_mock(record_manager, mock_record):
    with patch.object(mock_record, 'add_item'), \
         patch('src.records.record_persistence.save_persisted_records') as mock_save:
        
        record_manager.persist_records_dict["mock-id"] = mock_record
        record_manager.add_item_to_record("fake/path.tif", mock_record)

        mock_record.add_item.assert_called_once_with("fake/path.tif")
        mock_save.assert_called_once()


def test_get_record_by_id_case_insensitive(record_manager, mock_record):
    record_manager.persist_records_dict["rem-usr-ipat-samplea"] = mock_record
    result = record_manager.get_record_by_id("REM-usr-IPAT-SampleA")
    assert result == mock_record


def test_all_records_uploaded_true(record_manager, mock_record):
    record_manager.persist_records_dict = {
        "mock-id": mock_record
    }
    mock_record.all_files_uploaded.return_value = True
    assert record_manager.all_records_uploaded()


def test_all_records_uploaded_false(record_manager, mock_record):
    record_manager.persist_records_dict = {
        "mock-id": mock_record
    }
    mock_record.all_files_uploaded.return_value = False
    assert not record_manager.all_records_uploaded()


def test_sync_records_to_database_skips_non_ipat(record_manager, mock_record):
    mock_record.identifier = "rem-usr-another-sample"
    mock_record.all_files_uploaded.return_value = False
    record_manager.persist_records_dict = {"mock-id": mock_record}

    record_manager.sync_records_to_database()
    record_manager.sync.sync_record_to_database.assert_not_called()


def test_sync_records_to_database_uploads_ipat(record_manager, mock_record):
    mock_record.identifier = "rem-usr-ipat-sample"
    mock_record.all_files_uploaded.return_value = False
    record_manager.persist_records_dict = {"mock-id": mock_record}

    with patch('src.records.record_persistence.save_persisted_records'):
        record_manager.sync_records_to_database()
        record_manager.sync.sync_record_to_database.assert_called_once_with(mock_record)
