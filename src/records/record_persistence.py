import json
import os
import datetime
from src.config.settings import DAILY_RECORDS_JSON, ARCHIVED_FILES_JSON
from src.records.local_record import LocalRecord
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class RecordPersistence:
    def __init__(self):
        self.daily_records_path = DAILY_RECORDS_JSON
        self.records_db_path = ARCHIVED_FILES_JSON
        self.daily_records_date = datetime.datetime.now().strftime('%Y-%m-%d')

    def load_daily_records(self) -> dict:
        if os.path.exists(self.daily_records_path):
            try:
                with open(self.daily_records_path, 'r') as f:
                    daily_data = json.load(f)

                daily_records = {
                    base_name: LocalRecord.from_dict(record_data)
                    for base_name, record_data in daily_data.items()
                }
                return daily_records
            except Exception as e:
                logger.exception(f"Failed to load daily records: {e}")
        return {}

    def save_daily_records(self, daily_records_dict: dict):
        daily_data = {key: record.to_dict() for key, record in daily_records_dict.items()}

        try:
            with open(self.daily_records_path, 'w') as f:
                json.dump(daily_data, f, indent=4)
            logger.info("Daily records saved.")
        except Exception as e:
            logger.exception(f"Failed to save daily records: {e}")

    def append_to_records_db(self, record: LocalRecord):
        """Append a single record entry to the NDJSON records database."""
        record_id = record.long_id
        sync_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        record_name = record.short_id
        file_basenames = [os.path.basename(fp) for fp in record.file_uploaded.keys()]

        record_entry = {
            "record_id": record_id,
            "upsync_time": sync_time,
            "record_name": record_name,
            "files": file_basenames,
        }

        try:
            with open(self.records_db_path, 'a') as f:
                f.write(json.dumps(record_entry) + "\n")
            logger.info(f"Appended record '{record_id}' to records_db.ndjson.")
        except Exception as e:
            logger.exception(f"Failed to append to records_db: {e}")
