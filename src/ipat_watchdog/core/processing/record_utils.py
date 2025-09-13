"""
Record and session helpers to keep the manager focused on orchestration.
"""
from __future__ import annotations

from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.session.session_manager import SessionManager


def get_or_create_record(records: RecordManager, record: LocalRecord | None, filename_prefix: str) -> LocalRecord:
    """Return existing record or create a new one for the given prefix."""
    return record if record else records.create_record(filename_prefix)


def apply_device_defaults(record: LocalRecord, device_settings: object) -> None:
    """Apply default description and tags from current device settings to the record."""
    if not device_settings:
        return
    if not record.default_description:
        record.default_description = getattr(device_settings, "DEFAULT_RECORD_DESCRIPTION", None)
    if not record.default_tags:
        record.default_tags = list(getattr(device_settings, "RECORD_TAGS", []))


def update_record(records: RecordManager, final_path: str, record: LocalRecord) -> None:
    """Update internal tracking that a file was added to a record."""
    records.add_item_to_record(final_path, record)


def manage_session(session_manager: SessionManager) -> None:
    """Start a new session or reset timer for the active session."""
    if not session_manager.session_active:
        session_manager.start_session()
    else:
        session_manager.reset_timer()
