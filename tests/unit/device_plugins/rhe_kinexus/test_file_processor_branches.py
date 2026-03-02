"""Branch-focused tests for Kinexus processor helper and error paths."""

from __future__ import annotations

import time
import zipfile
from collections import deque
from pathlib import Path

import pytest

from dpost.device_plugins.rhe_kinexus.file_processor import (
    FileProcessorRHEKinexus,
    _FlushBatch,
    _FolderState,
    _Pair,
    _PendingRaw,
    _Sentinel,
)
from dpost.device_plugins.rhe_kinexus.settings import build_config
from dpost.domain.records.local_record import LocalRecord


def test_preprocessing_handles_missing_and_unsupported_files(tmp_path: Path) -> None:
    """Return deferred for missing paths and ignore unsupported file extensions."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    missing_export = tmp_path / "missing.csv"
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("note")

    assert processor.device_specific_preprocessing(str(missing_export)) is None
    assert processor.device_specific_preprocessing(str(unsupported)) is None


def test_configure_runtime_context_sets_separator_only_when_missing() -> None:
    """Runtime context hook should populate missing naming/exception context only."""
    processor = FileProcessorRHEKinexus(build_config())
    processor.configure_runtime_context(
        id_separator="__",
        exception_dir="C:/exceptions",
    )
    assert processor._resolve_id_separator() == "__"  # noqa: SLF001
    assert processor._exception_dir == "C:/exceptions"  # noqa: SLF001

    explicit = FileProcessorRHEKinexus(
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


def test_handle_export_pairs_with_pending_native(tmp_path: Path) -> None:
    """Consume oldest pending native when a compatible export arrives."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    export_path = folder / "sample.csv"
    export_path.write_text("kinexus")
    raw_path = folder / "sample.rdf"
    raw_path.write_bytes(b"raw")
    state = _FolderState(pending_raw=deque([_PendingRaw(path=raw_path, created=1.0)]))

    result = processor._handle_export(str(folder.resolve()), state, export_path)

    assert result is None
    assert not state.pending_raw
    assert len(state.bucket) == 1
    assert state.bucket[0].export_path == export_path
    assert state.bucket[0].raw_path == raw_path


def test_handle_export_skips_finalizing_and_tracked_exports(tmp_path: Path) -> None:
    """Return early for exports already tracked by finalizing batches or state."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    export_path = folder / "tracked.csv"
    export_path.write_text("kinexus")

    processor._finalizing["batch"] = _FlushBatch(
        prefix="tracked",
        pairs=[
            _Pair(export_path=export_path, raw_path=folder / "raw.rdf", created=1.0)
        ],
    )
    state = _FolderState()
    assert processor._handle_export(str(folder.resolve()), state, export_path) is None

    state = _FolderState(
        sentinel=_Sentinel(export_path=export_path, prefix="tracked", created=1.0)
    )
    assert processor._handle_export(str(folder.resolve()), state, export_path) is None

    processor._finalizing.clear()
    state = _FolderState(
        bucket=[
            _Pair(export_path=export_path, raw_path=folder / "other.rdf", created=1.0)
        ]
    )
    assert processor._handle_export(str(folder.resolve()), state, export_path) is None


def test_handle_export_replaces_existing_sentinel_when_new_export_arrives(
    tmp_path: Path,
) -> None:
    """Replace older sentinel when a different export arrives before native flush."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    old_export = folder / "old.csv"
    old_export.write_text("kinexus")
    new_export = folder / "new.csv"
    new_export.write_text("kinexus")
    state = _FolderState(
        sentinel=_Sentinel(export_path=old_export, prefix="old", created=1.0)
    )

    processor._handle_export(str(folder.resolve()), state, new_export)

    assert state.sentinel is not None
    assert state.sentinel.export_path == new_export
    assert state.sentinel.prefix == "new"


