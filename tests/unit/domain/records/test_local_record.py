import pytest
from pathlib import Path
from pyfakefs.fake_filesystem_unittest import Patcher

from dpost.domain.records.local_record import LocalRecord

pytestmark = pytest.mark.usefixtures("config_service")


@pytest.fixture
def sample_record():
    return LocalRecord(
        identifier="dev-jdoe-ipat-sample_1",
        datatype="tiff",
        date="20250405",
    )


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
    assert record.files_require_force == set()


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


def test_init_does_not_infer_separator_from_identifier_shape(caplog) -> None:
    """Do not auto-detect separators from identifier shape without explicit context."""
    caplog.set_level("WARNING")
    record = LocalRecord(identifier="dev:usr:inst:sample_1")

    assert record.id_separator == "-"
    assert record.user == "null"
    assert record.institute == "null"
    assert record.sample_name == "null"
    assert "does not conform" in caplog.text


def test_init_parses_identifier_when_separator_is_explicit() -> None:
    """Parse identifier segments when explicit id-separator context is provided."""
    record = LocalRecord(identifier="dev:usr:inst:sample_1", id_separator=":")

    assert record.id_separator == ":"
    assert record.user == "usr"
    assert record.institute == "inst"
    assert record.sample_name == "sample_1"


def test_init_rejects_empty_separator_value() -> None:
    """Reject record construction when explicit separator context is empty."""
    with pytest.raises(ValueError, match="id_separator must be provided explicitly"):
        LocalRecord(identifier="dev-usr-inst-sample_1", id_separator="")


def test_add_item_file_fs(sample_record):
    with Patcher() as patcher:
        fake_file = "/path/to/fake_file.tif"
        patcher.fs.create_file(fake_file, contents="fake data")
        sample_record.add_item(fake_file)

        resolved = str(Path(fake_file).resolve())
        assert resolved in sample_record.files_uploaded
        assert sample_record.files_uploaded[resolved] is False
        assert sample_record.files_require_force == set()


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
        assert sample_record.files_require_force == set()


def test_add_item_nested_dir(sample_record):
    with Patcher() as patcher:
        base_dir = "/nested"
        nested_file = "/nested/lvl1/lvl2/file.tif"
        patcher.fs.create_file(nested_file)

        sample_record.add_item(base_dir)

        resolved = str(Path(nested_file).resolve())
        assert resolved in sample_record.files_uploaded
        assert sample_record.files_uploaded[resolved] is False
        assert sample_record.files_require_force == set()


def test_add_same_file_twice(sample_record):
    with Patcher() as patcher:
        file_path = "/dup/file.tif"
        patcher.fs.create_file(file_path)

        sample_record.add_item(file_path)
        sample_record.add_item(file_path)

        resolved = str(Path(file_path).resolve())
        assert list(sample_record.files_uploaded.keys()).count(resolved) == 1
        assert resolved not in sample_record.files_require_force


def test_add_item_neither_file_nor_dir_fs(sample_record, caplog):
    caplog.set_level("WARNING")
    with Patcher():
        weird_path = "/some/odd/path"
        sample_record.add_item(weird_path)

        assert weird_path not in sample_record.files_uploaded
        warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
        assert any("neither a file nor a directory" in w for w in warnings)


def test_readd_uploaded_file_marks_force(sample_record):
    with Patcher() as patcher:
        file_path = "/force/file.tif"
        patcher.fs.create_file(file_path)

        sample_record.add_item(file_path)
        resolved = str(Path(file_path).resolve())
        sample_record.mark_uploaded(resolved)

        # adding again should mark for force upload
        sample_record.add_item(file_path)

        assert sample_record.files_uploaded[resolved] is False
        assert resolved in sample_record.files_require_force


def test_mark_uploaded(sample_record):
    fake_path = Path("/path/to/fake_file.tif").resolve()
    normalized = str(fake_path)
    sample_record.files_uploaded[normalized] = False
    sample_record.files_require_force.add(normalized)

    sample_record.mark_uploaded(fake_path)
    assert sample_record.files_uploaded[normalized] is True
    assert normalized not in sample_record.files_require_force


def test_mark_uploaded_nonexistent(sample_record, caplog):
    caplog.set_level("WARNING")
    fake_path = "/file/not/in/record"
    sample_record.mark_uploaded(fake_path)

    warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Tried to mark non-existent file" in w for w in warnings)


@pytest.mark.parametrize(
    "files, expected",
    [
        ({"/file/one": True, "/file/two": True}, True),
        ({"/file/one": True, "/file/two": False}, False),
        ({}, True),
    ],
)
def test_all_files_uploaded(sample_record, files, expected):
    sample_record.files_uploaded = files
    assert sample_record.all_files_uploaded() is expected


def test_mark_record_unsynced_marks_force(sample_record):
    sample_record.files_uploaded = {
        "/file/one": True,
        "/file/two": False,
    }

    sample_record.mark_record_unsynced()

    assert all(state is False for state in sample_record.files_uploaded.values())
    assert sample_record.files_require_force == set(sample_record.files_uploaded.keys())


def test_mark_file_as_unsynced_marks_force(sample_record):
    path = "/file/one"
    normalized = str(Path(path).resolve())
    sample_record.files_uploaded[normalized] = True

    sample_record.mark_file_as_unsynced(path)

    assert sample_record.files_uploaded[normalized] is False
    assert normalized in sample_record.files_require_force


def test_mark_file_as_unsynced_warns_for_unknown_file(sample_record, caplog):
    caplog.set_level("WARNING")
    sample_record.mark_file_as_unsynced("/missing/file.txt")

    warnings = [rec.message for rec in caplog.records if rec.levelname == "WARNING"]
    assert any("Tried to mark non-existent file as unsynced" in w for w in warnings)


def test_to_dict_from_dict_roundtrip():
    original = LocalRecord(
        identifier="rem-jdoe-ipat-sample_1",
        datatype="tiff",
        date="20250405",
        is_in_db=True,
        files_uploaded={"/file1.tif": True, "/file2.tif": False},
    )
    original.files_require_force.update({"/file1.tif"})

    data = original.to_dict()
    restored = LocalRecord.from_dict(data, id_separator="-")

    assert restored.identifier == original.identifier
    assert restored.user == original.user
    assert restored.institute == original.institute
    assert restored.sample_name == original.sample_name
    assert restored.datatype == original.datatype
    assert restored.date == original.date
    assert restored.is_in_db == original.is_in_db
    assert restored.files_uploaded == original.files_uploaded
    assert restored.files_require_force == original.files_require_force


def test_from_dict_requires_explicit_separator() -> None:
    """Reject persisted-record hydration without explicit separator context."""
    with pytest.raises(ValueError, match="id_separator must be provided explicitly"):
        LocalRecord.from_dict({"identifier": "dev-usr-inst-sample"})
