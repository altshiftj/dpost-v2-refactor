"""Record and session helpers to keep the manager focused on orchestration."""

from __future__ import annotations

from dpost.application.config import DeviceConfig
from dpost.application.records.record_manager import RecordManager
from dpost.application.session import SessionManager
from dpost.domain.records.local_record import LocalRecord


def get_or_create_record(
    records: RecordManager,
    record: LocalRecord | None,
    filename_prefix: str,
    device=None,
) -> LocalRecord:
    """Return existing record or create a new one for the given prefix."""
    return record if record else records.create_record(filename_prefix, device)


def apply_device_defaults(record: LocalRecord, device: DeviceConfig | None) -> None:
    """Apply default description and tags from current device configuration to the record."""
    if device is None:
        return
    metadata = device.metadata
    if not record.default_description:
        record.default_description = metadata.default_record_description
    if not record.default_tags:
        record.default_tags = list(metadata.record_tags)


def update_record(records: RecordManager, final_path: str, record: LocalRecord) -> int:
    """Update tracking for a processed file and return the new count."""
    return records.add_item_to_record(final_path, record)


def manage_session(session_manager: SessionManager, record: LocalRecord) -> None:
    """No-op session management.

    Previously this recorded activity (session_manager.note_activity(record)) to
    drive interactive session prompts and timeout handling. In the current
    'it just works' paradigm we disable session side-effects while keeping the
    call sites intact for easy reversion.
    """
    return
