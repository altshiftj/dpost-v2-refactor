from pathlib import Path
import pytest
from unittest.mock import patch
from src.processing.file_processor_sem import SEMFileProcessor
from src.records.local_record import LocalRecord

# -----------------------
# Fixtures and Dummies
# -----------------------

@pytest.fixture
def processor():
    return SEMFileProcessor()

@pytest.fixture
def dummy_record():
    return LocalRecord(
        identifier="rem-mus-ipat-sample_a",
        name="sample_a",
        datatype="tiff",
        date="20250405"
    )

# -----------------------
# Tests for device_specific_preprocessing
# -----------------------

def test_device_specific_preprocessing_no_digit(processor):
    # File name does not end with a digit -> should return original path.
    original_path = "/path/to/image.tif"
    with patch.object(Path, "rename") as mock_rename:
        result = processor.device_specific_preprocessing(original_path)
        assert result == original_path
        mock_rename.assert_not_called()

def test_device_specific_preprocessing_with_digit(processor):
    # File name ends with a digit: "image3.tif" should be renamed to "image.tif"
    original_path = "/path/to/image3.tif"
    expected_path = str(Path("/path/to/image.tif"))
    with patch.object(Path, "rename") as mock_rename:
        result = processor.device_specific_preprocessing(original_path)
        # Check that rename was called exactly once.
        mock_rename.assert_called_once()
        # Convert the argument to string and compare with expected_path.
        called_arg = mock_rename.call_args[0][0]
        assert str(called_arg) == expected_path
        assert result == expected_path

# -----------------------
# Tests for is_valid_datatype, is_appendable, etc.
# (The remaining tests can remain the same because they operate on strings or use tmp_path.)
# -----------------------

def test_is_valid_datatype_tiff_file(processor):
    path = "/path/to/sample.tif"
    assert processor.is_valid_datatype(path) is True

def test_is_valid_datatype_tiff_file_case_insensitive(processor):
    path = "/path/to/sample.TIFF"
    assert processor.is_valid_datatype(path) is True

def test_is_valid_datatype_elid_directory(tmp_path, processor):
    elid_dir = tmp_path / "elid_folder"
    elid_dir.mkdir()
    (elid_dir / "data.elid").write_text("dummy")
    assert processor.is_valid_datatype(str(elid_dir)) is True

def test_is_valid_datatype_invalid(processor, tmp_path):
    non_valid_dir = tmp_path / "nonvalid"
    non_valid_dir.mkdir()
    (non_valid_dir / "file.txt").write_text("dummy")
    invalid_file = "/path/to/sample.txt"
    assert processor.is_valid_datatype(str(non_valid_dir)) is False
    assert processor.is_valid_datatype(invalid_file) is False

def test_is_appendable_returns_false_for_elid(dummy_record, processor):
    dummy_record.files_uploaded = {"/path/to/file.elid": False}
    result = processor.is_appendable(dummy_record, "sample_a", ".tif")
    assert result is False

def test_is_appendable_returns_false_for_empty_extension(dummy_record, processor):
    dummy_record.files_uploaded = {}
    result = processor.is_appendable(dummy_record, "sample_a", "")
    assert result is False

def test_is_appendable_returns_true(dummy_record, processor):
    dummy_record.files_uploaded = {"/path/to/file.tif": False}
    result = processor.is_appendable(dummy_record, "sample_a", ".tif")
    assert result is True

def test_device_specific_processing_tif_branch(processor, tmp_path):
    record_dir = tmp_path / "record_folder"
    record_dir.mkdir()
    
    src_file = str(tmp_path / "sample.tif")
    with open(src_file, "w") as f:
        f.write("dummy image data")
    
    filename_prefix = "sample"
    extension = ".tif"
    
    unique_filename = str(record_dir / "sample-01.tif")
    with patch("src.processing.file_processor_sem.PathManager.get_unique_filename", return_value=unique_filename) as mock_get_unique:
        with patch("src.processing.file_processor_sem.StorageManager.move_item") as mock_move:
            result, datatype = processor.device_specific_processing(src_file, str(record_dir), filename_prefix, extension)
            assert result == unique_filename
            assert datatype == "img"
            mock_move.assert_called_once_with(src_file, unique_filename)
            mock_get_unique.assert_called_once_with(str(record_dir), filename_prefix, extension)
