"""Branch-focused tests for DSV Horiba processor helper and error paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from dpost.device_plugins.dsv_horiba.file_processor import FileProcessorDSVHoriba
from dpost.device_plugins.dsv_horiba.settings import build_config
from dpost.domain.records.local_record import LocalRecord


@pytest.fixture
def processor() -> FileProcessorDSVHoriba:
    """Return DSV processor configured for branch tests."""
    return FileProcessorDSVHoriba(build_config())


def test_configure_runtime_context_sets_missing_separator_and_exception_dir() -> None:
    """Populate missing runtime naming/exception context but preserve explicit overrides."""
    processor = FileProcessorDSVHoriba(build_config())
    processor.configure_runtime_context(id_separator="__", exception_dir="C:/exceptions")

    assert processor._id_separator == "__"  # noqa: SLF001
    assert processor._exception_dir == "C:/exceptions"  # noqa: SLF001

    explicit = FileProcessorDSVHoriba(build_config())
    explicit._id_separator = "-"  # noqa: SLF001
    explicit._exception_dir = "C:/explicit"  # noqa: SLF001
    explicit.configure_runtime_context(id_separator="__", exception_dir="C:/injected")

    assert explicit._id_separator == "-"  # noqa: SLF001
    assert explicit._exception_dir == "C:/explicit"  # noqa: SLF001


def test_probe_file_returns_unknown_when_text_read_fails(
    tmp_path: Path,
    processor: FileProcessorDSVHoriba,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return unknown decision when text-prefix read fails."""
    export_path = tmp_path / "sample.txt"
    export_path.write_text("content", encoding="utf-8")
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("decode failed")),
    )

    result = processor.probe_file(str(export_path))

    assert result.is_match() is False
    assert result.is_mismatch() is False
    assert result.reason == "decode failed"


def test_probe_file_returns_match_for_marker_text(
    tmp_path: Path,
    processor: FileProcessorDSVHoriba,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return positive probe match when dissolver markers are present."""
    export_path = tmp_path / "sample.txt"
    export_path.write_text("content", encoding="utf-8")
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: "dissolution release rpm medium horiba",
    )

    result = processor.probe_file(str(export_path))

    assert result.is_match() is True


def test_identity_helpers_are_stable(processor: FileProcessorDSVHoriba) -> None:
    """Expose stable plugin identity and appendability behavior."""
    record = LocalRecord(identifier="dev-user-ipat-sample")

    assert processor.get_device_id() == "dsv_horiba"
    assert processor.is_appendable(record, "prefix", ".txt") is True


def test_processing_falls_back_to_single_file_move_when_batch_missing(
    tmp_path: Path,
    processor: FileProcessorDSVHoriba,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Move file directly when no dissolved batch context is available."""
    src = tmp_path / "sample.txt"
    src.write_text("export")
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    destination = record_dir / "prefix-01.txt"
    moved: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.get_unique_filename",
        lambda _record_path, _file_id, _extension: str(destination),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.move_item",
        lambda src_path, dest_path: moved.append((src_path, dest_path)),
    )

    output = processor.device_specific_processing(
        str(src),
        str(record_dir),
        "prefix",
        ".txt",
    )

    assert output.final_path == str(destination)
    assert moved == [(str(src), str(destination))]


def test_processing_tolerates_raw_unlink_failures(
    tmp_path: Path,
    processor: FileProcessorDSVHoriba,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continue processing when deleting staged raw files fails."""
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    raw_path = watch_dir / "sample.wdb"
    raw_path.write_bytes(b"raw")
    txt_path = watch_dir / "sample.txt"
    txt_path.write_text("dissolution release rpm medium horiba", encoding="utf-8")
    processor._batches["sample"] = {
        "files": [raw_path, txt_path],
        "t": 0.0,
        "ready": True,
    }
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.get_unique_filename",
        lambda _record_path, _file_id, _extension: str(record_dir / "prefix-01.txt"),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.move_item",
        lambda src_path, dest_path: Path(dest_path).write_text(
            Path(src_path).read_text(encoding="utf-8"),
            encoding="utf-8",
        ),
    )
    monkeypatch.setattr(
        Path,
        "unlink",
        lambda _self, missing_ok=True: (_ for _ in ()).throw(OSError("unlink failed")),
    )

    output = processor.device_specific_processing(
        str(txt_path),
        str(record_dir),
        "prefix",
        ".txt",
    )

    assert Path(output.final_path) == record_dir
    assert (record_dir / "prefix_raw_data.zip").exists()


def test_purge_orphans_logs_warning_when_move_to_exception_fails(
    tmp_path: Path,
    processor: FileProcessorDSVHoriba,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Swallow orphan-move failures while still dropping stale batch entries."""
    processor.device_config.batch.ttl_seconds = 5
    now = 100.0
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()
    stale = watch_dir / "stale.wdb"
    stale.write_bytes(b"raw")
    processor._batches["sample"] = {
        "files": [stale],
        "t": now - 10,
        "ready": False,
    }
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.time.time",
        lambda: now,
    )
    monkeypatch.setattr(
        "dpost.device_plugins.dsv_horiba.file_processor.move_to_exception_folder",
        lambda _path, **_kwargs: (_ for _ in ()).throw(RuntimeError("move failed")),
    )

    processor._purge_orphans()

    assert "sample" not in processor._batches
