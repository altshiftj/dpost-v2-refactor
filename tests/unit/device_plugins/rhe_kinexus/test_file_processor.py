from __future__ import annotations

from collections import deque
import os
from pathlib import Path

import pytest

from dpost.device_plugins.rhe_kinexus.file_processor import (
    FileProcessorRHEKinexus,
    _FolderState,
    _Pair,
    _PendingRaw,
    _Sentinel,
)
from dpost.device_plugins.rhe_kinexus.settings import build_config


def test_preprocessing_stages_and_is_idempotent(tmp_path):
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    export_path = watch_dir / "sample.csv"
    export_path.write_text("kinexus", encoding="utf-8")
    raw_path = watch_dir / "sample.rdf"
    raw_path.write_bytes(b"raw")

    assert processor.device_specific_preprocessing(str(export_path)) is None

    advertised = processor.device_specific_preprocessing(str(raw_path))
    assert advertised is not None
    stage_dir = Path(advertised.effective_path)
    assert stage_dir.is_dir()
    assert stage_dir.name.startswith("sample.__staged__")

    advertised_again = processor.device_specific_preprocessing(str(raw_path))
    assert advertised_again is not None
    assert advertised_again.effective_path == advertised.effective_path


def test_reconstruct_batch_from_stage_pairs_by_stem(tmp_path):
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    stage_dir = tmp_path / "Batch.__staged__1"
    stage_dir.mkdir()

    export_a = stage_dir / "a.csv"
    export_a.write_text("kinexus", encoding="utf-8")
    export_b = stage_dir / "b.csv"
    export_b.write_text("kinexus", encoding="utf-8")
    native_a = stage_dir / "a.rdf"
    native_a.write_bytes(b"raw")
    native_c = stage_dir / "c.rdf"
    native_c.write_bytes(b"raw")

    batch = processor._reconstruct_batch_from_stage(stage_dir)

    stems = {(pair.export_path.stem, pair.raw_path.stem) for pair in batch.pairs}
    assert ("a", "a") in stems
    assert len(batch.pairs) == 2


def test_device_specific_processing_reconstructs_from_stage(tmp_path, config_service):
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    stage_dir = tmp_path / "Batch.__staged__1"
    stage_dir.mkdir()

    export_path = stage_dir / "sample.csv"
    export_path.write_text("kinexus", encoding="utf-8")
    raw_path = stage_dir / "sample.rdf"
    raw_path.write_bytes(b"raw")

    record_dir = tmp_path / "record"

    output = processor.device_specific_processing(
        str(stage_dir),
        str(record_dir),
        "prefix",
        "",
    )

    assert Path(output.final_path) == record_dir
    assert (record_dir / "prefix-01.csv").exists()
    assert (record_dir / "prefix-01.zip").exists()


def test_purge_stale_moves_pending_bucket_sentinel_and_stage(tmp_path, monkeypatch):
    processor = FileProcessorRHEKinexus(
        build_config(),
        id_separator="-",
        exception_dir=str(tmp_path / "exceptions"),
    )
    processor.device_config.batch.ttl_seconds = 5

    now = 100.0
    module_path = FileProcessorRHEKinexus.__module__
    monkeypatch.setattr(
        f"{module_path}.time.time",
        lambda: now,
    )

    moved: list[str] = []
    monkeypatch.setattr(
        f"{module_path}.move_to_exception_folder",
        lambda path, **_kwargs: moved.append(path),
    )

    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    pending_old = watch_dir / "pending.rdf"
    pending_old.write_bytes(b"raw")
    pending_fresh = watch_dir / "fresh.rdf"
    pending_fresh.write_bytes(b"raw")

    export_old = watch_dir / "old.csv"
    export_old.write_text("kinexus", encoding="utf-8")
    native_old = watch_dir / "old_bucket.rdf"
    native_old.write_bytes(b"raw")

    sentinel_csv = watch_dir / "sentinel.csv"
    sentinel_csv.write_text("kinexus", encoding="utf-8")

    stage_dir = watch_dir / "Batch.__staged__1"
    stage_dir.mkdir()
    old_time = now - 10
    stage_dir.touch()
    os.utime(stage_dir, (old_time, old_time))

    state = _FolderState(
        pending_raw=deque(
            [
                _PendingRaw(path=pending_old, created=now - 10),
                _PendingRaw(path=pending_fresh, created=now - 1),
            ]
        ),
        bucket=[_Pair(export_path=export_old, raw_path=native_old, created=now - 10)],
        sentinel=_Sentinel(export_path=sentinel_csv, prefix="Batch", created=now - 10),
    )
    processor._state[str(watch_dir.resolve())] = state

    processor._purge_stale()

    expected = {
        str(pending_old),
        str(export_old),
        str(native_old),
        str(sentinel_csv),
        str(stage_dir),
    }
    assert expected.issubset(set(moved))
    assert state.pending_raw and state.pending_raw[0].path == pending_fresh


def test_reconstruct_batch_from_stage_raises_when_missing_files(tmp_path):
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    stage_dir = tmp_path / "Empty.__staged__1"
    stage_dir.mkdir()
    (stage_dir / "only.csv").write_text("kinexus", encoding="utf-8")

    with pytest.raises(RuntimeError):
        processor._reconstruct_batch_from_stage(stage_dir)
