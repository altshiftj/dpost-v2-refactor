import json
import pytest
import datetime
from pathlib import Path
from src.records import record_persistence
from src.records.local_record import LocalRecord


@pytest.fixture
def today_str():
    return datetime.datetime.now().strftime("%Y%m%d")


@pytest.fixture
def record_id():
    return "dev-usr-inst-sample_01"


@pytest.fixture
def file_path():
    return "/some/path/image.tif"


@pytest.fixture
def local_record(record_id, today_str, file_path):
    return LocalRecord(
        identifier=record_id,
        date=today_str,
        datatype="tif",
        is_in_db=False,
        files_uploaded={file_path: False},
    )


@pytest.fixture
def temp_json_path(tmp_path):
    test_file = tmp_path / "record_persistence.json"
    # Use Path directly now, no need for str()
    record_persistence.DAILY_RECORDS_JSON = test_file
    return test_file


def test_save_persisted_records_creates_valid_json(
    temp_json_path, local_record, record_id, file_path
):
    record_persistence.save_persisted_records({record_id: local_record})

    data = json.loads(temp_json_path.read_text())

    record_json = data[record_id]
    assert record_json["identifier"] == record_id
    assert record_json["user"] == "usr"
    assert record_json["institute"] == "inst"
    assert record_json["sample_name"] == "sample_01"
    assert record_json["datatype"] == "tif"
    assert record_json["date"] == local_record.date
    assert record_json["is_in_db"] is False
    assert record_json["files_uploaded"][file_path] is False


def test_load_persisted_records_returns_localrecord_objects(
    temp_json_path, record_id, today_str, file_path
):
    test_data = {
        record_id: {
            "identifier": record_id,
            "datatype": "tif",
            "date": today_str,
            "is_in_db": True,
            "files_uploaded": {file_path: True},
        }
    }

    temp_json_path.write_text(json.dumps(test_data))

    result = record_persistence.load_persisted_records()
    record = result[record_id]

    assert isinstance(record, LocalRecord)
    assert record.identifier == record_id
    assert record.user == "usr"
    assert record.institute == "inst"
    assert record.sample_name == "sample_01"
    assert record.datatype == "tif"
    assert record.date == today_str
    assert record.files_uploaded[file_path] is True


def test_load_returns_empty_dict_for_missing_file(tmp_path):
    record_persistence.DAILY_RECORDS_JSON = tmp_path / "nonexistent.json"
    assert record_persistence.load_persisted_records() == {}


def test_load_returns_empty_dict_for_corrupt_json(temp_json_path):
    temp_json_path.write_text("{ bad json ]")
    assert record_persistence.load_persisted_records() == {}
