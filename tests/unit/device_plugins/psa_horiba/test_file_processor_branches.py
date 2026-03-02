"""Branch-focused tests for PSA Horiba processor helper and error paths."""

from __future__ import annotations

import time
import zipfile
from collections import deque
from pathlib import Path

import pytest

from dpost.device_plugins.psa_horiba.file_processor import (
    FileProcessorPSAHoriba,
    _FlushBatch,
    _FolderState,
    _Pair,
    _PendingNGB,
    _Sentinel,
)
from dpost.device_plugins.psa_horiba.settings import build_config
from dpost.domain.records.local_record import LocalRecord


def test_preprocessing_handles_missing_and_unsupported_files(tmp_path: Path) -> None:
    """Return deferred for missing items and ignore unknown extension files."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    missing_csv = tmp_path / "missing.csv"
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("note")

    assert processor.device_specific_preprocessing(str(missing_csv)) is None
    assert processor.device_specific_preprocessing(str(unsupported)) is None


def test_configure_runtime_context_sets_separator_only_when_missing() -> None:
    """Runtime context hook should populate missing naming/exception context only."""
    processor = FileProcessorPSAHoriba(build_config())
    processor.configure_runtime_context(
        id_separator="__",
        exception_dir="C:/exceptions",
    )
    assert processor._resolve_id_separator() == "__"  # noqa: SLF001
    assert processor._exception_dir == "C:/exceptions"  # noqa: SLF001

    explicit = FileProcessorPSAHoriba(
        build_config(),
        id_separator="-",
        exception_dir="C:/explicit",
    )
    explicit.configure_runtime_context(
        id_separator="__",
        exception_dir="C:/injected",
    )
    assert explicit._resolve_id_separator() == "-"  # noqa: SLF001
    assert explicit._exception_dir == "C:/explicit"  # noqa: SLF001


def test_handle_csv_skips_finalizing_and_tracked_entries(tmp_path: Path) -> None:
    """Skip CSV handling when item is finalizing already or tracked in state."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    csv_path = folder / "tracked.csv"
    csv_path.write_text("Probenname;Tracked\nX(mm);1\n", encoding="utf-8")
    ngb_path = folder / "tracked.ngb"
    ngb_path.write_bytes(b"ngb")

    processor._finalizing["batch"] = _FlushBatch(
        prefix="tracked",
        raw_probenname="tracked",
        pairs=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=1.0)],
    )
    assert processor._handle_csv(str(folder.resolve()), _FolderState(), csv_path) is None

    state = _FolderState(
        sentinel=_Sentinel(
            csv_path=csv_path,
            prefix="tracked",
            raw_probenname="tracked",
            created=1.0,
        )
    )
    assert processor._handle_csv(str(folder.resolve()), state, csv_path) is None


def test_handle_csv_parse_failure_and_pending_ngb_pairing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fallback to empty metadata and pair queued NGB when pending queue exists."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    csv_path = folder / "sample.csv"
    csv_path.write_text("bad", encoding="utf-8")
    ngb_path = folder / "sample.ngb"
    ngb_path.write_bytes(b"ngb")
    state = _FolderState(pending_ngb=deque([_PendingNGB(path=ngb_path, created=1.0)]))
    monkeypatch.setattr(
        processor,
        "_parse_csv_metadata",
        lambda _path: (_ for _ in ()).throw(RuntimeError("parse failed")),
    )

    result = processor._handle_csv(str(folder.resolve()), state, csv_path)

    assert result is None
    assert not state.pending_ngb
    assert len(state.bucket) == 1
    assert state.bucket[0].csv_path == csv_path
    assert state.bucket[0].ngb_path == ngb_path