def test_handle_native_branches_for_staged_tracked_and_pending(tmp_path: Path) -> None:
    """Return staged path, skip tracked native, or queue pending native by branch."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    native = folder / "sample.rdf"
    native.write_bytes(b"raw")

    staged_dir = tmp_path / "stage"
    staged_dir.mkdir()
    processor._raw_to_stage[str(native)] = str(staged_dir)
    passthrough = processor._handle_native(
        str(folder.resolve()), _FolderState(), native
    )
    assert passthrough is not None
    assert passthrough.effective_path == str(staged_dir)
    processor._raw_to_stage.clear()

    tracked_state = _FolderState(
        pending_raw=deque([_PendingRaw(path=native, created=1.0)])
    )
    assert (
        processor._handle_native(str(folder.resolve()), tracked_state, native) is None
    )
    assert len(tracked_state.pending_raw) == 1

    pending_state = _FolderState()
    processor._raw_to_stage.clear()
    assert (
        processor._handle_native(str(folder.resolve()), pending_state, native) is None
    )
    assert len(pending_state.pending_raw) == 1


def test_handle_native_flush_survives_move_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continue flush bookkeeping even when staging move operations fail."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    export_a = folder / "a.csv"
    export_a.write_text("kinexus")
    raw_a = folder / "a.rdf"
    raw_a.write_bytes(b"raw")
    sentinel_export = folder / "sentinel.csv"
    sentinel_export.write_text("kinexus")
    trigger_raw = folder / "sentinel.rdf"
    trigger_raw.write_bytes(b"raw")
    state = _FolderState(
        bucket=[_Pair(export_path=export_a, raw_path=raw_a, created=time.time())],
        sentinel=_Sentinel(
            export_path=sentinel_export,
            prefix="sentinel",
            created=time.time(),
        ),
    )
    folder_key = str(folder.resolve())
    processor._state[folder_key] = state
    stage_dir = folder / "sentinel.__staged__1"
    stage_dir.mkdir()

    monkeypatch.setattr(
        processor,
        "_create_unique_stage_dir",
        lambda _base_dir, _prefix: stage_dir,
    )
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.move_item",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("move failed")),
    )

    result = processor._handle_native(folder_key, state, trigger_raw)

    assert result is not None
    assert result.effective_path == str(stage_dir)
    assert str(stage_dir) in processor._finalizing


@pytest.mark.parametrize(
    ("filename", "snippet", "expected_match"),
    [
        ("sample.rdf", None, False),
        ("sample.txt", None, False),
        ("sample.csv", "dissolution profile; zWICK", False),
        ("sample.csv", "Kinexus viscosity g' response", True),
    ],
)
def test_probe_file_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    snippet: str | None,
    expected_match: bool,
) -> None:
    """Cover native/mismatch/inconclusive/match probe branches."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    target = tmp_path / filename
    target.write_text("content", encoding="utf-8")
    if filename.endswith(".csv") and snippet is not None:
        monkeypatch.setattr(
            "dpost.device_plugins.rhe_kinexus.file_processor.read_text_prefix",
            lambda *_args, **_kwargs: snippet,
        )

    result = processor.probe_file(str(target))

    assert result.is_match() is expected_match
    if filename.endswith(".txt"):
        assert result.is_mismatch() is True


def test_probe_file_returns_unknown_when_text_read_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return unknown probe decision when text prefix extraction fails."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    target = tmp_path / "sample.csv"
    target.write_text("content", encoding="utf-8")
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.read_text_prefix",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("decode fail")),
    )

    result = processor.probe_file(str(target))

    assert result.is_match() is False
    assert result.is_mismatch() is False
    assert result.reason == "decode fail"


def test_identity_helpers_are_stable() -> None:
    """Expose stable identity/appendability contracts used by routing policy."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    record = LocalRecord(identifier="dev-user-ipat-sample", id_separator="-")

    assert processor.is_appendable(record, "prefix", ".csv") is True
    assert processor.get_device_id() == "rhe_kinexus"


def test_constructor_accepts_explicit_id_separator_for_sequence_helper(
    tmp_path: Path,
) -> None:
    """Sequence helper should respect injected separator without ambient config lookup."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="__")
    record_dir = tmp_path / "record"
    record_dir.mkdir()
    (record_dir / "prefix__01.csv").write_text("1")
    (record_dir / "prefix__02.csv").write_text("2")

    assert processor._next_sequence_basename(record_dir, "prefix") == "prefix__03"


def test_resolve_id_separator_requires_explicit_runtime_context() -> None:
    """Reject separator resolution when processor has no explicit naming context."""
    processor = FileProcessorRHEKinexus(build_config())

    with pytest.raises(
        RuntimeError,
        match="id_separator runtime context is not configured",
    ):
        processor._resolve_id_separator()


