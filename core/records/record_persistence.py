"""
record_persistence.py

This module manages the serialization and deserialization of LocalRecord objects
to and from JSON files.
"""

import json
from pathlib import Path
from core.config.constants import DAILY_RECORDS_JSON
from core.records.local_record import LocalRecord
from core.app.logger import setup_logger

logger = setup_logger(__name__)


def load_persisted_records() -> dict[str, LocalRecord]:
    """
    Loads daily record data from a JSON file, converting each entry back into a LocalRecord.
    :return: A dictionary of short_id -> LocalRecord objects.
    """
    json_path = Path(DAILY_RECORDS_JSON)
    if not json_path.exists():
        return {}
    try:
        raw_data = json_path.read_text(encoding="utf-8")
        records = json.loads(raw_data)
        logger.debug(f"JSON data loaded from '{json_path}'.")
        return {
            id: LocalRecord.from_dict(record_data)
            for id, record_data in records.items()
        }
    except Exception as e:
        logger.exception(f"Failed to read or convert JSON file '{json_path}': {e}")
        return {}


def save_persisted_records(daily_records_dict: dict[str, LocalRecord]):
    """
    Saves the given dictionary of LocalRecord objects to the daily records JSON file.
    :param daily_records_dict: A dictionary mapping short_id -> LocalRecord objects.
    """
    json_path = Path(DAILY_RECORDS_JSON)
    try:
        serialized = json.dumps(
            {key: record.to_dict() for key, record in daily_records_dict.items()},
            indent=4,
        )
        json_path.write_text(serialized, encoding="utf-8")
        logger.debug(f"JSON data saved to '{json_path}'.")
    except Exception as e:
        logger.exception(f"Failed to write JSON file '{json_path}': {e}")