def test_handle_csv_replaces_existing_sentinel(tmp_path: Path) -> None:
    """Replace stale sentinel when a new CSV sentinel arrives before NGB."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    old_csv = folder / "old.csv"
    old_csv.write_text("Probenname;Old\nX(mm);1\n", encoding="utf-8")
    new_csv = folder / "new.csv"
    new_csv.write_text("Probenname;New\nX(mm);1\n", encoding="utf-8")
    state = _FolderState(
        sentinel=_Sentinel(
            csv_path=old_csv,
            prefix="Old",
            raw_probenname="Old",
            created=1.0,
        )
    )

    processor._handle_csv(str(folder.resolve()), state, new_csv)

    assert state.sentinel is not None
    assert state.sentinel.csv_path == new_csv
    assert state.sentinel.prefix == "New"


def test_handle_csv_skips_already_bucketed_csv(tmp_path: Path) -> None:
    """Return early when CSV is already tracked inside the pending bucket."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    csv_path = folder / "bucket.csv"
    csv_path.write_text("Probenname;B\nX(mm);1\n", encoding="utf-8")
    ngb_path = folder / "bucket.ngb"
    ngb_path.write_bytes(b"ngb")
    state = _FolderState(
        bucket=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=1.0)]
    )

    assert processor._handle_csv(str(folder.resolve()), state, csv_path) is None


def test_handle_ngb_branches_for_staged_tracked_and_pending(tmp_path: Path) -> None:
    """Return staged path, skip tracked NGB, or queue NGB for later CSV."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    ngb_path = folder / "sample.ngb"
    ngb_path.write_bytes(b"ngb")

    staged_dir = tmp_path / "stage"
    staged_dir.mkdir()
    processor._ngb_to_stage[str(ngb_path)] = str(staged_dir)
    passthrough = processor._handle_ngb(str(folder.resolve()), _FolderState(), ngb_path)
    assert passthrough is not None
    assert passthrough.effective_path == str(staged_dir)

    processor._ngb_to_stage.clear()
    tracked_state = _FolderState(pending_ngb=deque([_PendingNGB(path=ngb_path, created=1.0)]))
    assert processor._handle_ngb(str(folder.resolve()), tracked_state, ngb_path) is None
    assert len(tracked_state.pending_ngb) == 1

    pending_state = _FolderState()
    assert processor._handle_ngb(str(folder.resolve()), pending_state, ngb_path) is None
    assert len(pending_state.pending_ngb) == 1


def test_handle_ngb_flush_survives_move_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continue staging bookkeeping even when move operations fail."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    csv_a = folder / "a.csv"
    csv_a.write_text("Probenname;A\nX(mm);1\n", encoding="utf-8")
    ngb_a = folder / "a.ngb"
    ngb_a.write_bytes(b"ngb")
    sentinel_csv = folder / "sentinel.csv"
    sentinel_csv.write_text("Probenname;S\nX(mm);1\n", encoding="utf-8")
    trigger_ngb = folder / "sentinel.ngb"
    trigger_ngb.write_bytes(b"ngb")
    state = _FolderState(
        bucket=[_Pair(csv_path=csv_a, ngb_path=ngb_a, created=time.time())],
        sentinel=_Sentinel(
            csv_path=sentinel_csv,
            prefix="S",
            raw_probenname="S",
            created=time.time(),
        ),
    )
    folder_key = str(folder.resolve())
    processor._state[folder_key] = state
    stage_dir = folder / "S.__staged__1"
    stage_dir.mkdir()
    monkeypatch.setattr(
        processor,
        "_create_unique_stage_dir",
        lambda _base_dir, _prefix: stage_dir,
    )
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.move_item",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("move failed")),
    )

    result = processor._handle_ngb(folder_key, state, trigger_ngb)

    assert result is not None
    assert result.effective_path == str(stage_dir)
    assert str(stage_dir) in processor._finalizing


def test_probe_file_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover mismatch, unknown, inconclusive, and match probe outcomes."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("x")
    mismatch = processor.probe_file(str(txt_path))
    assert mismatch.is_mismatch() is True

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("read failed")),
    )
    unknown = processor.probe_file(str(csv_path))
    assert unknown.is_match() is False
    assert unknown.is_mismatch() is False

    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: "dissolution cumulative release",
    )
    inconclusive = processor.probe_file(str(csv_path))
    assert inconclusive.is_match() is False
    assert inconclusive.is_mismatch() is False

    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: "HORIBA Partica LA-960 diameter",
    )
    matched = processor.probe_file(str(csv_path))
    assert matched.is_match() is True


def test_is_appendable_always_true() -> None:
    """Return appendable marker used by routing for PSA outputs."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    record = LocalRecord(identifier="dev-user-ipat-sample", id_separator="-")

    assert processor.is_appendable(record, "prefix", ".csv") is True