def test_processing_requires_pending_batch_for_file_source(tmp_path: Path) -> None:
    """Reject direct file finalization when no matching staged batch exists."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    src = tmp_path / "direct.rdf"
    src.write_bytes(b"raw")
    record_dir = tmp_path / "record"

    with pytest.raises(RuntimeError, match="No pending batch"):
        processor.device_specific_processing(
            str(src), str(record_dir), "prefix", ".rdf"
        )


@pytest.mark.parametrize(
    ("missing_export", "missing_raw", "expected_message"),
    [
        (True, False, "Expected export missing"),
        (False, True, "Expected native missing"),
    ],
)
def test_processing_raises_when_staged_pair_components_are_missing(
    tmp_path: Path,
    missing_export: bool,
    missing_raw: bool,
    expected_message: str,
) -> None:
    """Fail finalization if staged pair components disappear before move/zip."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    export_path = stage_dir / "pair.csv"
    raw_path = stage_dir / "pair.rdf"
    if not missing_export:
        export_path.write_text("kinexus")
    if not missing_raw:
        raw_path.write_bytes(b"raw")
    processor._finalizing[str(stage_dir)] = _FlushBatch(
        prefix="prefix",
        pairs=[_Pair(export_path=export_path, raw_path=raw_path, created=time.time())],
    )

    with pytest.raises(RuntimeError, match=expected_message):
        processor.device_specific_processing(
            str(stage_dir),
            str(tmp_path / "record"),
            "prefix",
            "",
        )


def test_processing_directory_cleanup_ignores_rmdir_and_map_pop_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep processing success even if cleanup steps raise defensive exceptions."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    stage_dir = tmp_path / "batch.__staged__1"
    stage_dir.mkdir()
    export_path = stage_dir / "pair.csv"
    export_path.write_text("kinexus")
    raw_path = stage_dir / "pair.rdf"
    raw_path.write_bytes(b"raw")
    record_dir = tmp_path / "record"

    class _FaultyPopDict(dict):
        def pop(self, key, default=None):  # type: ignore[override]
            raise RuntimeError("pop failed")

    processor._raw_to_stage = _FaultyPopDict({str(raw_path): str(stage_dir)})
    processor._finalizing[str(stage_dir)] = _FlushBatch(
        prefix="prefix",
        pairs=[_Pair(export_path=export_path, raw_path=raw_path, created=time.time())],
    )
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.get_unique_filename",
        lambda _record_path, _base_prefix, _extension, **_kwargs: str(
            record_dir / "prefix-01.csv"
        ),
    )
    monkeypatch.setattr(
        Path,
        "rmdir",
        lambda _self: (_ for _ in ()).throw(OSError("rmdir failed")),
    )

    output = processor.device_specific_processing(
        str(stage_dir),
        str(record_dir),
        "prefix",
        "",
    )

    assert Path(output.final_path) == record_dir
    assert (record_dir / "prefix-01.csv").exists()
    assert (record_dir / "prefix-01.zip").exists()


def test_export_tracking_and_sequence_helpers(tmp_path: Path) -> None:
    """Track pending exports and compute next sequence from existing filenames."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    folder = tmp_path / "incoming"
    folder.mkdir()
    tracked_export = folder / "tracked.csv"
    tracked_export.write_text("kinexus")
    state = _FolderState(
        sentinel=_Sentinel(export_path=tracked_export, prefix="tracked", created=1.0)
    )
    assert processor._export_tracked(state, tracked_export) is True

    processor._finalizing["active"] = _FlushBatch(
        prefix="tracked",
        pairs=[
            _Pair(
                export_path=tracked_export,
                raw_path=folder / "tracked.rdf",
                created=1.0,
            )
        ],
    )
    assert processor._is_export_finalizing(tracked_export) is True

    record_dir = tmp_path / "record"
    record_dir.mkdir()
    (record_dir / "prefix.csv").write_text("plain")
    (record_dir / "prefix-01.csv").write_text("1")
    (record_dir / "prefix-09.csv").write_text("9")
    (record_dir / "prefix-xx.csv").write_text("x")
    (record_dir / "other-99.csv").write_text("o")
    (record_dir / "nested").mkdir()

    assert processor._next_sequence_basename(record_dir, "prefix") == "prefix-10"


def test_zip_raw_preserves_output_when_source_unlink_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create zip archive even when cleanup unlink of raw source raises."""
    src = tmp_path / "native.rdf"
    src.write_bytes(b"raw")
    dest = tmp_path / "out.zip"
    monkeypatch.setattr(
        Path,
        "unlink",
        lambda _self, missing_ok=True: (_ for _ in ()).throw(OSError("unlink failed")),
    )

    FileProcessorRHEKinexus._zip_raw(src, dest, arcname="native.rdf")

    with zipfile.ZipFile(dest) as zf:
        assert zf.namelist() == ["native.rdf"]


