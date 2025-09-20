"""
Record and session helpers to keep the manager focused on orchestration.
"""
from __future__ import annotations

from ipat_watchdog.core.config import DeviceConfig
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.session.session_manager import SessionManager


def get_or_create_record(records: RecordManager, record: LocalRecord | None, filename_prefix: str, device=None) -> LocalRecord:
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


def update_record(records: RecordManager, final_path: str, record: LocalRecord) -> None:
    """Update internal tracking that a file was added to a record."""
    records.add_item_to_record(final_path, record)


def manage_session(session_manager: SessionManager, record: LocalRecord) -> None:
    """Record activity to start or keep the current session alive."""
    session_manager.note_activity(record)
