"""Routing helper utilities."""
from __future__ import annotations

from typing import Optional

from ipat_watchdog.core.processing.models import RoutingDecision
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.storage.filesystem_utils import generate_record_id
from ipat_watchdog.core.storage.filesystem_utils import sanitize_and_validate
from ipat_watchdog.core.config import DeviceConfig


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


def determine_routing_state(
    record: Optional[LocalRecord],
    is_valid_format: bool,
    filename_prefix: str,
    extension: str,
    processor,
) -> RoutingDecision:
    """Determine routing decision based on record state and processor capabilities."""
    if record is None:
        return RoutingDecision.REQUIRE_RENAME if not is_valid_format else RoutingDecision.ACCEPT

    if not is_valid_format:
        return RoutingDecision.REQUIRE_RENAME

    if processor.is_appendable(record, filename_prefix, extension):
        # In 'it just works' mode we automatically append even if the record
        # has already been synced (no user prompt). Collapse APPEND_TO_SYNCED
        # into ACCEPT to unify downstream handling.
        return RoutingDecision.ACCEPT

    return RoutingDecision.UNAPPENDABLE

