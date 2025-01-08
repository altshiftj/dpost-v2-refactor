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

class RecordPersistence:
    """
    Responsible for loading and saving 'daily' records data (used during the current
    session or day) and appending records to an archive or historical log.
    """

    def __init__(self):
        """
        Initializes the RecordPersistence with default file paths for daily records 
        and archived records, as well as setting today's date for daily record tracking.
        """
        self.daily_records_path = DAILY_RECORDS_JSON
        self.records_db_path = ARCHIVED_FILES_JSON

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------
    def load_daily_records(self) -> dict:
        """
        Loads daily record data from a JSON file, converting each entry back into a LocalRecord.

        :return: A dictionary of short_id -> LocalRecord objects.
        """
        raw_data = self._read_json_file(self.daily_records_path)
        if raw_data is None:
            # If file doesn't exist or there's an error, return an empty dict
            return {}

        return self._convert_to_local_records(raw_data)

    def save_daily_records(self, daily_records_dict: dict[str, LocalRecord]):
        """
        Saves the given dictionary of LocalRecord objects to the daily records JSON file.

        :param daily_records_dict: A dictionary mapping short_id -> LocalRecord objects.
        """
        # Convert each LocalRecord object into a JSON-serializable dict
        daily_data = self._convert_local_records_to_dict(daily_records_dict)
        self._write_json_file(self.daily_records_path, daily_data)

    def append_to_records_db(self, record: LocalRecord):
        """
        Appends a single record entry to an NDJSON file as an ongoing log of all synced records.

        :param record: The LocalRecord that has been successfully synced.
        """
        record_entry = self._build_record_ndjson_entry(record)
        self._append_ndjson_entry(self.records_db_path, record_entry)
    # -------------------------------------------------------------------------


    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------
    def _read_json_file(self, path: str) -> dict | None:
        """
        Reads a JSON file and returns its contents as a dictionary. Logs exceptions if any.

        :param path: Path to the JSON file.
        :return: Dictionary with JSON contents, or None if reading fails or file doesn't exist.
        """
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Failed to read JSON file '{path}': {e}")
            return None

    def _write_json_file(self, path: str, data: dict):
        """
        Writes a dictionary to a JSON file, logging any exceptions that occur.

        :param path: Path to the JSON file.
        :param data: Dictionary to be written as JSON.
        """
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            logger.debug(f"JSON data saved to '{path}'.")
        except Exception as e:
            logger.exception(f"Failed to write JSON file '{path}': {e}")

    def _convert_to_local_records(self, raw_data: dict) -> dict[str, LocalRecord]:
        """
        Converts a raw dictionary of data into a dict of short_id -> LocalRecord objects.

        :param raw_data: Dictionary loaded from JSON.
        :return: A dict mapping short_id -> LocalRecord.
        """
        try:
            return {
                short_id: LocalRecord.from_dict(record_data)
                for short_id, record_data in raw_data.items()
            }
        except Exception as e:
            logger.exception(f"Failed to convert raw data to LocalRecords: {e}")
            return {}

    def _convert_local_records_to_dict(self, local_records: dict[str, LocalRecord]) -> dict:
        """
        Converts a dict of short_id -> LocalRecord into a dict suitable for JSON serialization.

        :param local_records: The dictionary of short_id -> LocalRecord objects.
        :return: A dictionary with JSON-serializable data.
        """
        return {
            key: record.to_dict()
            for key, record in local_records.items()
        }

    def _build_record_ndjson_entry(self, record: LocalRecord) -> dict:
        """
        Builds a single record entry (dict) for NDJSON logging.

        :param record: The LocalRecord to convert.
        :return: A dictionary suitable for writing as NDJSON.
        """
        record_id = record.long_id
        sync_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_name = record.short_id
        file_basenames = [os.path.basename(fp) for fp in record.files_uploaded.keys()]

        return {
            "record_id": record_id,
            "upsync_time": sync_time,
            "record_name": record_name,
            "files": file_basenames,
        }

    def _append_ndjson_entry(self, path: str, entry: dict):
        """
        Appends a dict as a JSON line to an NDJSON file.

        :param path: Path to the NDJSON file.
        :param entry: The dictionary to write as a JSON line.
        """
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(f"Appended record '{entry.get('record_id')}' to NDJSON at '{path}'.")
        except Exception as e:
            logger.exception(f"Failed to append to NDJSON file '{path}': {e}")
    # -------------------------------------------------------------------------
