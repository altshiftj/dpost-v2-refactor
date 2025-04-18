import pytest
from pathlib import Path
from pyfakefs.fake_filesystem_unittest import Patcher

from config.settings_store import SettingsStore
from config.settings_base import BaseSettings
from records.local_record import LocalRecord


# ──────────────────────────────── Fixtures ──────────────────────────────── #

@pytest.fixture(autouse=True)
def init_settings(tmp_path):
    """
    Ensures that the SettingsStore is initialized before each test.
    Required for LocalRecord to parse identifier correctly.
    """
    class TempSettings(BaseSettings):
        ID_SEP = "-"
    SettingsStore.set(TempSettings())
    yield
    SettingsStore.reset()


@pytest.fixture
def sample_record():
    return LocalRecord(
        identifier="dev-jdoe-ipat-sample_1", datatype="tiff", date="20250405"
    )


# ──────────────────────────────── Tests ──────────────────────────────── #

def test_init_defaults():
    record = LocalRecord()
    assert record.identifier == "null"
    assert record.user == "null"
    assert record.institute == "null"
    assert record.sample_name == "null"
    assert record.datatype == "null"
    assert record.date == "null"
    assert record.is_in_db is False
    assert record.files_uploaded == {}


def test_init_with_identifier():
    record = LocalRecord(identifier="dev-usr-inst-sample_1")
    assert record.user == "usr"
    assert record.institute == "inst"
    assert record.sample_name == "sample_1"


def test_init_with_invalid_identifier(caplog):
    caplog.set_level("WARNING")
    record = LocalRecord(identifier="invalid")
    assert record.user == "null"
    assert record.institute == "null"
    assert record.sample_name == "null"
    assert "does not conform" in caplog.text


def test_add_item_file_fs(sample_record):
    with Patcher() as patcher:
        fake_file = "/path/to/fake_file.tif"
        patcher.fs.create_file(fake_file, contents="fake data")
        sample_record.add_item(fake_file)

        resolved = str(Path(fake_file).resolve())
        assert resolved in sample_record.files_uploaded
        assert sample_record.files_uploaded[resolved] is False


def test_add_item_dir_fs(sample_record):
    with Patcher() as patcher:
        base_dir = "/path/to/fake_dir"
        patcher.fs.create_dir(base_dir)
        file1 = f"{base_dir}/file1.tif"
        file2 = f"{base_dir}/subdir/file2.tif"
        patcher.fs.create_file(file1)
        patcher.fs.create_file(file2)

        sample_record.add_item(base_dir)

        for f in [file1, file2]:
            resolved = str(Path(f).resolve())
            assert resolved in sample_record.files_uploaded
            assert sample_record.files_uploaded[resolved] is False


def test_add_item_nested_dir(sample_record):
    with Patcher() as patcher:
        base_dir = "/nested"
        nested_file = "/nested/lvl1/lvl2/file.tif"
        patcher.fs.create_file(nested_file)

        sample_record.add_item(base_dir)

        resolved = str(Path(nested_file).resolve())
        assert resolved in sample_record.files_uploaded
        assert sample_record.files_uploaded[resolved] is False


def test_add_same_file_twice(sample_record):
    with Patcher() as patcher:
        file_path = "/dup/file.tif"
        patcher.fs.create_file(file_path)

        sample_record.add_item(file_path)
        sample_record.add_item(file_path)

        resolved = str(Path(file_path).resolve())
        assert list(sample_record.files_uploaded.keys()).count(resolved) == 1


def test_add_item_neither_file_nor_dir_fs(sample_record, caplog):
    caplog.set_level("WARNING")
    with Patcher():
        weird_path = "/some/odd/path"
        sample_record.add_item(weird_path)

        assert weird_path not in sample_record.files_uploaded
        warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
        assert any("neither a file nor a directory" in w for w in warnings)


def test_mark_uploaded(sample_record):
    fake_path = Path("/path/to/fake_file.tif").resolve()
    sample_record.files_uploaded[str(fake_path)] = False

    sample_record.mark_uploaded(fake_path)
    assert sample_record.files_uploaded[str(fake_path)] is True


def test_mark_uploaded_nonexistent(sample_record, caplog):
    caplog.set_level("WARNING")
    fake_path = "/file/not/in/record"
    sample_record.mark_uploaded(fake_path)

    warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Tried to mark non-existent file" in w for w in warnings)


def test_all_files_uploaded_true(sample_record):
    sample_record.files_uploaded = {"/file/one": True, "/file/two": True}
    assert sample_record.all_files_uploaded() is True


def test_all_files_uploaded_false(sample_record):
    sample_record.files_uploaded = {"/file/one": True, "/file/two": False}
    assert sample_record.all_files_uploaded() is False


def test_to_dict_from_dict_roundtrip():
    original = LocalRecord(
        identifier="rem-jdoe-ipat-sample_1",
        datatype="tiff",
        date="20250405",
        is_in_db=True,
        files_uploaded={"/file1.tif": True, "/file2.tif": False},
    )
    data = original.to_dict()
    restored = LocalRecord.from_dict(data)

    assert restored.identifier == original.identifier
    assert restored.user == original.user
    assert restored.institute == original.institute
    assert restored.sample_name == original.sample_name
    assert restored.datatype == original.datatype
    assert restored.date == original.date
    assert restored.is_in_db == original.is_in_db
    assert restored.files_uploaded == original.files_uploaded
