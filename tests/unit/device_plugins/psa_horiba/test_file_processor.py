from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dpost.device_plugins.psa_horiba.file_processor import FileProcessorPSAHoriba
from dpost.device_plugins.psa_horiba.settings import build_config


@pytest.fixture
def processor() -> FileProcessorPSAHoriba:
    return FileProcessorPSAHoriba(build_config())


def test_sentinel_flush_creates_numbered_artifacts(tmp_path, processor, config_service):
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()

    # First pair: native NGB arrives before exported CSV
    ngb_first = watch_dir / "s01.ngb"
    ngb_first.write_bytes(b"ngb-first")
    csv_first = watch_dir / "s01.csv"
    csv_first.write_text("Probenname\tBucket Sample\nX(mm)\tValue\n", encoding="utf-8")

    assert processor.device_specific_preprocessing(str(ngb_first)) is None
    assert processor.device_specific_preprocessing(str(csv_first)) is None

    # Sentinel pair: exported CSV followed by native NGB (triggers flush)
    csv_sentinel = watch_dir / "sentinel.csv"
    csv_sentinel.write_text("Probenname;Final Sample\nX(mm);Value\n", encoding="utf-8")
    assert processor.device_specific_preprocessing(str(csv_sentinel)) is None

    ngb_sentinel = watch_dir / "sentinel.ngb"
    ngb_sentinel.write_bytes(b"ngb-second")

    advertised = processor.device_specific_preprocessing(str(ngb_sentinel))
    expected_prefix = "Final Sample"
    # Staging approach advertises a folder named '<prefix>.__staged__<n>'
    assert advertised is not None
    advertised_path = Path(advertised.effective_path)
    assert advertised_path.is_dir()
    assert advertised_path.name.startswith(f"{expected_prefix}.__staged__")

    output = processor.device_specific_processing(
        str(advertised_path), str(record_dir), advertised_path.stem, ""
    )
    assert Path(output.final_path) == record_dir
    assert output.datatype == "psa"

    produced = sorted(p.name for p in record_dir.iterdir())
    assert produced == [
        f"{expected_prefix}-01.csv",
        f"{expected_prefix}-01.zip",
        f"{expected_prefix}-02.csv",
        f"{expected_prefix}-02.zip",
    ]

    first_csv = record_dir / f"{expected_prefix}-01.csv"
    first_zip = record_dir / f"{expected_prefix}-01.zip"
    second_zip = record_dir / f"{expected_prefix}-02.zip"

    # CSV content is preserved (no delimiter conversion) and originals removed
    assert "Probenname\tBucket Sample" in first_csv.read_text(encoding="utf-8")
    for original in (csv_first, csv_sentinel, ngb_first, ngb_sentinel):
        assert not original.exists()

    with zipfile.ZipFile(first_zip) as zf:
        assert zf.namelist() == [f"{expected_prefix}-01.ngb"]
        assert zf.read(f"{expected_prefix}-01.ngb") == b"ngb-first"

    with zipfile.ZipFile(second_zip) as zf:
        assert zf.namelist() == [f"{expected_prefix}-02.ngb"]
        assert zf.read(f"{expected_prefix}-02.ngb") == b"ngb-second"


def test_preprocessing_is_idempotent_for_sentinel(tmp_path, processor):
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    csv_sentinel = watch_dir / "flush.csv"
    csv_sentinel.write_text("Probenname;One Shot\nX(mm);Value\n", encoding="utf-8")
    assert processor.device_specific_preprocessing(str(csv_sentinel)) is None

    ngb_sentinel = watch_dir / "flush.ngb"
    ngb_sentinel.write_bytes(b"payload")

    advertised_first = processor.device_specific_preprocessing(str(ngb_sentinel))
    advertised_second = processor.device_specific_preprocessing(str(ngb_sentinel))

    assert advertised_first is not None
    assert advertised_second is not None
    assert advertised_first.effective_path == advertised_second.effective_path