def test_processing_requires_pending_batch_for_file_source(tmp_path: Path) -> None:
    """Reject direct file finalization when no batch is pending."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    src = tmp_path / "direct.ngb"
    src.write_bytes(b"ngb")

    with pytest.raises(RuntimeError, match="No pending batch"):
        processor.device_specific_processing(
            str(src),
            str(tmp_path / "record"),
            "prefix",
            ".ngb",
        )


def test_processing_reconstructs_batch_when_stage_dir_not_cached(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconstruct staged batch when src dir exists but cache has been cleared."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    reconstructed = _FlushBatch(prefix="prefix", raw_probenname="prefix", pairs=[])
    monkeypatch.setattr(
        processor,
        "_reconstruct_batch_from_stage",
        lambda _stage: reconstructed,
    )

    output = processor.device_specific_processing(
        str(stage_dir),
        str(record_dir),
        "prefix",
        "",
    )

    assert Path(output.final_path) == record_dir


@pytest.mark.parametrize(
    ("missing_csv", "missing_ngb", "expected_message"),
    [
        (True, False, "Expected CSV missing"),
        (False, True, "Expected NGB missing"),
    ],
)
def test_processing_raises_when_staged_components_are_missing(
    tmp_path: Path,
    missing_csv: bool,
    missing_ngb: bool,
    expected_message: str,
) -> None:
    """Fail processing when staged CSV/NGB pair has disappeared."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    csv_path = stage_dir / "pair.csv"
    ngb_path = stage_dir / "pair.ngb"
    if not missing_csv:
        csv_path.write_text("Probenname;P\nX(mm);1\n", encoding="utf-8")
    if not missing_ngb:
        ngb_path.write_bytes(b"ngb")
    processor._finalizing[str(stage_dir)] = _FlushBatch(
        prefix="prefix",
        raw_probenname="prefix",
        pairs=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=time.time())],
    )

    with pytest.raises(RuntimeError, match=expected_message):
        processor.device_specific_processing(
            str(stage_dir),
            str(tmp_path / "record"),
            "override",
            "",
        )


def test_processing_cleanup_ignores_directory_and_map_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep successful output when cleanup hooks raise defensive exceptions."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    csv_path = stage_dir / "pair.csv"
    csv_path.write_text("Probenname;P\nX(mm);1\n", encoding="utf-8")
    ngb_path = stage_dir / "pair.ngb"
    ngb_path.write_bytes(b"ngb")
    record_dir = tmp_path / "record"

    class _FaultyPopDict(dict):
        def pop(self, key, default=None):  # type: ignore[override]
            raise RuntimeError("pop failed")

    processor._ngb_to_stage = _FaultyPopDict({str(ngb_path): str(stage_dir)})
    processor._finalizing[str(stage_dir)] = _FlushBatch(
        prefix="sentinel",
        raw_probenname="sentinel",
        pairs=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=time.time())],
    )
    monkeypatch.setattr(
        processor,
        "_next_sequence_basename",
        lambda _directory, _prefix: "override-01",
    )
    monkeypatch.setattr(
        Path,
        "iterdir",
        lambda _self: (_ for _ in ()).throw(OSError("iterdir failed")),
    )

    output = processor.device_specific_processing(
        str(stage_dir),
        str(record_dir),
        "override",
        "",
    )

    assert Path(output.final_path) == record_dir
    assert (record_dir / "override-01.csv").exists()
    assert (record_dir / "override-01.zip").exists()


