"""
Routing utilities for deciding how to handle an item based on name validity
and the state of its corresponding record.
"""
from __future__ import annotations

from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.storage.filesystem_utils import (
    sanitize_and_validate,
    generate_record_id,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.records.record_manager import RecordManager

# Routing states
UNAPPENDABLE = "unappendable_record"  # File cannot be added to existing record
APPEND_SYNCED = "append_to_synced"    # File being added to already-synced record
VALID_NAME = "valid_name"             # File has valid naming convention
INVALID_NAME = "invalid_name"         # File naming doesn't meet requirements


def fetch_record_for_prefix(records: RecordManager, filename_prefix: str) -> tuple[str, bool, LocalRecord | None]:
    """
    Retrieve or validate record information for a filename prefix.

    Returns:
        tuple: (sanitized_prefix, is_valid_format, existing_record)
            - sanitized_prefix: Cleaned version of the filename prefix
            - is_valid_format: Whether the prefix follows naming conventions
            - existing_record: LocalRecord if one exists, None otherwise
    """
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
) -> str:
    """
    Determine how to route the file based on validation and record state.

    Logic:
    1. If record exists but file can't be appended -> UNAPPENDABLE
    2. If record exists and is fully synced -> APPEND_SYNCED (needs user confirmation)
    3. If record exists or name is valid -> VALID_NAME (standard processing)
    4. Otherwise -> INVALID_NAME (requires rename flow)
    """
    if record and not file_processor.is_appendable(record, filename_prefix, extension):
        return UNAPPENDABLE
    if record and record.is_in_db and record.all_files_uploaded():
        return APPEND_SYNCED
    if record or is_valid_format:
        return VALID_NAME
    return INVALID_NAME
