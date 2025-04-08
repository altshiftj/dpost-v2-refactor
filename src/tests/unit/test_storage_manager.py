from pathlib import Path
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager


def test_move_item_os_rename_success(tmp_path):
    # Create a source file with known content.
    src_file = tmp_path / "source.txt"
    src_file.write_text("hello")
    dest_file = tmp_path / "dest.txt"

    # Call the move_item method.
    StorageManager.move_item(str(src_file), str(dest_file))

    # Verify that the destination file exists with the same content and the source file is gone.
    assert dest_file.exists()
    assert dest_file.read_text() == "hello"
    assert not src_file.exists()


def test_move_item_fallback_shutil_move(tmp_path, monkeypatch):
    # Create a source file.
    src_file = tmp_path / "source.txt"
    src_file.write_text("fallback")
    dest_file = tmp_path / "dest.txt"

    # Patch Path.rename to simulate a failure.
    monkeypatch.setattr(
        Path,
        "rename",
        lambda self, dest: (_ for _ in ()).throw(OSError("Simulated rename failure")),
    )

    # Call the method, which should now fall back to shutil.move.
    StorageManager.move_item(str(src_file), str(dest_file))

    # Assert the move succeeded via fallback.
    assert dest_file.exists()
    assert dest_file.read_text() == "fallback"
    assert not src_file.exists()


def test_move_to_exception_folder(tmp_path, monkeypatch):
    # Create a source file.
    src_file = tmp_path / "source_exception.txt"
    src_file.write_text("exception")

    # Define a fake unique path function that returns a predictable destination.
    fake_unique_path = lambda name: str(tmp_path / ("exception_" + name))
    monkeypatch.setattr(
        PathManager, "get_exception_path", lambda name: fake_unique_path(name)
    )

    # Call the method to move the file to the exception folder.
    StorageManager.move_to_exception_folder(str(src_file), "testfile", ".txt")

    expected_dest = tmp_path / "exception_testfile.txt"
    assert expected_dest.exists()
    assert expected_dest.read_text() == "exception"
    assert not src_file.exists()


def test_move_to_rename_folder(tmp_path, monkeypatch):
    # Create a source file.
    src_file = tmp_path / "source_rename.txt"
    src_file.write_text("rename")

    # Patch get_rename_path to return a predictable path.
    fake_unique_path = lambda name, base_dir=None: str(tmp_path / ("rename_" + name))
    monkeypatch.setattr(
        PathManager,
        "get_rename_path",
        lambda name, base_dir=None: fake_unique_path(name, base_dir),
    )

    # Call the method to move the file to the rename folder.
    StorageManager.move_to_rename_folder(str(src_file), "testfile", ".txt")

    expected_dest = tmp_path / "rename_testfile.txt"
    assert expected_dest.exists()
    assert expected_dest.read_text() == "rename"
    assert not src_file.exists()


def test_move_to_record_folder(tmp_path, monkeypatch):
    # Arrange: create a source file.
    src_file = tmp_path / "source_record.txt"
    src_file.write_text("record")

    # Patch get_record_path to return a full file path rather than a directory.
    dest_file = tmp_path / "record_testfile_01.txt"
    monkeypatch.setattr(
        PathManager, "get_record_path", lambda filename_prefix: str(dest_file)
    )

    # Act: perform the move.
    StorageManager.move_to_record_folder(str(src_file), "testfile", ".txt")

    # Assert: file is moved and renamed.
    assert dest_file.exists()
    assert dest_file.read_text() == "record"
    assert not src_file.exists()
