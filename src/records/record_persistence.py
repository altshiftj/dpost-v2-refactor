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

    Usage Examples:
      1. Load all daily records from disk.
      2. Save updated daily records when new files are added.
      3. Append a record to the historical 'records_db.ndjson' when it is synced.
    """

    def __init__(self):
        """
        Initializes the RecordPersistence with default file paths for daily records 
        and archived records, as well as setting today's date for daily record tracking.
        """
        self.daily_records_path = DAILY_RECORDS_JSON
        self.records_db_path = ARCHIVED_FILES_JSON
        # The date associated with the current daily records
        self.daily_records_date = datetime.datetime.now().strftime('%Y-%m-%d')

    def load_daily_records(self) -> dict:
        """
        Loads daily record data from a JSON file. This file is expected to contain
        a mapping from short_id strings to corresponding record data.

        :return: A dictionary of short_id -> LocalRecord objects.
        """
        if os.path.exists(self.daily_records_path):
            try:
                with open(self.daily_records_path, 'r') as f:
                    daily_data = json.load(f)

                # Convert each JSON entry back into a LocalRecord
                daily_records = {
                    base_name: LocalRecord.from_dict(record_data)
                    for base_name, record_data in daily_data.items()
                }
                return daily_records
            except Exception as e:
                logger.exception(f"Failed to load daily records: {e}")
        return {}

    def save_daily_records(self, daily_records_dict: dict [str, LocalRecord]):
        """
        Saves the given dictionary of LocalRecord objects to the daily records JSON file.

        :param daily_records_dict: A dictionary mapping short_id -> LocalRecord objects.
        """
        # Convert each LocalRecord object into a JSON-serializable dict
        daily_data = {key: record.to_dict() for key, record in daily_records_dict.items()}

        try:
            with open(self.daily_records_path, 'w') as f:
                json.dump(daily_data, f, indent=4)
            logger.info("Daily records saved.")
        except Exception as e:
            logger.exception(f"Failed to save daily records: {e}")

    def append_to_records_db(self, record: LocalRecord):
        """
        Appends a single record entry to an NDJSON (newline-delimited JSON) file.
        This file serves as an ongoing log or 'archive' of all synced records.

        :param record: The LocalRecord that has been successfully synced.
        """
        record_id = record.long_id
        sync_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_name = record.short_id
        # Gather the basenames of the record's files for storage
        file_basenames = [os.path.basename(fp) for fp in record.file_uploaded.keys()]

        # Prepare a record entry suitable for NDJSON
        record_entry = {
            "record_id": record_id,
            "upsync_time": sync_time,
            "record_name": record_name,
            "files": file_basenames,
        }

        try:
            # Open the archive file in append mode and write one JSON object per line
            with open(self.records_db_path, 'a') as f:
                f.write(json.dumps(record_entry) + "\n")
            logger.info(f"Appended record '{record_id}' to records_db.ndjson.")
        except Exception as e:
            logger.exception(f"Failed to append to records_db: {e}")
