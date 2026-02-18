from __future__ import annotations

from pathlib import Path


from ipat_watchdog.device_plugins.dsv_horiba.file_processor import FileProcessorDSVHoriba
from ipat_watchdog.device_plugins.dsv_horiba.settings import build_config


def test_preprocessing_returns_passthrough_when_ready(tmp_path):
    processor = FileProcessorDSVHoriba(build_config())
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    raw_path = watch_dir / "sample.wdb"
    raw_path.write_bytes(b"raw")
    export_path = watch_dir / "sample.txt"
    export_path.write_text("dissolution rpm medium", encoding="utf-8")

    assert processor.device_specific_preprocessing(str(raw_path)) is None

    result = processor.device_specific_preprocessing(str(export_path))
    assert result is not None
    assert result.effective_path == str(export_path)


def test_processing_zips_raw_and_moves_txt(tmp_path, config_service):
    processor = FileProcessorDSVHoriba(build_config())
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()

    raw_path = watch_dir / "sample.wdb"
    raw_path.write_bytes(b"raw")
    export_path = watch_dir / "sample.txt"
    export_path.write_text("dissolution rpm medium", encoding="utf-8")

    processor._batches["sample"] = {
        "files": [raw_path, export_path],
        "t": 0.0,
        "ready": True,
    }

    output = processor.device_specific_processing(
        str(export_path),
        str(record_dir),
        "prefix",
        ".txt",
    )

    assert Path(output.final_path) == record_dir
    assert (record_dir / "prefix_raw_data.zip").exists()
    assert not raw_path.exists()
    assert any(p.suffix == ".txt" for p in record_dir.iterdir())


def test_purge_orphans_moves_files(tmp_path, monkeypatch):
    processor = FileProcessorDSVHoriba(build_config())
    processor.device_config.batch.ttl_seconds = 5

    now = 100.0
    monkeypatch.setattr(
        "ipat_watchdog.device_plugins.dsv_horiba.file_processor.time.time",
        lambda: now,
    )

    moved: list[str] = []
    monkeypatch.setattr(
        "ipat_watchdog.device_plugins.dsv_horiba.file_processor.move_to_exception_folder",
        lambda path: moved.append(path),
    )

    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    raw_path = watch_dir / "sample.wdb"
    raw_path.write_bytes(b"raw")

    processor._batches["sample"] = {
        "files": [raw_path],
        "t": now - 10,
        "ready": False,
    }

    processor._purge_orphans()

    assert "sample" not in processor._batches
    assert str(raw_path) in moved


def test_probe_file_flags_mismatch_and_unknown(tmp_path):
    processor = FileProcessorDSVHoriba(build_config())
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    raw_path = watch_dir / "sample.wdb"
    raw_path.write_bytes(b"raw")
    export_path = watch_dir / "sample.txt"
    export_path.write_text("no markers", encoding="utf-8")
    mismatch_path = watch_dir / "sample.csv"
    mismatch_path.write_text("data", encoding="utf-8")

    assert processor.probe_file(str(raw_path)).is_definitive() is False
    assert processor.probe_file(str(export_path)).is_match() is False
    assert processor.probe_file(str(mismatch_path)).is_mismatch() is True
