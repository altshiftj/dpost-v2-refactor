import os
from pathlib import Path
from unittest.mock import patch
import pytest

from devices.SEM_TischREM_BLB.file_processor_tischrem import FileProcessorTischREM
from records.local_record import LocalRecord
import storage.filesystem_utils as fs_utils
from config.settings_store import SettingsStore


@pytest.fixture(autouse=True)
def _init_test_settings(tmp_settings):
    # Automatically initializes SettingsStore for all tests
    pass


@pytest.fixture
def processor():
    return FileProcessorTischREM()


@pytest.fixture
def dummy_record():
    return LocalRecord(
        identifier="rem-mus-ipat-sample_a",
        sample_name="sample_a",
        datatype="tiff",
        date="20250405",
    )


# -----------------------
# Preprocessing tests
# -----------------------

def test_device_specific_preprocessing_no_digit(processor):
    path = "/path/to/image.tif"
    with patch("pathlib.Path.rename") as mock_rename:
        result = processor.device_specific_preprocessing(path)
        assert result == path
        mock_rename.assert_not_called()


def test_device_specific_preprocessing_with_digit(processor):
    path = "/path/to/image3.tif"
    expected = str(Path("/path/to/image.tif"))

    with patch("pathlib.Path.rename") as mock_rename:
        result = processor.device_specific_preprocessing(path)
        assert result == expected
        mock_rename.assert_called_once()
        assert str(mock_rename.call_args[0][0]) == expected


# -----------------------
# Datatype validation
# -----------------------

def test_is_valid_datatype_tiff_file(processor):
    assert processor.is_valid_datatype("/some/file.tif") is True


def test_is_valid_datatype_tiff_case_insensitive(processor):
    assert processor.is_valid_datatype("/some/file.TIFF") is True


def test_is_valid_datatype_elid_directory(tmp_path, processor):
    elid_dir = tmp_path / "elid_dir"
    elid_dir.mkdir()
    (elid_dir / "file.elid").write_text("data")
    assert processor.is_valid_datatype(str(elid_dir)) is True


def test_is_valid_datatype_invalid(tmp_path, processor):
    non_elid_dir = tmp_path / "not_elid"
    non_elid_dir.mkdir()
    (non_elid_dir / "file.txt").write_text("data")
    assert not processor.is_valid_datatype(str(non_elid_dir))
    assert not processor.is_valid_datatype("/path/to/file.txt")


# -----------------------
# Appendable logic
# -----------------------

def test_is_appendable_false_for_elid(dummy_record, processor):
    dummy_record.files_uploaded = {"/some/file.elid": False}
    assert not processor.is_appendable(dummy_record, "prefix", ".tif")


def test_is_appendable_false_for_empty_extension(dummy_record, processor):
    dummy_record.files_uploaded = {}
    assert not processor.is_appendable(dummy_record, "prefix", "")


def test_is_appendable_true(dummy_record, processor):
    dummy_record.files_uploaded = {"/some/file.tif": False}
    assert processor.is_appendable(dummy_record, "prefix", ".tif")


# -----------------------
# Processing logic
# -----------------------

def test_device_specific_processing_tif_branch(tmp_path, processor):
    src_file = tmp_path / "image.tif"
    src_file.write_text("image data")

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    unique_file = record_dir / "prefix-01.tif"

    with patch("devices.SEM_TischREM_BLB.file_processor_tischrem.get_unique_filename", return_value=str(unique_file)) as mock_unique, \
         patch("devices.SEM_TischREM_BLB.file_processor_tischrem.move_item") as mock_move:

        result, dtype = processor.device_specific_processing(
            str(src_file), str(record_dir), "prefix", ".tif"
        )

        assert result == str(unique_file)
        assert dtype == "img"
        mock_unique.assert_called_once_with(str(record_dir), "prefix", ".tif")
        mock_move.assert_called_once_with(src_file, str(unique_file))


def test_device_specific_processing_elid_branch(tmp_path, processor):
    elid_dir = tmp_path / "elid"
    elid_dir.mkdir()
    (elid_dir / "file.elid").write_text("data")
    (elid_dir / "notes.odt").write_text("note")

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    with patch("devices.SEM_TischREM_BLB.file_processor_tischrem.move_item") as mock_move, \
         patch("devices.SEM_TischREM_BLB.file_processor_tischrem.remove_directory_if_empty") as mock_remove:

        result_path, dtype = processor.device_specific_processing(
            str(elid_dir), str(record_dir), "prefix", ".elid"
        )

        assert Path(result_path) == record_dir
        assert dtype == "elid"
        assert mock_move.call_count >= 2
        mock_remove.assert_called_with(elid_dir)

def test_device_specific_processing_flattens_elid_subfolders(tmp_path, processor):
    # Setup mock elid folder structure
    elid_dir = tmp_path / "elid"
    export_dir = elid_dir / "export" / "Image_1_analysis_1_spot"
    export_dir.mkdir(parents=True)

    # Create nested files
    (export_dir / "quantification.csv").write_text("some data")
    (export_dir / "spectrum.tiff").write_text("spectrum image")
    (elid_dir / "test.elid").write_text("elid meta")
    (elid_dir / "test.odt").write_text("doc")

    record_dir = tmp_path / "RECORD"
    record_dir.mkdir()

    with patch("devices.SEM_TischREM_BLB.file_processor_tischrem.move_item") as mock_move, \
         patch("devices.SEM_TischREM_BLB.file_processor_tischrem.remove_directory_if_empty") as mock_remove:

        result_path, dtype = processor.device_specific_processing(
            str(elid_dir), str(record_dir), "REM-testingelid", ".elid"
        )

        assert Path(result_path) == record_dir
        assert dtype == "elid"

        moved_files = [str(call.args[1]) for call in mock_move.call_args_list]

        expected_elid_folder_files = [
            str(elid_dir / "Image_1_analysis_1_spot_quantification.csv"),
            str(elid_dir / "Image_1_analysis_1_spot_spectrum.tiff"),
            str(elid_dir / "REM-testingelid.elid"),
            str(elid_dir / "REM-testingelid.odt"),
        ]

        expected_record_folder_files = [
            str(record_dir / "test.elid"),
            str(record_dir / "test.odt"),
        ]

        # All expected elid folder files were created
        for expected_file in expected_elid_folder_files:
            assert expected_file in moved_files

        # Then those renamed .elid and .odt files were moved again to record
        for expected_file in expected_record_folder_files:
            assert expected_file in moved_files

        mock_remove.assert_called_with(elid_dir)
