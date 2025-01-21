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

<<<<<<< HEAD
from src.records.local_record import LocalRecord, RecordInfo
from src.records.record_persistence import RecordPersistence
from src.records.id_generator import IdGenerator
from src.storage.path_manager import PathManager
from src.sync.sync_manager import ISyncManager
=======
from src.records.local_record import LocalRecord
from src.records import record_persistence

from src.sync.sync_manager import ISyncManager
from src.records.id_generator import IdGenerator #TODO: Phase out class for util method
>>>>>>> ref-sqlpersistence
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
<<<<<<< HEAD
        6. Reset daily records.
=======
>>>>>>> ref-sqlpersistence
    """

    def __init__(
        self,  
<<<<<<< HEAD
        paths_manager: PathManager, 
        record_persistence: RecordPersistence,
        id_generator: IdGenerator,
=======
>>>>>>> ref-sqlpersistence
        sync_manager: ISyncManager
    ):
        """
        Initializes the RecordManager with references to persistence, path, 
        ID generation, and synchronization utilities. Loads any previously 
<<<<<<< HEAD
        stored daily records from disk into memory.

        :param record_persistence: Manages saving/loading records to disk (daily/archived).
        :param paths_manager: Provides path construction/validation methods.
        :param id_generator: Helps generate unique record/file IDs based on naming conventions.
        :param sync_manager: Handles synchronization of records with a remote database/system.
        """
        self.paths = paths_manager
        self.persistence = record_persistence
        self.ids = id_generator
        self.sync = sync_manager

        # Dictionary of records for the current day,
        # keyed by their short_id (e.g., "ipat-jrf_Sample_A")
        self.daily_records_dict: Dict[str, LocalRecord] = self.persistence.load_daily_records()

    def create_record(self, record_info: RecordInfo) -> LocalRecord:
=======
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
>>>>>>> ref-sqlpersistence
        """
        Creates a new LocalRecord object based on the provided RecordInfo,
        assigning both a long_id and short_id to the record. Stores it
        in the daily records dictionary.

        :param record_info: A RecordInfo dataclass containing the record's basic metadata.
        :return: The newly created LocalRecord object.
        """
<<<<<<< HEAD
        daily_record_key = self.ids.construct_short_id(record_info)
        self.daily_records_dict[daily_record_key] = LocalRecord(
            long_id=self.ids.construct_long_id(record_info),
            short_id=daily_record_key,
            name=record_info.sample_id,
            date = record_info.date
        )
        
        logger.debug(f"Created new record with short_id '{daily_record_key}' and long_id '{self.daily_records_dict[daily_record_key].long_id}'.")
        return self.daily_records_dict[daily_record_key]
=======
        record_id = IdGenerator.generate_record_id(filename_prefix)
        sample_id = filename_prefix.split('-')[-1]
        self.persist_records_dict[record_id] = LocalRecord(
            identifier=record_id,
            name=sample_id,
            date = datetime.datetime.now().strftime('%Y%m%d')
        )
        
        logger.debug(f"Created new record with id '{filename_prefix}'.")
        return self.persist_records_dict[record_id]
>>>>>>> ref-sqlpersistence

    def add_item_to_record(self, path: str, record: LocalRecord):
        """
        Adds a file or directory path to an existing LocalRecord,
        then saves the updated records to disk.

        :param path: The file or directory path to associate with the record.
        :param record: The LocalRecord object to which the path will be added.
        """
<<<<<<< HEAD
        logger.debug(f"Adding item '{path}' to record '{record.short_id}'.")
=======
        logger.debug(f"Adding item '{path}' to record '{record.identifier}'.")
>>>>>>> ref-sqlpersistence
        record.add_item(path)
        self.save_records()

    def save_records(self):
        """
        Persists the current daily records dictionary to disk via the 
        RecordPersistence object.
        """
        logger.debug("Saving daily records to disk.")
<<<<<<< HEAD
        self.persistence.save_daily_records(self.daily_records_dict)
=======
        record_persistence.save_persisted_records(self.persist_records_dict)
>>>>>>> ref-sqlpersistence

    def get_all_records(self) -> dict:
        """
        Retrieves all LocalRecord objects in the daily records dictionary.

        :return: A dictionary mapping short_id -> LocalRecord.
        """
<<<<<<< HEAD
        return self.daily_records_dict
=======
        return self.persist_records_dict
>>>>>>> ref-sqlpersistence

    def get_num_records(self) -> int:
        """
        Counts the total number of daily records currently in memory.

        :return: An integer count of LocalRecord objects.
        """
<<<<<<< HEAD
        count = len(self.daily_records_dict.keys())
        logger.debug(f"Total number of records: {count}")
        return count

    def clear_all_records(self):
        """
        Removes all LocalRecord objects from the daily records dictionary
        and saves the empty dictionary to disk. This is typically done
        resetting the system for a new day.
        """
        logger.info("Clearing all daily records.")
        self.daily_records_dict.clear()
        self.save_records()

    def get_record_by_short_id(self, short_id: str) -> LocalRecord:
        """
        Looks up a LocalRecord by its short_id in the daily records dictionary.

        :param short_id: The short_id to look for (e.g., "ipat-mus_sample_a").
        :return: The LocalRecord if found, otherwise None.
        """
        short_id = short_id.lower()
        record = self.daily_records_dict.get(short_id)
        if record:
            logger.debug(f"Found record with short_id '{short_id}'.")
        else:
            logger.debug(f"No record found with short_id '{short_id}'.")
        return record
    
    def get_record_by_long_id(self, long_id: str) -> LocalRecord:
        """
        Iterates over all daily records to find one whose long_id matches.

        :param long_id: The record's long ID string to look for 
                        (e.g., "dev_01-20231010-rec_001-img-ipat-mus").
        :return: The matching LocalRecord if found, otherwise None.
        """
        long_id = long_id.lower()
        for record in self.daily_records_dict.values():
            if record.long_id == long_id:
                logger.debug(f"Found record with long_id '{long_id}'.")
                return record
        logger.debug(f"No record found with long_id '{long_id}'.")
        return None
    
=======
        count = len(self.persist_records_dict.keys())
        logger.debug(f"Total number of records: {count}")
        return count

    def get_record_by_id(self, id: str) -> LocalRecord:
        """
        Looks up a LocalRecord by its short_id in the daily records dictionary.

        :param short_id: The short_id to look for (e.g., "jfi-ipat-sample_a").
        :return: The LocalRecord if found, otherwise None.
        """
        id = id.lower()
        record = self.persist_records_dict.get(id)
        if record:
            logger.debug(f"Found record with short_id '{id}'.")
        else:
            logger.debug(f"No record found with short_id '{id}'.")
        return record
     
>>>>>>> ref-sqlpersistence
    def all_records_uploaded(self) -> bool:
        """
        Checks if all known records and their files have been uploaded to the database.

        :return: True if every file in every record is marked as uploaded, otherwise False.
        """
<<<<<<< HEAD
        all_uploaded = all(record.all_files_uploaded() for record in self.daily_records_dict.values())
        logger.debug(f"All records uploaded: {all_uploaded}")
        return all_uploaded
    
    def is_dict_up_to_date(self) -> bool:
        """
        Determines if the daily records date matches today's date. If it doesn't,
        the records dictionary is considered out of date.

        :return: True if the date matches today's date, False otherwise.
        """
        today_str = datetime.datetime.now().strftime('%Y%m%d')
        up_to_date = all(record.date == today_str for record in self.daily_records_dict.values())
        logger.debug(f"Is daily records dictionary up to date? {up_to_date}")
        return up_to_date

    def reset_dict(self):
        """
        Resets the daily records dictionary by syncing any pending records to the database,
        clearing all existing records, updating the date to today, and saving the empty
        records dictionary to disk. This is typically called when the system detects that
        the daily records dictionary is out of date.
        """
        logger.info("Resetting daily records dictionary and syncing to database.")
        self.sync_records_to_database()
        self.clear_all_records()
        logger.info("Daily records dictionary has been reset.")
    
=======
        all_uploaded = all(record.all_files_uploaded() for record in self.persist_records_dict.values())
        logger.debug(f"All records uploaded: {all_uploaded}")
        return all_uploaded

>>>>>>> ref-sqlpersistence
    def sync_records_to_database(self):
        """
        Iterates through all records in memory and attempts to sync any that are
        not fully uploaded to the remote database/system. After syncing, the records
        are saved to disk, and an entry is appended to the records database.
        """
        logger.info("Starting synchronization of records to the database.")
        for record in self.get_all_records().values():
            record: LocalRecord
            
            if not record.all_files_uploaded():
<<<<<<< HEAD
                logger.info(f"Syncing record '{record.long_id}' to the database.")
                self.sync.sync_record_to_database(record)
                self.save_records()
                self.persistence.append_to_records_db(record)
=======
                logger.info(f"Syncing record '{record.identifier}' to the database.")
                self.sync.sync_record_to_database(record)
                self.save_records()
>>>>>>> ref-sqlpersistence
        logger.info("Synchronization of records completed.")
