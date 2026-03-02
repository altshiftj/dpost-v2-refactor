from __future__ import annotations

from collections import deque
import os

import pytest

from dpost.device_plugins.psa_horiba.file_processor import (
    FileProcessorPSAHoriba,
    _FolderState,
    _FlushBatch,
    _Pair,
    _PendingNGB,
    _Sentinel,
)
from dpost.device_plugins.psa_horiba.settings import build_config


def test_preprocessing_skips_finalizing_csv(tmp_path):
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    csv_path = watch_dir / "final.csv"
    csv_path.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")
    ngb_path = watch_dir / "final.ngb"
    ngb_path.write_bytes(b"ngb")

    stage_dir = watch_dir / "stage.__staged__1"
    stage_dir.mkdir()

    processor._finalizing[str(stage_dir)] = _FlushBatch(
        prefix="final",
        raw_probenname="final",
        pairs=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=0.0)],
    )

    assert processor.device_specific_preprocessing(str(csv_path)) is None


def test_preprocessing_skips_tracked_ngb(tmp_path, monkeypatch):
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    ngb_path = watch_dir / "pending.ngb"
    ngb_path.write_bytes(b"ngb")

    module_path = FileProcessorPSAHoriba.__module__
    monkeypatch.setattr(
        f"{module_path}.time.time",
        lambda: 0.0,
    )

    state = _FolderState(pending_ngb=deque([_PendingNGB(path=ngb_path, created=0.0)]))
    processor._state[str(watch_dir.resolve())] = state

    assert processor.device_specific_preprocessing(str(ngb_path)) is None
    assert len(state.pending_ngb) == 1


def test_purge_stale_moves_pending_bucket_sentinel_and_stage(tmp_path, monkeypatch):
    processor = FileProcessorPSAHoriba(
        build_config(),
        id_separator="-",
        exception_dir=str(tmp_path / "exceptions"),
    )
    processor.device_config.batch.ttl_seconds = 5

    now = 100.0
    module_path = FileProcessorPSAHoriba.__module__
    monkeypatch.setattr(
        f"{module_path}.time.time",
        lambda: now,
    )

    moved: list[str] = []
    monkeypatch.setattr(
        f"{module_path}.safe_move_to_exception",
        lambda path, **_kwargs: moved.append(path),
    )

    watch_dir = tmp_path / "incoming"
    watch_dir.mkdir()

    pending_old = watch_dir / "old.ngb"
    pending_old.write_bytes(b"ngb")
    pending_fresh = watch_dir / "fresh.ngb"
    pending_fresh.write_bytes(b"ngb")
    csv_old = watch_dir / "old.csv"
    csv_old.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")
    ngb_old = watch_dir / "old_pair.ngb"
    ngb_old.write_bytes(b"ngb")
    sentinel_csv = watch_dir / "sentinel.csv"
    sentinel_csv.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")

    stage_dir = watch_dir / "Sample.__staged__1"
    stage_dir.mkdir()
    old_time = now - 10
    stage_dir.touch()
    os.utime(stage_dir, (old_time, old_time))

    state = _FolderState(
        pending_ngb=deque(
            [
                _PendingNGB(path=pending_old, created=now - 10),
                _PendingNGB(path=pending_fresh, created=now - 1),
            ]
        ),
        bucket=[_Pair(csv_path=csv_old, ngb_path=ngb_old, created=now - 10)],
        sentinel=_Sentinel(
            csv_path=sentinel_csv,
            prefix="Sample",
            raw_probenname="Sample",
            created=now - 10,
        ),
    )
    processor._state[str(watch_dir.resolve())] = state

    processor._purge_stale()

    expected = {
        str(pending_old),
        str(csv_old),
        str(ngb_old),
        str(sentinel_csv),
        str(stage_dir),
    }
    assert expected.issubset(set(moved))
    assert state.pending_ngb and state.pending_ngb[0].path == pending_fresh


def test_reconstruct_batch_from_stage_pairs_by_stem(tmp_path):
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "Batch.__staged__1"
    stage_dir.mkdir()

    csv_a = stage_dir / "a.csv"
    csv_a.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")
    csv_b = stage_dir / "b.csv"
    csv_b.write_text("Probenname\tSample\nX(mm)\t1\n", encoding="utf-8")
    ngb_a = stage_dir / "a.ngb"
    ngb_a.write_bytes(b"ngb")
    ngb_c = stage_dir / "c.ngb"
    ngb_c.write_bytes(b"ngb")

    batch = processor._reconstruct_batch_from_stage(stage_dir)

    assert batch.prefix == "Batch"
    stems = {(pair.csv_path.stem, pair.ngb_path.stem) for pair in batch.pairs}
    assert ("a", "a") in stems
    assert len(batch.pairs) == 2


def test_reconstruct_batch_from_stage_raises_when_empty(tmp_path):
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "Empty.__staged__1"
    stage_dir.mkdir()

    with pytest.raises(RuntimeError):
        processor._reconstruct_batch_from_stage(stage_dir)