def test_tracking_helpers_and_next_sequence_basename(
    tmp_path: Path,
) -> None:
    """Track CSV/NGB sentinels and compute next sequence from existing files."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    csv_path = folder / "tracked.csv"
    csv_path.write_text("Probenname;Tracked\nX(mm);1\n", encoding="utf-8")
    ngb_path = folder / "tracked.ngb"
    ngb_path.write_bytes(b"ngb")
    state = _FolderState(
        sentinel=_Sentinel(
            csv_path=csv_path,
            prefix="tracked",
            raw_probenname="tracked",
            created=1.0,
        ),
    )
    assert processor._csv_tracked(state, csv_path) is True
    assert processor._ngb_tracked(state, csv_path) is False

    processor._finalizing["active"] = _FlushBatch(
        prefix="tracked",
        raw_probenname="tracked",
        pairs=[_Pair(csv_path=csv_path, ngb_path=ngb_path, created=1.0)],
    )
    assert processor._is_csv_finalizing(csv_path) is True

    record_dir = tmp_path / "record"
    record_dir.mkdir()
    (record_dir / "prefix.csv").write_text("plain")
    (record_dir / "prefix-01.csv").write_text("1")
    (record_dir / "prefix-09.csv").write_text("9")
    (record_dir / "prefix-xx.csv").write_text("x")
    (record_dir / "other-99.csv").write_text("o")
    (record_dir / "nested").mkdir()

    assert processor._next_sequence_basename(record_dir, "prefix") == "prefix-10"


def test_resolve_id_separator_requires_explicit_runtime_context() -> None:
    """Reject separator resolution when processor has no explicit naming context."""
    processor = FileProcessorPSAHoriba(build_config())

    with pytest.raises(
        RuntimeError,
        match="id_separator runtime context is not configured",
    ):
        processor._resolve_id_separator()


def test_zip_ngb_keeps_zip_when_unlink_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create zip output even when source deletion raises."""
    src = tmp_path / "native.ngb"
    src.write_bytes(b"ngb")
    dest = tmp_path / "out.zip"
    monkeypatch.setattr(
        Path,
        "unlink",
        lambda _self, missing_ok=True: (_ for _ in ()).throw(OSError("unlink failed")),
    )

    FileProcessorPSAHoriba._zip_ngb(src, dest, arcname="native.ngb")

    with zipfile.ZipFile(dest) as zf:
        assert zf.namelist() == ["native.ngb"]


def test_parse_csv_metadata_handles_empty_lines_and_split_edge_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return empty metadata for empty text and tolerate empty split payloads."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: "",
    )
    assert processor._parse_csv_metadata(csv_path) == {}

    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: " \nline\n",
    )
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.re.split",
        lambda _pattern, _line: [],
    )
    assert processor._parse_csv_metadata(csv_path) == {}


def test_reconstruct_batch_from_stage_wraps_pairs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrap reconstructed staging pairs into PSA flush-batch dataclasses."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    csv_path = stage_dir / "pair.csv"
    ngb_path = stage_dir / "pair.ngb"
    csv_path.write_text("Probenname;P\nX(mm);1\n", encoding="utf-8")
    ngb_path.write_bytes(b"ngb")

    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.reconstruct_pairs_from_stage",
        lambda *_args, **_kwargs: ("prefix", [(csv_path, ngb_path)]),
    )
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.time.time",
        lambda: 123.0,
    )

    batch = processor._reconstruct_batch_from_stage(stage_dir)

    assert batch.prefix == "prefix"
    assert batch.raw_probenname == "prefix"
    assert len(batch.pairs) == 1
    assert batch.pairs[0].csv_path == csv_path
    assert batch.pairs[0].ngb_path == ngb_path
    assert batch.pairs[0].created == 123.0


