"""
record_persistence.py

This module manages the serialization and deserialization of LocalRecord objects 
to and from JSON files. It also provides a way to append records to a log of 
historical/archived record data in NDJSON (newline-delimited JSON) format.
"""

import json
import os
import datetime
from src.config.settings import DAILY_RECORDS_JSON, ARCHIVED_FILES_JSON
from src.records.local_record import LocalRecord
from src.app.logger import setup_logger

logger = setup_logger(__name__)

def load_daily_records() -> dict[str, LocalRecord]:
    """
    Loads daily record data from a JSON file, converting each entry back into a LocalRecord.
    :return: A dictionary of short_id -> LocalRecord objects.
    """
    if not os.path.exists(DAILY_RECORDS_JSON):
        return {}
    try:
        with open(DAILY_RECORDS_JSON, 'r') as f:
            raw_data = json.load(f)
        return {short_id: LocalRecord.from_dict(record_data) for short_id, record_data in raw_data.items()}
    except Exception as e:
        logger.exception(f"Failed to read or convert JSON file '{DAILY_RECORDS_JSON}': {e}")
        return {}

def save_daily_records(daily_records_dict: dict[str, LocalRecord]):
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

def append_to_records_db(record: LocalRecord):
    """
    Appends a single record entry to an NDJSON file as an ongoing log of all synced records.
    :param record: The LocalRecord that has been successfully synced.
    """
    entry = {
        "record_id": record.long_id,
        "upsync_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "record_name": record.record_name,
        "files": [os.path.basename(fp) for fp in record.files_uploaded.keys()],
    }
    try:
        with open(ARCHIVED_FILES_JSON, 'a') as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(f"Appended record '{entry.get('record_id')}' to NDJSON at '{ARCHIVED_FILES_JSON}'.")
    except Exception as e:
        logger.exception(f"Failed to append to NDJSON file '{ARCHIVED_FILES_JSON}': {e}")
