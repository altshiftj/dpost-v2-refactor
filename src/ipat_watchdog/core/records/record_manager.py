"""Manages LocalRecord lifecycle, persistence, and sync orchestration."""

import datetime
from typing import Dict, Optional

from ipat_watchdog.metrics import FILES_PROCESSED_BY_RECORD
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import (
    load_persisted_records,
    save_persisted_records,
    generate_record_id,
)
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class RecordManager:
    """
    Central manager for LocalRecord lifecycle and database synchronization.
    
    Responsibilities:
    - Create and store LocalRecord instances for processed files
    - Maintain persistent storage of records on disk
    - Coordinate database synchronization through sync manager
    - Track file processing metrics and record states
    
    The RecordManager acts as the bridge between file processing and database
    storage, ensuring records are properly persisted and synchronized.
    """

    def __init__(self, sync_manager: ISyncManager):
        """
        Initialize RecordManager with synchronization capabilities.
        
        Args:
            sync_manager: Interface for syncing records to external database
        """
        self.sync = sync_manager
        # Lazy-loaded dictionary of all persisted records
        self._persist_records_dict: Optional[Dict[str, LocalRecord]] = None

    @property
    def persist_records_dict(self) -> Dict[str, LocalRecord]:
        """
        Lazily loads persisted records from disk the first time accessed.
        
        This lazy loading pattern improves startup performance by only reading
        records when actually needed. Subsequent accesses use the cached version.
        
        Returns:
            Dict mapping record IDs to LocalRecord instances
        """
        if self._persist_records_dict is None:
            logger.debug("Lazy loading persisted records from disk...")
            self._persist_records_dict = load_persisted_records()
        return self._persist_records_dict

    def reload_records(self):
        """
        Forces a reload of the persisted records from disk.
        
        Used when external changes to record storage are detected
        or when manual refresh is needed.
        """
        logger.info("Reloading persisted records from disk...")
        self._persist_records_dict = load_persisted_records()

    def create_record(self, filename_prefix: str, device=None) -> LocalRecord:
        """
        Creates and stores a new LocalRecord using the filename prefix.

        Extracts sample name from prefix and generates unique record ID.
        The new record is immediately stored and persisted.

        Args:
            filename_prefix: Standardized filename prefix (e.g., 'usr-ipat-sample123')
            device: Optional device configuration providing record identity information

        Returns:
            LocalRecord: Newly created record instance
        """
        # Generate unique identifier and extract sample name
        record_id = generate_record_id(
            filename_prefix,
            dev_kadi_record_id=(device.metadata.record_kadi_id if device else None),
        )
        sample_name = filename_prefix.split('-')[-1]  # Extract last part as sample name

        # Create new record with current date
        record = LocalRecord(
            identifier=record_id,
            sample_name=sample_name,
            date=datetime.datetime.now().strftime('%Y%m%d'),
        )

        # Store and persist the new record
        self._store_record(record)
        logger.debug(f"Created new record with id '{record_id}'.")
        return record
    def add_item_to_record(self, path: str, record: LocalRecord):
        """
        Adds a file path to a record and updates metrics and persistence.
        
        This is called when a file is successfully processed and needs to be
        tracked as part of a record. Updates Prometheus metrics and saves state.
        
        Args:
            path: File path that was processed
            record: LocalRecord to add the file to
        """
        logger.debug(f"Adding item '{path}' to record '{record.identifier}'.")
        
        # Add file to the record's tracking
        record.add_item(path)
        
        # Update processing metrics for observability
        FILES_PROCESSED_BY_RECORD.labels(record_id=record.identifier).inc()
        
        # Persist the updated state to disk
        self.save_records()

    def remove_item_from_record(self, path: str, record: LocalRecord):
        """
        Remove a file path from a record.
        
        Note: Implementation appears incomplete - should call record.remove_item()
        and handle metrics update if needed.
        """
        # TODO: Add actual removal logic
        self.save_records()

    def save_records(self):
        """
        Persists all processed records to a dictionary ledger for crash recovery and state preservation.
        """
        logger.debug(f"Persisting {len(self.persist_records_dict)} records.")
        save_persisted_records(self.persist_records_dict)

    def get_all_records(self) -> Dict[str, LocalRecord]:
        """
        Get all currently loaded records.
        
        Returns:
            Dict mapping record IDs to LocalRecord instances
        """
        return self.persist_records_dict

    def get_num_records(self) -> int:
        """
        Get the total count of currently loaded records.
        
        Returns:
            int: Number of records in memory
        """
        count = len(self.persist_records_dict)
        logger.debug(f"Total number of records: {count}")
        return count

    def get_record_by_id(self, record_id: str) -> Optional[LocalRecord]:
        """
        Retrieve a specific record by its identifier.
        
        Performs case-insensitive lookup for robustness.
        
        Args:
            record_id: The record identifier to search for
            
        Returns:
            LocalRecord if found, None otherwise
        """
        record_id = record_id.lower()  # Normalize for case-insensitive lookup
        record = self.persist_records_dict.get(record_id)
        
        if record:
            logger.debug(f"Found record with identifier '{record_id}'.")
        else:
            logger.debug(f"No record found with identifier '{record_id}'.")
        return record

    def all_records_uploaded(self) -> bool:
        """
        Check if all records have been fully uploaded to the database.
        
        Used to determine if local cleanup can proceed or if sync is needed.
        
        Returns:
            bool: True if all records are fully uploaded, False otherwise
        """
        all_uploaded = all(
            record.all_files_uploaded() for record in self.persist_records_dict.values()
        )
        logger.debug(f"All records uploaded: {all_uploaded}")
        return all_uploaded

    def sync_records_to_database(self):
        """
        Synchronize all eligible records to the external database.
        
        Processing logic:
        1. Skip non-IPAT records (institute filter)
        2. Skip already fully uploaded records  
        3. Sync remaining records and track progress
        
        Records are synced independently of file processors since all files
        have already been processed and organized by their respective processors.
        """
        logger.info("Starting synchronization of records to the database.")
        synced_count = 0

        # Process each record, creating a list copy to avoid modification during iteration
        for record in list(self.persist_records_dict.values()):
            if record.institute != "ipat":
                # Skip records from other institutes (not applicable for this database)
                logger.info(
                    f"Record '{record.identifier}' is not applicable for syncing."
                )
            elif record.all_files_uploaded():
                # Skip records that are already fully synchronized
                logger.info(f"Record '{record.identifier}' is already fully uploaded.")
            else:
                # Sync eligible record to database
                logger.info(f"Syncing record '{record.identifier}' to the database.")
                self._sync_record(record)
                synced_count += 1

        logger.info(f"Synchronization of records completed. Synced: {synced_count}")


    # --------------------------
    # Internal Helper Methods
    # --------------------------

    def _store_record(self, record: LocalRecord):
        """Store a record in the in-memory dictionary using its identifier as key."""
        self.persist_records_dict[record.identifier] = record

    def _sync_record(self, record: LocalRecord):
        """
        Synchronize a single record to the database and handle cleanup.
        
        Uses the sync manager to upload record data.
        
        Args:
            record: LocalRecord to synchronize
        """
        # Delegate actual sync logic to the sync manager
        files_remaining = self.sync.sync_record_to_database(record)
        if not files_remaining:
            del self._persist_records_dict[record.identifier]
        self.save_records() 

        logger.debug(f"Persisted updated state for record '{record.identifier}' after sync.")
