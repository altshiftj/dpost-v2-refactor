"""
record_persistence.py

This module manages the serialization and deserialization of LocalRecord objects 
to and from JSON files.
"""

import json
import os
from src.config.settings import DAILY_RECORDS_JSON
from src.records.local_record import LocalRecord
from src.app.logger import setup_logger

logger = setup_logger(__name__)

def load_persisted_records() -> dict[str, LocalRecord]:
    """
    Loads daily record data from a JSON file, converting each entry back into a LocalRecord.
    :return: A dictionary of short_id -> LocalRecord objects.
    """
    if not os.path.exists(DAILY_RECORDS_JSON):
        return {}
    try:
        with open(DAILY_RECORDS_JSON, 'r') as f:
            raw_data = json.load(f)
        logger.debug(f"JSON data loaded from '{DAILY_RECORDS_JSON}'.")
        return {id: LocalRecord.from_dict(record_data) for id, record_data in raw_data.items()}
    except Exception as e:
        logger.exception(f"Failed to read or convert JSON file '{DAILY_RECORDS_JSON}': {e}")
        return {}

def save_persisted_records(daily_records_dict: dict[str, LocalRecord]):
    """
    Saves the given dictionary of LocalRecord objects to the daily records JSON file.
    :param daily_records_dict: A dictionary mapping short_id -> LocalRecord objects.
    """
    try:
        with open(DAILY_RECORDS_JSON, 'w') as f:
            json.dump({key: record.to_dict() for key, record in daily_records_dict.items()}, f, indent=4)
        logger.debug(f"JSON data saved to '{DAILY_RECORDS_JSON}'.")
    except Exception as e:
        logger.exception(f"Failed to write JSON file '{DAILY_RECORDS_JSON}': {e}")
