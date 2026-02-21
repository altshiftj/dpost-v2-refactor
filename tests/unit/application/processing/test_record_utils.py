"""Unit coverage for processing record/session helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

from dpost.application.processing.record_utils import (
    apply_device_defaults,
    get_or_create_record,
    manage_session,
    update_record,
)
from dpost.domain.records.local_record import LocalRecord


@dataclass(frozen=True)
class _MetadataStub:
    """Minimal device metadata payload used in record helper tests."""

    default_record_description: str
    record_tags: tuple[str, ...]


@dataclass(frozen=True)
class _DeviceStub:
    """Minimal device wrapper exposing metadata field."""

    metadata: _MetadataStub


def test_get_or_create_record_returns_existing_record_without_creation() -> None:
    """Return existing record directly and avoid creating a new one."""
    records = Mock()
    existing = LocalRecord(identifier="dev-usr-ins-sample")

    resolved = get_or_create_record(records, existing, "prefix", device=object())

    assert resolved is existing
    records.create_record.assert_not_called()


def test_get_or_create_record_creates_new_record_when_missing() -> None:
    """Create a record through record manager when no existing record is passed."""
    records = Mock()
    created = LocalRecord(identifier="dev-usr-ins-sample")
    records.create_record.return_value = created

    resolved = get_or_create_record(records, None, "prefix", device="device-x")

    assert resolved is created
    records.create_record.assert_called_once_with("prefix", "device-x")


def test_apply_device_defaults_noops_when_device_is_none() -> None:
    """Leave record defaults unchanged when no active device is provided."""
    record = LocalRecord(identifier="dev-usr-ins-sample")
    record.default_description = "keep"
    record.default_tags = ["keep-tag"]

    apply_device_defaults(record, None)

    assert record.default_description == "keep"
    assert record.default_tags == ["keep-tag"]


def test_apply_device_defaults_sets_description_and_tags_when_missing() -> None:
    """Populate missing defaults from active device metadata."""
    record = LocalRecord(identifier="dev-usr-ins-sample")
    device = _DeviceStub(
        metadata=_MetadataStub(
            default_record_description="Device default description",
            record_tags=("tag-a", "tag-b"),
        )
    )

    apply_device_defaults(record, device)

    assert record.default_description == "Device default description"
    assert record.default_tags == ["tag-a", "tag-b"]


def test_update_record_delegates_to_record_manager() -> None:
    """Forward processed path tracking to record manager and return new count."""
    records = Mock()
    records.add_item_to_record.return_value = 3
    record = LocalRecord(identifier="dev-usr-ins-sample")

    total = update_record(records, "C:/records/file.csv", record)

    assert total == 3
    records.add_item_to_record.assert_called_once_with("C:/records/file.csv", record)


def test_manage_session_is_explicit_noop() -> None:
    """Perform no session side effects to preserve current no-op semantics."""
    session = Mock()
    record = LocalRecord(identifier="dev-usr-ins-sample")

    result = manage_session(session, record)

    assert result is None
    session.note_activity.assert_not_called()
