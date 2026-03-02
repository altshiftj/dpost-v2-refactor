from pathlib import Path
from unittest.mock import patch
import pytest

from dpost.domain.records.local_record import LocalRecord
from dpost.device_plugins.sem_phenomxl2.file_processor import FileProcessorSEMPhenomXL2
from dpost.device_plugins.sem_phenomxl2.settings import build_config

pytestmark = pytest.mark.usefixtures("config_service")


# ---------------------------------------------------------------------------
# Fixtures & boilerplate
# ---------------------------------------------------------------------------


@pytest.fixture
def processor():
    config = build_config()
    return FileProcessorSEMPhenomXL2(device_config=config)


@pytest.fixture
def dummy_record():
    return LocalRecord(
        identifier="rem-mus-ipat-sample_a",
        sample_name="sample_a",
        datatype="tiff",
        date="20250405",
    )


# ---------------------------------------------------------------------------
# Pre-processing
# ---------------------------------------------------------------------------


def test_device_specific_preprocessing_no_digit(processor):
    path = "/path/to/image.tif"
    with patch("pathlib.Path.rename") as mock_rename:
        result = processor.device_specific_preprocessing(path)
        assert result.effective_path == path
        assert result.prefix_override is None
        mock_rename.assert_not_called()


def test_device_specific_preprocessing_with_digit(processor):
    path = "/path/to/image3.tif"
    result = processor.device_specific_preprocessing(path)
    assert result.effective_path == path
    assert result.prefix_override == "image"


def test_configure_runtime_context_sets_missing_separator_only() -> None:
    """Apply runtime separator once and preserve explicit overrides."""
    processor = FileProcessorSEMPhenomXL2(device_config=build_config())
    processor.configure_runtime_context(id_separator=":")
    assert processor._id_separator == ":"  # noqa: SLF001

    processor._id_separator = "-"  # noqa: SLF001
    processor.configure_runtime_context(id_separator="|")
    assert processor._id_separator == "-"  # noqa: SLF001


# ---------------------------------------------------------------------------
# Appendable logic
# ---------------------------------------------------------------------------


def test_is_appendable_false_for_elid(dummy_record, processor):
    dummy_record.files_uploaded = {"/some/file.elid": False}
    assert not processor.is_appendable(dummy_record, "prefix", ".tif")


def test_is_appendable_true(dummy_record, processor):
    dummy_record.files_uploaded = {"/some/file.tif": False}
    assert processor.is_appendable(dummy_record, "prefix", ".tif")


# ---------------------------------------------------------------------------
# Processing logic
# ---------------------------------------------------------------------------


def test_device_specific_processing_tif_branch(tmp_path, processor):
    src_file = tmp_path / "image.tif"
    src_file.write_text("image data")

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    unique_file = record_dir / "prefix-01.tif"

    module_path = FileProcessorSEMPhenomXL2.__module__
    with (
        patch(
            f"{module_path}.get_unique_filename",
            return_value=str(unique_file),
        ) as mock_unique,
        patch(f"{module_path}.move_item") as mock_move,
    ):

        output = processor.device_specific_processing(
            str(src_file), str(record_dir), "prefix", ".tif"
        )

        assert output.final_path == str(unique_file)
        assert output.datatype == "img"
        mock_unique.assert_called_once_with(
            str(record_dir),
            "prefix",
            ".tif",
            id_separator="-",
        )
        mock_move.assert_called_once_with(src_file, str(unique_file))


def test_device_specific_processing_elid_branch(tmp_path, processor):
    """
    Verifies that:
      • export/ gets zipped to <prefix>.zip via shutil.make_archive
      • .odt / .elid are renamed to <prefix>.* and moved
      • source folder is deleted (shutil.rmtree)
      • function returns the record directory path
    """
    # --- build dummy ELID directory -----------------------------------------
    elid_dir = tmp_path / "elid"
    export_dir = elid_dir / "export"
    export_dir.mkdir(parents=True)

    # dummy payload
    (export_dir / "dummy.dat").write_text("42")
    (elid_dir / "sample.elid").write_text("meta")
    (elid_dir / "sample.odt").write_text("note")

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    with (
        patch(
            f"{FileProcessorSEMPhenomXL2.__module__}.shutil.make_archive"
        ) as mock_archive,
        patch(f"{FileProcessorSEMPhenomXL2.__module__}.move_item") as mock_move,
        patch(f"{FileProcessorSEMPhenomXL2.__module__}.shutil.rmtree") as mock_rmtree,
    ):

        mock_archive.return_value = str(record_dir / "prefix.zip")

        output = processor.device_specific_processing(
            str(elid_dir), str(record_dir), "prefix", ".elid"
        )

        assert Path(output.final_path) == record_dir
        assert output.datatype == "elid"

        # ---- archive call ---------------------------------------------------
        # make_archive is called with the *base* path (no .zip suffix)
        expected_base = str(record_dir / "prefix")
        mock_archive.assert_called_once_with(
            expected_base, "zip", root_dir=str(export_dir)
        )

        # ---- descriptor renaming / move ------------------------------------
        dest_paths = [Path(call.args[1]) for call in mock_move.call_args_list]
        assert record_dir / "prefix.odt" in dest_paths
        assert record_dir / "prefix.elid" in dest_paths
        assert len(dest_paths) == 2  # exactly the two descriptor files

        # ---- source folder cleanup -----------------------------------------
        mock_rmtree.assert_called_once_with(elid_dir)
