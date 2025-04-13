import pytest
from pathlib import Path
from pyfakefs.fake_filesystem_unittest import Patcher

from core.records.local_record import LocalRecord


@pytest.fixture
def sample_record():
    """
    A pytest fixture that returns a fresh LocalRecord before each test.
    """
    return LocalRecord(
        identifier="dev-jdoe-ipat-sample_1", datatype="tiff", date="20250405"
    )


def test_init_defaults():
    """
    When initialized without arguments, ensure LocalRecord has default attributes.
    """
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
    """
    When initialized with an identifier, ensure LocalRecord extracts user, institute, and sample name correctly.
    """
    record = LocalRecord(identifier="dev-usr-inst-sample_1")
    assert record.user == "usr"
    assert record.institute == "inst"
    assert record.sample_name == "sample_1"


def test_add_item_file_fs(sample_record):
    """
    Using pyfakefs to simulate a single file. We don't patch path checks;
    `Path.is_file()` will behave as if the file exists on a real filesystem.
    """
    with Patcher() as patcher:
        # Create file in the fake filesystem
        fake_file = "/path/to/fake_file.tif"
        patcher.fs.create_file(fake_file, contents="fake data")

        # Act
        sample_record.add_item(fake_file)

        # Assert
        resolved_path = str(Path(fake_file).resolve())
        assert resolved_path in sample_record.files_uploaded
        assert sample_record.files_uploaded[resolved_path] is False


def test_add_item_dir_fs(sample_record):
    """
    Using pyfakefs to simulate a directory with subdirectories & files.
    Again, no manual patching for Path.is_file / Path.is_dir.
    """
    with Patcher() as patcher:
        # Create directories and files
        base_dir = "/path/to/fake_dir"
        patcher.fs.create_dir(base_dir)

        file1 = f"{base_dir}/file1.tif"
        file2 = f"{base_dir}/subdir/file2.tif"

        patcher.fs.create_file(file1, contents="file1 data")
        patcher.fs.create_file(file2, contents="file2 data")

        # Act
        sample_record.add_item(base_dir)

        # Assert
        for f in [file1, file2]:
            resolved_path = str(Path(f).resolve())
            assert resolved_path in sample_record.files_uploaded
            assert sample_record.files_uploaded[resolved_path] is False


def test_add_item_neither_file_nor_dir_fs(sample_record, caplog):
    """
    If path is neither a file nor a directory in the fake filesystem,
    ensure a warning is logged and nothing is added.
    """
    with Patcher():
        # We do NOT create this path, so it won't exist in the fakefs
        weird_path = "/some/odd/path"

        # Act
        sample_record.add_item(weird_path)

        # Assert: it should not be in files_uploaded
        assert weird_path not in sample_record.files_uploaded

        # Check logs for a warning
        warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
        assert any("neither a file nor a directory" in w for w in warnings)


def test_mark_uploaded(sample_record):
    """
    mark_uploaded() should set an existing file's status to True if found.
    """
    fake_path = Path("/path/to/fake_file.tif").resolve()
    sample_record.files_uploaded[str(fake_path)] = False

    sample_record.mark_uploaded(fake_path)
    assert sample_record.files_uploaded[str(fake_path)] is True


def test_mark_uploaded_nonexistent(sample_record, caplog):
    """
    If we call mark_uploaded() for a file that isn't in files_uploaded,
    a warning should be logged.
    """
    fake_path = "/file/not/in/record"
    sample_record.mark_uploaded(fake_path)

    warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Tried to mark non-existent file" in w for w in warnings)


def test_all_files_uploaded_true(sample_record):
    """
    all_files_uploaded() should return True if all files in the record are True.
    """
    sample_record.files_uploaded = {"/file/one": True, "/file/two": True}
    assert sample_record.all_files_uploaded() is True


def test_all_files_uploaded_false(sample_record):
    """
    all_files_uploaded() should return False if any file is not yet True.
    """
    sample_record.files_uploaded = {"/file/one": True, "/file/two": False}
    assert sample_record.all_files_uploaded() is False


def test_to_dict_from_dict_roundtrip():
    """
    to_dict() => from_dict() should preserve LocalRecord attributes.
    """
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
