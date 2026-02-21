"""Routing helper utilities."""

from __future__ import annotations

from typing import Optional

from dpost.application.config import DeviceConfig
from dpost.application.naming.policy import sanitize_and_validate
from dpost.application.records.record_manager import RecordManager
from dpost.domain.records.local_record import LocalRecord
from dpost.infrastructure.storage.filesystem_utils import (
    generate_record_id,
)


def fetch_record_for_prefix(
    records: RecordManager,
    filename_prefix: str,
    device: Optional[DeviceConfig],
) -> tuple[str, bool, LocalRecord | None]:
    """Return sanitized prefix, validity, and existing record if present."""
    sanitized_prefix, is_valid_format = sanitize_and_validate(filename_prefix)
    try:
        record_id = generate_record_id(
            sanitized_prefix,
            dev_kadi_record_id=device.metadata.record_kadi_id if device else None,
        )
    except ValueError:
        record_id = sanitized_prefix.lower()

    record = records.get_record_by_id(record_id)
    return sanitized_prefix, is_valid_format, record
