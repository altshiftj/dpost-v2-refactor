"""
file_processor.py

This module contains classes for processing and organizing files within the
data-watchdog system. The classes handle file validation, renaming, moving,
and tying them to existing or new records. They also manage interactions
between sessions, storage operations, and database synchronization.

Classes:
    BaseFileProcessor (abstract):
        Defines the common logic and interface for processing files (or folders)
        and linking them to local records.

    SEMFileProcessor:
        A specific implementation of BaseFileProcessor that handles PhenomXL SEM data types
        (e.g., TIFF images, .elid directories) with custom file/folder handling.
"""

from abc import ABC, abstractmethod
import os
# these are just namespaces
from src.processing.metadata_extractor import MetadataExtractor
from src.storage.storage_manager import StorageManager
from src.storage.path_manager import PathManager
from src.records.id_generator import IdGenerator

# these carry state
from src.records.local_record import LocalRecord
from src.sessions.session_manager import SessionManager
from src.records.record_manager import RecordManager
from src.gui.user_interface import UserInterface
from src.sync.sync_manager import KadiSyncManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class FileProcessManager:
    """
    Coordinates the overall workflow for new or updated files/folders within the
    data-watchdog system. This class acts as the primary entry point for file events:
    it validates file types via the configured BaseFileProcessor, manages user prompts
    (e.g., renaming and record decisions), handles session control, and updates or
    creates records accordingly. If a file does not meet criteria or the user opts out,
    it routes items to rename or exception folders. The FileProcessManager also ensures
    pending records are synchronized to the database on startup and after processing.
    """

    def __init__(
        self,
        ui:                 UserInterface,
        session_manager:    SessionManager,
        file_processor:     'BaseFileProcessor',
    ):
        self.ui                 = ui
        self.session_manager    = session_manager
        self.records            = RecordManager(sync_manager=KadiSyncManager(ui=ui))   #TODO: Decouple ui from sync_manager and generally
        self.file_processor:    BaseFileProcessor   = file_processor

        # initialize directories
        PathManager.init_dirs()

        # If any record is not fully uploaded, sync on startup
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def process_item(self, src_path: str):
        """
        Entry point when a file/folder is created or modified.
        """
        src_path = self.file_processor.device_specific_preprocessing(src_path)

        # TODO: Create helper function to extract and split the filename and extension
        base_name = os.path.basename(src_path)
        filename_prefix, extension = os.path.splitext(base_name)

        valid_datatype = self.file_processor.is_valid_datatype(src_path)
        if not valid_datatype:
            self._handle_invalid_datatype(src_path, filename_prefix, extension)
            return

        # Route item based on record name & state
        self._route_item(src_path, filename_prefix, extension)

    def _handle_invalid_datatype(self, src_path: str, filename_prefix: str, extension: str):
        """
        Moves invalid items to exception folder and informs the user.
        """
        StorageManager.move_to_exception_folder(src_path, filename_prefix, extension)
        self.ui.show_warning(
            "Invalid Data Type",
            "The file/folder is not a recognized data type.\n"
            "Only .tif/.tiff images and .elid directories are supported."
        )
        logger.debug(f"Moved invalid item '{src_path}' to exception folder.")

    def _route_item(self, src_path: str, filename_prefix: str, extension: str):
        """
        Determines how to process a valid item—whether it belongs to a known record
        or needs a new one, or if the naming is invalid.
        """
        # Sanitize the name (remove illegal chars, etc.)
        sanitized_filename_prefix, is_valid_format = PathManager.sanitize_and_validate_name(filename_prefix)
        
        record_id = IdGenerator.generate_record_id(sanitized_filename_prefix)
        record = self.records.get_record_by_id(record_id)

        # Decide 'state' of the item
        item_state = self._determine_routing_state(record, is_valid_format, filename_prefix, extension)

        # Match on routing state
        match item_state:
            case 'unappendable_record':
                self._handle_unappendable_record(src_path, sanitized_filename_prefix, extension)
            case 'append_to_synced':
                self._handle_append_to_synced_record(record, src_path, sanitized_filename_prefix, extension)
            case 'valid_name':
                self.add_item_to_record(record, src_path, sanitized_filename_prefix, extension, notify=False)
            case 'invalid_name':
                self._prompt_item_rename(src_path, filename_prefix, extension)

    def _determine_routing_state(self, record: LocalRecord, is_valid_format: bool, filename_prefix: str, extension: str) -> str:
        """
        Returns a string denoting how we should handle the incoming item:
          - 'unappendable_record'
          - 'append_to_synced'
          - 'valid_name'
          - 'invalid_name'
        """
        if record:
            # If record can't be appended to for device-specific reasons:
            if not self.file_processor.is_appendable(record, filename_prefix, extension):
                return 'unappendable_record'
            
            # If record is fully synced in DB and user might want to attach more data:
            elif record.is_in_db and record.all_files_uploaded():
                return 'append_to_synced'
            
            else:
                return 'valid_name'
        
        elif is_valid_format:
            return 'valid_name'
        
        else:
            return 'invalid_name'

    def _handle_unappendable_record(self, src_path: str, filename_prefix: str, extension: str):
        """
        If the existing record is unappendable, prompt to rename and create a new record.
        """
        self.ui.show_warning(
            "Invalid Record",
            "An existing record with this name cannot be appended.\n"
            "Please create a new record for this data."
        )
        self._prompt_item_rename(src_path, filename_prefix, extension, bad_name_prompt=False)

    def _handle_append_to_synced_record(self, record, src_path, filename_prefix, extension):
        """
        If the record is synced but user may still want to append new data.
        """
        if self.ui.prompt_append_record(filename_prefix):
            self.add_item_to_record(record, src_path, filename_prefix, extension)
        else:
            # Prompt user for a new record name
            self._prompt_item_rename(src_path, filename_prefix, extension, bad_name_prompt=False, new_record_prompt=True)

    def _prompt_item_rename(self, src_path, filename_prefix, extension, bad_name_prompt=True, new_record_prompt=False):
        """
        Guides the user to rename the item properly. 
        Allows multiple attempts or cancellation (moves to rename folder).
        """
        # Optional warning prompt for invalid naming
        if bad_name_prompt:
            self.ui.show_warning(
                "Invalid Name",
                f"'{filename_prefix}{extension}' does not follow the naming convention.\n"
                "Format: User-Institute-Sample_Name\n"
                "No special characters (e.g., !@#$%^&*-+=)\n"
                "30 character limit for Sample Name."
            )
        
        # Optional message for creating a new record name
        if new_record_prompt:
            self.ui.show_info(
                "New Record",
                "Please enter a name for the new record."
            )

        # Keep asking until valid name or user cancels
        while True:
            user_input = self.ui.prompt_rename()  # Returns dict or None
            result, is_valid = PathManager.validate_user_input(user_input)

            if not is_valid:
                if result == "User cancelled the dialog.":
                    # Move to rename folder
                    StorageManager.move_to_rename_folder(src_path, filename_prefix, extension)
                    self.ui.show_info(
                        "Operation Cancelled",
                        "The item has been moved to the rename folder."
                    )
                    return
                elif result == "Invalid Parts":
                    # Field(s) contained invalid characters
                    self.ui.show_warning(
                        "Invalid Name",
                        "Please avoid special characters (e.g., !@#$%^&*-+=)\n"
                        "30 character limit for Sample Name."
                    )
                    continue
                else:
                    # Possibly incomplete fields, try again
                    self.ui.show_warning(
                        "Incomplete Information",
                        "All fields are required. Please try again."
                    )
                    continue

            self._route_item(src_path, result, extension)
            break

    def add_item_to_record(self, record, src_path, filename_prefix, extension, notify=True):
        """
        Attaches the file/folder to an existing or new record, then handles final storage.
        """
        try:
            # 1) Get or create record
            record = self._get_or_create_record(record, filename_prefix)

            # 2) Prepare final file path + device-specific ops
            record_path = PathManager.get_record_path(filename_prefix)

            file_id = IdGenerator.generate_file_id(filename_prefix)

            final_path, datatype = self.file_processor.device_specific_processing(
                src_path, record_path, file_id, extension
            )

            record.datatype = datatype

            # 3) Notify the user of success
            if notify:
                item_type = "Folder" if os.path.isdir(src_path) else "File"
                self.ui.show_info("Success", f"{item_type} renamed to '{os.path.basename(final_path)}'")

            logger.debug(
                f"{'Folder' if os.path.isdir(src_path) else 'File'} '{src_path}' "
                f"moved/renamed to '{final_path}'."
            )

            # 4) Add item to record + manage session
            self.records.add_item_to_record(final_path, record)

            if not self.session_manager.session_active:
                # No active session; start a new one
                self.session_manager.start_session()
                # Show a dialog informing the user that the session is active and can be ended
                self.ui.show_done_dialog(self.session_manager)
                logger.debug("Started a new session and displayed the 'Done' dialog.")
            else:
                # Session is active; reset the timer to extend the session
                self.session_manager.reset_timer()
                logger.debug("Session is active. Timer has been reset to extend the session.")


        except Exception as e:
            self.ui.show_error("Error", f"Failed to rename: {e}")
            StorageManager.move_to_exception_folder(src_path, filename_prefix, extension)

    def _get_or_create_record(self, record: LocalRecord, filename_prefix: str) -> LocalRecord:
        """
        Returns an existing record or creates a new one if `record` is None.
        """
        if record is not None:
            return record
        return self.records.create_record(filename_prefix)

    def sync_records_to_database(self):
        """
        Syncs the in-memory records to the external database.
        """
        self.records.sync_records_to_database()

    def sync_logs_to_database(self):
        """
        Syncs the log file to the external database.
        """
        self.records.sync_logs_to_database()

class BaseFileProcessor(ABC):
    """
    An abstract base for processors that handle new/modified files or directories
    and associate them with records in the system.
    """
    @abstractmethod
    def device_specific_preprocessing(self, src_path: str)-> str:
        """
        Method to implement optional preprocessing steps before routing the item.
        """
        pass
    
    @abstractmethod
    def is_valid_datatype(self, path: str):
        """
        Checks if the file/folder at the given path is valid for this processor.
        Returns (bool|None) -> (is_valid, data_type).
        """
        pass

    @abstractmethod
    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        """
        Checks if the record can be appended to with this processor’s data type.
        Return: (appendable, message_if_not_appendable)
        """
        pass

    @abstractmethod
    def device_specific_processing(
        self, record_path, file_id, source_path, filename_prefix, extension
    ):
        """
        Allows subclasses to implement custom moves, renames, or metadata extraction.
        Must return the final path of the processed item.
        """
        pass
