"""
record_manager.py

Manages LocalRecord objects in memory, linking them to files/folders on disk,
and facilitating creation, lookup, and clearing of records. This class also
coordinates daily record resets and persists record data through a
RecordPersistence object. Additionally, it handles synchronization of records
to a remote database using a SyncManager.
"""

import datetime
from typing import Dict

from src.records.local_record import LocalRecord
from src.records import record_persistence

from src.sync.sync_manager import ISyncManager
from src.records.id_generator import IdGenerator
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class RecordManager:
    """
    The RecordManager class handles CRUD-like operations on LocalRecord objects
    (i.e., create, read, update, delete/clear) and maintains these records
    in a dictionary keyed by their 'short_id'. It also provides methods to
    persist and restore record data via a RecordPersistence object, and 
    synchronizes records with a remote database through a SyncManager.

    Typical usage:
        1. Load or create records in memory.
        2. Add file paths to existing records.
        3. Syncing records to a remote database.
    """

    def __init__(
        self,  
        sync_manager: ISyncManager
    ):
        """
        Initializes the RecordManager with references to persistence, path, 
        ID generation, and synchronization utilities. Loads any previously 
        stored records from disk into memory.

        :param record_persistence: Manages saving/loading records to disk.
        :param paths_manager: Provides path construction/validation methods.
        :param sync_manager: Handles synchronization of records with a remote database/system.
        """
        self.sync = sync_manager

        # Dictionary of records processed for this device
        # keyed by their id (e.g., "jfi-ipat-Sample_A")
        self.persist_records_dict: Dict[str, LocalRecord] = record_persistence.load_persisted_records()

    def create_record(self, filename_prefix: str) -> LocalRecord:
        """
        Creates a new LocalRecord object based on the given filename_prefix. Stores it
        in the record_persistance dictionary.

        :param filename_prefix: The extensionless filename used to generate the record ID.
        :return: The newly created LocalRecord object.
        """
        record_id = IdGenerator.generate_record_id(filename_prefix)

        sample_id = filename_prefix.split('-')[-1]
        self.persist_records_dict[record_id] = LocalRecord(
            identifier=record_id,
            name=sample_id,
            date = datetime.datetime.now().strftime('%Y%m%d')
        )
        
        logger.debug(f"Created new record with id '{filename_prefix}'.")
        return self.persist_records_dict[record_id]

    def add_item_to_record(self, path: str, record: LocalRecord):
        """
        Adds a file or directory path to an existing LocalRecord,
        then saves the updated records to disk.

        :param path: The file or directory path to associate with the record.
        :param record: The LocalRecord object to which the path will be added.
        """
        logger.debug(f"Adding item '{path}' to record '{record.identifier}'.")
        record.add_item(path)
        self.save_records()

    def save_records(self):
        """
        Persists the current daily records dictionary to disk via the 
        RecordPersistence object.
        """
        logger.debug("Saving daily records to disk.")
        record_persistence.save_persisted_records(self.persist_records_dict)

    def get_all_records(self) -> dict:
        """
        Retrieves all LocalRecord objects in the daily records dictionary.

        :return: A dictionary mapping short_id -> LocalRecord.
        """
        return self.persist_records_dict

    def get_num_records(self) -> int:
        """
        Counts the total number of daily records currently in memory.

        :return: An integer count of LocalRecord objects.
        """
        count = len(self.persist_records_dict.keys())
        logger.debug(f"Total number of records: {count}")
        return count

    def get_record_by_id(self, id: str) -> LocalRecord:
        """
        Looks up a LocalRecord by its identifier in the daily records dictionary.

        :param identifier: The identifier to look for (e.g., "jfi-ipat-sample_a").
        :return: The LocalRecord if found, otherwise None.
        """
        id = id.lower()
        record = self.persist_records_dict.get(id)
        if record:
            logger.debug(f"Found record with identifier '{id}'.")
        else:
            logger.debug(f"No record found with identifier '{id}'.")
        return record
     
    def all_records_uploaded(self) -> bool:
        """
        Checks if all known records and their files have been uploaded to the database.

        :return: True if every file in every record is marked as uploaded, otherwise False.
        """
        all_uploaded = all(record.all_files_uploaded() for record in self.persist_records_dict.values())
        logger.debug(f"All records uploaded: {all_uploaded}")
        return all_uploaded

    def sync_records_to_database(self):
        """
        Iterates through all records in memory and attempts to sync any that are
        not fully uploaded to the remote database/system. After syncing, the records
        are saved to disk, and an entry is appended to the records database.
        """
        logger.info("Starting synchronization of records to the database.")
        for record in self.get_all_records().values():
            record: LocalRecord
            # if the institute in the record identifier is ipat, then sync the record
            institute = record.identifier.split('-')[2]
            
            if institute == 'ipat' and not record.all_files_uploaded():
                logger.info(f"Syncing record '{record.identifier}' to the database.")
                self.sync.sync_record_to_database(record)
                self.save_records()
            elif institute != 'ipat':
                logger.info(f"Record '{record.identifier}' is not applicable for syncing.")
            else:
                logger.info(f"Record '{record.identifier}' is already fully uploaded.")
                
        logger.info("Synchronization of records completed.")

    def sync_logs_to_database(self):
        """
        Syncs the log file to the database.
        """
        logger.info("Starting synchronization of logs to the database.")
        self.sync.sync_logs_to_database()
        logger.info("Synchronization of logs completed.")
