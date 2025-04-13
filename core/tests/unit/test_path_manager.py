import pytest
from pathlib import Path
from unittest.mock import patch
from pyfakefs.fake_filesystem_unittest import Patcher

# Adjust these imports to your actual locations
from core.config.constants import (
    WATCH_DIR,
    DEST_DIR,
    RENAME_DIR,
    EXCEPTIONS_DIR,
    FILENAME_PATTERN,
    ID_SEP,
)
from core.storage.path_manager import PathManager


@pytest.fixture
def patch_settings_for_fs():
    """
    A fixture that temporarily sets the paths in settings to
    fake directories we'll create in pyfakefs. This ensures that
    PathManager.init_dirs() and others read the correct paths.
    """
    with patch("src.config.settings.WATCH_DIR", "/fake_watch"), patch(
        "src.config.settings.DEST_DIR", "/fake_dest"
    ), patch("src.config.settings.RENAME_DIR", "/fake_rename"), patch(
        "src.config.settings.EXCEPTIONS_DIR", "/fake_exceptions"
    ):
        yield  # proceed to the test


def test_init_dirs_pyfakefs():
    """
    Test that PathManager.init_dirs creates custom directories using pathlib in a fake filesystem.
    """
    with Patcher() as patcher:
        fake_dirs = [
            Path("/fake_watch"),
            Path("/fake_dest"),
            Path("/fake_rename"),
            Path("/fake_exceptions"),
        ]

        # Make sure none exist before
        for path in fake_dirs:
            assert not path.exists()

        # Create directories
        PathManager.init_dirs([str(p) for p in fake_dirs])

        # Assert all were created
        for path in fake_dirs:
            assert path.is_dir()


def test_get_unique_filename_pyfakefs():
    """
    Simulates existing files to test that get_unique_filename properly increments filenames.
    """
    with Patcher() as patcher:
        test_dir = Path("/some_dir")
        patcher.fs.create_dir(str(test_dir))

        # Simulate an existing file named with "-01"
        existing_file = test_dir / "existing_file-01.jpg"
        patcher.fs.create_file(str(existing_file))

        # Now ask for a new unique name
        result = PathManager.get_unique_filename(str(test_dir), "existing_file", ".jpg")

        # Expecting incremented suffix with '-02' (ID_SEP = '-')
        expected = test_dir / "existing_file-02.jpg"
        assert Path(result) == expected


def test_get_rename_path_pyfakefs():
    """
    Tests get_rename_path with a custom rename folder in a fake filesystem.
    """
    with Patcher() as patcher:
        fake_rename_dir = Path("/my_rename_test_dir")
        patcher.fs.create_dir(str(fake_rename_dir))
        patcher.fs.create_file(str(fake_rename_dir / "existing_file-01.jpg"))

        result = PathManager.get_rename_path(
            "existing_file.jpg", base_dir=str(fake_rename_dir)
        )

        # Assert it's in the fake directory and uses expected naming
        assert Path(result).parent == fake_rename_dir
        assert Path(result).name.startswith("existing_file-")
        assert Path(result).suffix == ".jpg"


def test_get_exception_path_pyfakefs():
    """
    Tests get_exception_path with a custom exceptions folder in a fake filesystem.
    """
    with Patcher() as patcher:
        fake_exceptions_dir = Path("/fake_exceptions")
        patcher.fs.create_dir(str(fake_exceptions_dir))
        patcher.fs.create_file(str(fake_exceptions_dir / "file_already-01.doc"))

        result = PathManager.get_exception_path(
            "file_already.doc", base_dir=str(fake_exceptions_dir)
        )

        assert Path(result).parent == fake_exceptions_dir
        assert Path(result).name.startswith("file_already-")
        assert Path(result).suffix == ".doc"


def test_get_record_path_pyfakefs(patch_settings_for_fs):
    """
    get_record_path() should create a directory under DEST_DIR
    with the correct substructure (institute, user, sample).
    """
    with Patcher() as patcher:
        patcher.fs.create_dir("/fake_dest")

        record_path = PathManager.get_record_path("mus-ipat-test_01")
        # Typically => "/fake_dest/IPAT/MUS/test_01", or something in that structure
        assert patcher.fs.isdir(record_path)
        assert "ipat" in record_path.lower()
        assert "mus" in record_path.lower()
        assert "test_01" in record_path.lower()
