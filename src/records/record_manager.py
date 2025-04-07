import datetime
from typing import Dict, Optional

from src.records.local_record import LocalRecord
from src.records import record_persistence
from src.sync.sync_abstract import ISyncManager
from src.records.id_generator import IdGenerator
from src.app.logger import setup_logger

logger = setup_logger(__name__)


class RecordManager:
    """
    Handles LocalRecord creation, storage, syncing, and persistence.
    """

    def __init__(self, sync_manager: ISyncManager):
        self.sync = sync_manager
        self._persist_records_dict: Optional[Dict[str, LocalRecord]] = None

    @property
    def persist_records_dict(self) -> Dict[str, LocalRecord]:
        """
        Lazily loads persisted records from disk the first time accessed.
        """
        if self._persist_records_dict is None:
            logger.debug("Lazy loading persisted records from disk...")
            self._persist_records_dict = record_persistence.load_persisted_records()
        return self._persist_records_dict

    def reload_records(self):
        """
        Forces a reload of the persisted records from disk.
        """
        logger.info("Reloading persisted records from disk...")
        self._persist_records_dict = record_persistence.load_persisted_records()

    def create_record(self, filename_prefix: str) -> LocalRecord:
        """
        Creates and stores a new LocalRecord using the filename prefix.
        """
        record_id = IdGenerator.generate_record_id(filename_prefix)
        record = LocalRecord(
            identifier=record_id,
            date=datetime.datetime.now().strftime('%Y%m%d')
        )
        self._store_record(record)
        logger.debug(f"Created new record with id '{record_id}'.")
        return record

    def add_item_to_record(self, path: str, record: LocalRecord):
        """
        Adds a path to a record, then persists the update.
        """
        logger.debug(f"Adding item '{path}' to record '{record.identifier}'.")
        record.add_item(path)
        self.save_records()

    def save_records(self):
        """
        Persists all records to disk.
        """
        logger.debug(f"Saving {len(self.persist_records_dict)} records to disk.")
        record_persistence.save_persisted_records(self.persist_records_dict)

    def get_all_records(self) -> Dict[str, LocalRecord]:
        return self.persist_records_dict

    def get_num_records(self) -> int:
        count = len(self.persist_records_dict)
        logger.debug(f"Total number of records: {count}")
        return count

    def get_record_by_id(self, record_id: str) -> Optional[LocalRecord]:
        record_id = record_id.lower()
        record = self.persist_records_dict.get(record_id)
        if record:
            logger.debug(f"Found record with identifier '{record_id}'.")
        else:
            logger.debug(f"No record found with identifier '{record_id}'.")
        return record

    def all_records_uploaded(self) -> bool:
        all_uploaded = all(record.all_files_uploaded() for record in self.persist_records_dict.values())
        logger.debug(f"All records uploaded: {all_uploaded}")
        return all_uploaded

    def sync_records_to_database(self):
        logger.info("Starting synchronization of records to the database.")
        synced_count = 0

        for record in self.persist_records_dict.values():
            if record.institute != 'ipat':
                logger.info(f"Record '{record.identifier}' is not applicable for syncing.")
            elif record.all_files_uploaded():
                logger.info(f"Record '{record.identifier}' is already fully uploaded.")
            else:
                logger.info(f"Syncing record '{record.identifier}' to the database.")
                self._sync_record(record)
                synced_count += 1

        logger.info(f"Synchronization of records completed. Synced: {synced_count}")

    def sync_logs_to_database(self):
        logger.info("Starting synchronization of logs to the database.")
        self.sync.sync_logs_to_database()
        logger.info("Synchronization of logs completed.")

    # --------------------------
    # Internal Helper Methods
    # --------------------------

    def _store_record(self, record: LocalRecord):
        self.persist_records_dict[record.identifier] = record

    def _sync_record(self, record: LocalRecord):
        self.sync.sync_record_to_database(record)
        self.save_records()
