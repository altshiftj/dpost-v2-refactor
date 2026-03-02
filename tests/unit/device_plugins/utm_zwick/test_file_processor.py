from pathlib import Path
from unittest.mock import patch, call
import pytest

from dpost.device_plugins.utm_zwick.file_processor import FileProcessorUTMZwick
from dpost.device_plugins.utm_zwick.settings import build_config


# ---------------------------------------------------------------------------
# Fixtures & boilerplate
# ---------------------------------------------------------------------------
@pytest.fixture
def processor():
    config = build_config()
    return FileProcessorUTMZwick(device_config=config)


# ---------------------------------------------------------------------------
# Pre-processing behavior (zs2 staged, sentinel xlsx triggers finalize)
# ---------------------------------------------------------------------------


def test_preprocessing_stages_until_sentinel_xlsx(tmp_path, processor):
    zs2 = tmp_path / "usr-inst-sample_a.zs2"
    xlsx = tmp_path / "usr-inst-sample_a.xlsx"
    zs2.write_text("raw")
    xlsx.write_text("results")

    r1 = processor.device_specific_preprocessing(str(zs2))
    assert r1 is None

    r2 = processor.device_specific_preprocessing(str(xlsx))
    assert r2 is not None
    assert r2.effective_path == str(xlsx)


def test_preprocessing_rejects_or_ignores_non_sentinel(tmp_path, processor):
    csv = tmp_path / "usr-inst-sample_a.csv"
    txt = tmp_path / "usr-inst-sample_a-01.txt"
    csv.write_text("results")
    txt.write_text("snap")

    r1 = processor.device_specific_preprocessing(str(csv))
    r2 = processor.device_specific_preprocessing(str(txt))

    assert r1 is None
    assert r2 is None


def test_preprocessing_ignores_sentinel_without_zs2(tmp_path, processor):
    xlsx = tmp_path / "usr-inst-sample_a.xlsx"
    xlsx.write_text("results")

    r1 = processor.device_specific_preprocessing(str(xlsx))
    assert r1 is None


def test_preprocessing_requires_exact_stem_match(tmp_path, processor):
    """Do not pair artefacts when stems differ in casing."""
    zs2 = tmp_path / "Usr-Inst-SampleA.zs2"
    xlsx = tmp_path / "usr-inst-samplea.xlsx"
    zs2.write_text("raw")
    xlsx.write_text("results")

    first = processor.device_specific_preprocessing(str(zs2))
    second = processor.device_specific_preprocessing(str(xlsx))

    assert first is None
    assert second is None


# ---------------------------------------------------------------------------
# Processing flow (zs2 + sentinel xlsx)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("zs2_name", "xlsx_name"),
    [
        ("usr-inst-sample_a.zs2", "usr-inst-sample_a.xlsx"),
        ("Usr-Inst-test_sample.zs2", "Usr-Inst-test_sample.xlsx"),
    ],
    ids=["normalized-prefix", "mixed-case-prefix"],
)
def test_device_specific_processing_moves_staged_series(
    tmp_path,
    processor,
    zs2_name: str,
    xlsx_name: str,
):
    """Move staged `.zs2` and sentinel `.xlsx` artefacts into record storage."""
    zs2 = tmp_path / zs2_name
    xlsx = tmp_path / xlsx_name

    zs2.write_text("raw-bytes")
    xlsx.write_text("xlsx-content")

    processor.device_specific_preprocessing(str(zs2))
    processor.device_specific_preprocessing(str(xlsx))

    record_dir = tmp_path / "record"
    record_dir.mkdir()
    processor.configure_runtime_context(id_separator=":")

    unique_paths = [
        str(record_dir / "prefix-01.zs2"),
        str(record_dir / "prefix-01.xlsx"),
    ]

    with (
        patch(
            f"{FileProcessorUTMZwick.__module__}.get_unique_filename",
            side_effect=unique_paths,
        ) as mock_unique,
        patch(f"{FileProcessorUTMZwick.__module__}.move_item") as mock_move,
    ):
        output = processor.device_specific_processing(
            str(xlsx), str(record_dir), "prefix", ".xlsx"
        )

    assert Path(output.final_path) == record_dir
    assert output.datatype == "xlsx"
    assert mock_unique.call_args_list == [
        call(str(record_dir), "prefix", ".zs2", id_separator=":"),
        call(str(record_dir), "prefix", ".xlsx", id_separator=":"),
    ]
    assert mock_move.call_args_list == [
        call(str(zs2), unique_paths[0]),
        call(str(xlsx), unique_paths[1]),
    ]


def test_device_specific_processing_raises_without_staging(tmp_path, processor):
    """Raise when processing is requested without prior staged series state."""
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    # No prior preprocessing for this prefix -> should raise
    with pytest.raises(KeyError):
        processor.device_specific_processing(
            str(tmp_path / "ghost.xlsx"), str(record_dir), "prefix", ".xlsx"
        )


def test_device_specific_processing_requires_explicit_separator_context(
    tmp_path: Path,
) -> None:
    """Reject processing when runtime separator context was not configured."""
    processor = FileProcessorUTMZwick(device_config=build_config())
    zs2 = tmp_path / "usr-inst-sample_a.zs2"
    xlsx = tmp_path / "usr-inst-sample_a.xlsx"
    zs2.write_text("raw-bytes")
    xlsx.write_text("xlsx-content")

    processor.device_specific_preprocessing(str(zs2))
    processor.device_specific_preprocessing(str(xlsx))

    record_dir = tmp_path / "record"
    record_dir.mkdir()

    with pytest.raises(RuntimeError, match="id_separator runtime context"):
        processor.device_specific_processing(
            str(xlsx), str(record_dir), "prefix", ".xlsx"
        )
