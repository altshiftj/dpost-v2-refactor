"""Migration tests for records/sync parity in dpost-owned processing paths."""

from __future__ import annotations

from pathlib import Path

from dpost.application.interactions import ErrorMessages
from dpost.application.processing.file_process_manager import FileProcessManager
from dpost.application.processing.file_processor_abstract import ProcessingOutput


class _InteractionProbe:
    """Capture user-facing error calls emitted by processing flows."""

    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))


class _RecordsProbe:
    """Track record-sync calls and optionally raise sync failures."""

    def __init__(
        self,
        *,
        all_uploaded: bool,
        sync_error: Exception | None = None,
    ) -> None:
        self._all_uploaded = all_uploaded
        self._sync_error = sync_error
        self.sync_calls = 0

    def all_records_uploaded(self) -> bool:
        return self._all_uploaded

    def sync_records_to_database(self) -> None:
        self.sync_calls += 1
        if self._sync_error is not None:
            raise self._sync_error


def _build_manager(
    *,
    records: _RecordsProbe,
    interactions: _InteractionProbe,
    immediate_sync: bool,
) -> FileProcessManager:
    manager = FileProcessManager.__new__(FileProcessManager)
    manager.records = records
    manager.interactions = interactions
    manager._immediate_sync = immediate_sync
    return manager


def test_immediate_sync_attempts_record_sync_when_pending(monkeypatch) -> None:
    """Require immediate-sync policy to trigger sync attempts for pending records."""
    records = _RecordsProbe(all_uploaded=False)
    interactions = _InteractionProbe()
    manager = _build_manager(
        records=records,
        interactions=interactions,
        immediate_sync=True,
    )
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.update_record",
        lambda _records, _path, _record: 1,
    )

    manager._post_persist_side_effects_stage(
        ProcessingOutput(final_path=str(Path("out.txt")), datatype="raw"),
        record=object(),
        record_path=str(Path(".")),
        src_path=str(Path("source.txt")),
    )

    assert records.sync_calls == 1


def test_immediate_sync_skips_when_records_are_already_uploaded(monkeypatch) -> None:
    """Require immediate-sync policy to skip sync when no pending uploads remain."""
    records = _RecordsProbe(all_uploaded=True)
    interactions = _InteractionProbe()
    manager = _build_manager(
        records=records,
        interactions=interactions,
        immediate_sync=True,
    )
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.update_record",
        lambda _records, _path, _record: 1,
    )

    manager._post_persist_side_effects_stage(
        ProcessingOutput(final_path=str(Path("out.txt")), datatype="raw"),
        record=object(),
        record_path=str(Path(".")),
        src_path=str(Path("source.txt")),
    )

    assert records.sync_calls == 0


def test_immediate_sync_failure_surfaces_user_error_message(monkeypatch) -> None:
    """Require sync failures to keep processing alive and surface actionable UI error."""
    records = _RecordsProbe(
        all_uploaded=False,
        sync_error=RuntimeError("credentials rejected"),
    )
    interactions = _InteractionProbe()
    manager = _build_manager(
        records=records,
        interactions=interactions,
        immediate_sync=True,
    )
    monkeypatch.setattr(
        "dpost.application.processing.file_process_manager.update_record",
        lambda _records, _path, _record: 1,
    )

    manager._post_persist_side_effects_stage(
        ProcessingOutput(final_path=str(Path("out.txt")), datatype="raw"),
        record=object(),
        record_path=str(Path(".")),
        src_path=str(Path("source.txt")),
    )

    assert records.sync_calls == 1
    assert interactions.errors
    title, details = interactions.errors[0]
    assert title == ErrorMessages.SYNC_ERROR
    assert "credentials rejected" in details
