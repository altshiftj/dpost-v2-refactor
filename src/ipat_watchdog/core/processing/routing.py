"""Routing utilities for processing decisions."""
from __future__ import annotations

from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.processing.models import RoutingDecision
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.storage.filesystem_utils import (
    generate_record_id,
    sanitize_and_validate,
)

# Backward compatible string aliases --------------------------------------------------
UNAPPENDABLE = RoutingDecision.UNAPPENDABLE.value
APPEND_SYNCED = RoutingDecision.APPEND_TO_SYNCED.value
VALID_NAME = RoutingDecision.ACCEPT.value
INVALID_NAME = RoutingDecision.REQUIRE_RENAME.value


def fetch_record_for_prefix(records: RecordManager, filename_prefix: str) -> tuple[str, bool, LocalRecord | None]:
    """Return sanitized prefix, validity flag, and existing record (if any)."""
    sanitized_prefix, is_valid_format = sanitize_and_validate(filename_prefix)
    record_id = generate_record_id(sanitized_prefix)
    record = records.get_record_by_id(record_id)
    return sanitized_prefix, is_valid_format, record


def determine_routing_state(
    record: LocalRecord | None,
    is_valid_format: bool,
    filename_prefix: str,
    extension: str,
    file_processor: FileProcessorABS,
) -> RoutingDecision:
    """Compute the routing decision for the incoming artefact."""
    if record and not file_processor.is_appendable(record, filename_prefix, extension):
        return RoutingDecision.UNAPPENDABLE
    if record and record.is_in_db and record.all_files_uploaded():
        return RoutingDecision.APPEND_TO_SYNCED
    if record or is_valid_format:
        return RoutingDecision.ACCEPT
    return RoutingDecision.REQUIRE_RENAME