def test_purge_stale_covers_exception_and_cleanup_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tolerate stale-move and stale-scan failures while retaining fresh entries."""
    processor = FileProcessorRHEKinexus(
        build_config(),
        id_separator="-",
        exception_dir=str(tmp_path / "exceptions"),
    )
    processor.device_config.batch = type("BatchCfg", (), {"ttl_seconds": 5})()
    now = 100.0
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.time.time",
        lambda: now,
    )

    missing_key = str((tmp_path / "missing_state").resolve())
    watch_dir = (tmp_path / "incoming").resolve()
    watch_dir.mkdir(parents=True)

    pending_fail = watch_dir / "pending_fail.rdf"
    pending_fail.write_bytes(b"raw")
    bucket_export_fail = watch_dir / "bucket_export_fail.csv"
    bucket_export_fail.write_text("kinexus")
    bucket_raw = watch_dir / "bucket_raw.rdf"
    bucket_raw.write_bytes(b"raw")
    fresh_export = watch_dir / "fresh.csv"
    fresh_export.write_text("kinexus")
    fresh_raw = watch_dir / "fresh.rdf"
    fresh_raw.write_bytes(b"raw")
    sentinel_fail = watch_dir / "sentinel_fail.csv"
    sentinel_fail.write_text("kinexus")

    state = _FolderState(
        pending_raw=deque([_PendingRaw(path=pending_fail, created=now - 10)]),
        bucket=[
            _Pair(
                export_path=bucket_export_fail,
                raw_path=bucket_raw,
                created=now - 10,
            ),
            _Pair(export_path=fresh_export, raw_path=fresh_raw, created=now - 1),
        ],
        sentinel=_Sentinel(
            export_path=sentinel_fail,
            prefix="stale",
            created=now - 10,
        ),
    )
    processor._state = {missing_key: None, str(watch_dir): state}  # type: ignore[assignment]

    stale_dir_ok = watch_dir / "Batch.__staged__1"
    stale_dir_fail = watch_dir / "Batch.__staged__2"
    stale_dir_ok.mkdir()
    stale_dir_fail.mkdir()
    processor._raw_to_stage = {
        "raw-ok": str(stale_dir_ok),
        "raw-fail": str(stale_dir_fail),
    }
    moved: list[str] = []

    def fake_move(path: str, **_kwargs) -> None:
        name = Path(path).name
        if name in {"pending_fail.rdf", "bucket_export_fail.csv", "sentinel_fail.csv"}:
            raise RuntimeError("move failed")
        if name == "Batch.__staged__2":
            raise RuntimeError("stage move failed")
        moved.append(path)

    def fake_find_stale(parent: Path, **_kwargs):
        if parent.resolve() == watch_dir:
            return [stale_dir_ok, stale_dir_fail]
        raise RuntimeError("scan failed")

    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.move_to_exception_folder",
        fake_move,
    )
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.find_stale_stage_dirs",
        fake_find_stale,
    )

    processor._purge_stale()

    assert state.sentinel is None
    assert len(state.bucket) == 1
    assert state.bucket[0].export_path == fresh_export
    assert str(stale_dir_ok) in moved
    assert "raw-ok" not in processor._raw_to_stage


def test_purge_stale_requires_exception_dir_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip stale exception-move calls when exception-dir context is missing."""
    processor = FileProcessorRHEKinexus(build_config(), id_separator="-")
    processor.device_config.batch = type("BatchCfg", (), {"ttl_seconds": 5})()
    now = 100.0
    watch_dir = (tmp_path / "incoming").resolve()
    watch_dir.mkdir(parents=True)
    stale = watch_dir / "stale.rdf"
    stale.write_bytes(b"raw")
    processor._state[str(watch_dir)] = _FolderState(
        pending_raw=deque([_PendingRaw(path=stale, created=now - 10)])
    )
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.time.time",
        lambda: now,
    )
    move_calls: list[str] = []
    monkeypatch.setattr(
        "dpost.device_plugins.rhe_kinexus.file_processor.move_to_exception_folder",
        lambda path, **_kwargs: move_calls.append(path),
    )

    processor._purge_stale()

    assert move_calls == []