def test_purge_stale_covers_exception_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Swallow stale-move and stage-scan failures while retaining fresh queue entries."""
    processor = FileProcessorPSAHoriba(
        build_config(),
        id_separator="-",
        exception_dir=str(tmp_path / "exceptions"),
    )
    processor.device_config.batch = type("BatchCfg", (), {"ttl_seconds": 5})()
    now = 100.0
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.time.time",
        lambda: now,
    )

    main_dir = (tmp_path / "incoming").resolve()
    main_dir.mkdir(parents=True)
    other_dir = (tmp_path / "other").resolve()
    other_dir.mkdir(parents=True)

    stale_pending = main_dir / "stale_pending.ngb"
    stale_pending.write_bytes(b"ngb")
    stale_csv = main_dir / "stale.csv"
    stale_csv.write_text("Probenname;S\nX(mm);1\n", encoding="utf-8")
    stale_ngb = main_dir / "stale_pair.ngb"
    stale_ngb.write_bytes(b"ngb")
    stale_sentinel = main_dir / "stale_sentinel.csv"
    stale_sentinel.write_text("Probenname;S\nX(mm);1\n", encoding="utf-8")
    fresh_pending = main_dir / "fresh.ngb"
    fresh_pending.write_bytes(b"ngb")

    processor._state[str(main_dir)] = _FolderState(
        pending_ngb=deque(
            [
                _PendingNGB(path=stale_pending, created=now - 10),
                _PendingNGB(path=fresh_pending, created=now - 1),
            ]
        ),
        bucket=[_Pair(csv_path=stale_csv, ngb_path=stale_ngb, created=now - 10)],
        sentinel=_Sentinel(
            csv_path=stale_sentinel,
            prefix="S",
            raw_probenname="S",
            created=now - 10,
        ),
    )
    processor._state[str(other_dir)] = _FolderState(
        pending_ngb=deque([_PendingNGB(path=fresh_pending, created=now - 1)])
    )

    stale_dir = main_dir / "S.__staged__1"
    stale_dir.mkdir()

    def fake_move(path: str, **_kwargs) -> None:
        if Path(path).name in {
            "stale_pending.ngb",
            "stale.csv",
            "stale_sentinel.csv",
            "S.__staged__1",
        }:
            raise RuntimeError("move failed")

    def fake_find_stale(parent: Path, **_kwargs):
        if parent.resolve() == main_dir:
            return [stale_dir]
        raise RuntimeError("scan failed")

    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.safe_move_to_exception",
        fake_move,
    )
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.find_stale_stage_dirs",
        fake_find_stale,
    )

    processor._purge_stale()

    main_state = processor._state[str(main_dir)]
    assert main_state.sentinel is None
    assert len(main_state.pending_ngb) == 1
    assert main_state.pending_ngb[0].path == fresh_pending


def test_purge_stale_requires_exception_dir_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip stale exception-move calls when exception-dir context is missing."""
    processor = FileProcessorPSAHoriba(build_config(), id_separator="-")
    processor.device_config.batch = type("BatchCfg", (), {"ttl_seconds": 5})()
    now = 100.0
    incoming = (tmp_path / "incoming").resolve()
    incoming.mkdir(parents=True)
    stale = incoming / "stale.ngb"
    stale.write_bytes(b"ngb")
    processor._state[str(incoming)] = _FolderState(
        pending_ngb=deque([_PendingNGB(path=stale, created=now - 10)])
    )
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.time.time",
        lambda: now,
    )
    move_calls: list[str] = []
    monkeypatch.setattr(
        "dpost.device_plugins.psa_horiba.file_processor.safe_move_to_exception",
        lambda path, **_kwargs: move_calls.append(path),
    )

    processor._purge_stale()

    assert move_calls == []
