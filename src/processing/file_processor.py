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
from src.records.local_record import LocalRecord
# these carry state
from src.sessions.session_manager import SessionManager
from src.records.record_manager import RecordManager
from src.gui.user_interface import UserInterface
from src.sync.sync_manager import SyncManager
from src.app.logger import setup_logger

logger = setup_logger(__name__)



class FileProcessorWrapper:

    def __init__(
        self,
        ui:                 UserInterface,
        session_manager:    SessionManager,
        file_processor:     'BaseFileProcessor',
    ):
        self.ui                 = ui
        self.session_manager    = session_manager
        self.records            = RecordManager(
            sync_manager=SyncManager(ui=ui) 
            )   # i feel like we can avoid the ui with the syncmanager
        self.file_processor:    BaseFileProcessor   = file_processor

        # initialize directories
        PathManager.init_dirs()

        # If any record is not fully uploaded, sync on startup
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()
            if not self.records.is_dict_up_to_date():
                self.records.reset_dict()

    def process_item(self, src_path: str):
        """
        Entry point when a file/folder is created or modified.
        """
        base_name = os.path.basename(src_path)
        filename_prefix, extension = os.path.splitext(base_name)

        # Validate data type TODO CHANGE THIS attribtue manipulation of itemdatatype
        valid_datatype, self.file_processor.item_data_type = self.file_processor.is_valid_datatype(src_path)
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
        # Ensure the in-memory record dict is up to date
        if not self.records.is_dict_up_to_date():
            self.records.reset_dict()

        # Sanitize the name (remove illegal chars, etc.)
        sanitized_filename_prefix, is_valid_format = PathManager.sanitize_and_validate_name(filename_prefix)
        record = self.records.get_record_by_short_id(sanitized_filename_prefix)

        # Decide 'state' of the item
        item_state = self._determine_routing_state(record, is_valid_format)

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

    def _determine_routing_state(self, record: LocalRecord, is_valid_format: bool) -> str:
        """
        Returns a string denoting how we should handle the incoming item:
          - 'unappendable_record'
          - 'append_to_synced'
          - 'valid_name'
          - 'invalid_name'
        """
        if record:
            # If record can't be appended to for device-specific reasons:
            if not self.file_processor.is_record_appendable(record):
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
                "Format: Institute-UserName-Sample Name"
            )
        
        # Optional message for creating a new record name
        if new_record_prompt:
            self.ui.show_info(
                "New Record",
                "Please enter the name for a new record (Format: Institute-UserName-Sample Name)"
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
                        "Please avoid special characters (e.g., !@#$%^&*_+=) and follow the naming convention."
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
            file_id = IdGenerator.generate_file_id(filename_prefix)
            record_path = PathManager.get_record_path(record)
            os.makedirs(record_path, exist_ok=True)

            final_path = self.file_processor.device_specific_processing(
                record_path, file_id, src_path, filename_prefix, extension
            )

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
        # TODO remove item datatype from interdependence
        record_info = IdGenerator.generate_new_record_info(
            filename_prefix=filename_prefix,
            data_type=self.file_processor.item_data_type,
            record_count=self.records.get_num_records(),
        )
        return self.records.create_record(record_info)

    def sync_records_to_database(self):
        """
        Syncs the in-memory records to the external database.
        """
        self.records.sync_records_to_database()

class BaseFileProcessor(ABC):
    """
    An abstract base for processors that handle new/modified files or directories
    and associate them with records in the system.
    """
    # Holds the data type for the item being processed
    item_data_type = None 

    @abstractmethod
    def is_valid_datatype(self, path: str):
        """
        Checks if the file/folder at the given path is valid for this processor.
        Returns (bool, str|None) -> (is_valid, data_type).
        """
        pass

    @abstractmethod
    def is_record_appendable(self, record: LocalRecord) -> bool:
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
    
class SEMFileProcessor(BaseFileProcessor):
    """
    A concrete processor for PhenomXL SEM data (TIFF images or .elid directories).
    """

    def is_valid_datatype(self, path: str):
        """
        Checks if path is a TIFF/TIF file or a folder containing .elid files.
        """
        if os.path.isdir(path):
            if any(f.endswith('.elid') for f in os.listdir(path)):
                return True, 'ELID'
        if path.lower().endswith(('.tiff', '.tif')):
            return True, 'IMG'
        return False, None

    def is_record_appendable(self, record: LocalRecord) -> bool:
        """
        Disallow appending to records that already represent an ELID directory.
        """
        if 'elid' in record.long_id:
            return False
        return True

    def device_specific_processing(self, record_path, file_id, src_path, filename_prefix, extension):
        """
        For ELID data, flatten subdirectories first.
        For TIF/TIFF, just rename and move the file.
        """
        if self.item_data_type == 'ELID':
            self._flatten_elid_directory(src_path, filename_prefix)
            new_dir_path = os.path.join(record_path, file_id)
            StorageManager.move_item(src_path, new_dir_path)
            return new_dir_path
        else:
            # For images, create a unique filename
            new_file_path = PathManager.get_unique_filename(record_path, file_id, extension)
            StorageManager.move_item(src_path, new_file_path)
            return new_file_path

    def _flatten_elid_directory(self, folder_path: str, filename_prefix: str):
        """
        Eliminates subdirectories, renames .elid/.odt, etc. in-place.
        """
        logger.debug(f"Flattening ELID directory: {folder_path}")
        target_dir = folder_path
        renamed_files = {}

        for root, dirs, files in os.walk(folder_path, topdown=False):
            for fname in files:
                old_path = os.path.join(root, fname)
                new_fname = self._build_new_filename(fname, root, filename_prefix)
                
                # Ensure uniqueness
                counter = 1
                original_new_fname = new_fname
                while (new_fname in renamed_files or 
                       os.path.exists(os.path.join(target_dir, new_fname))):
                    name_only, ext = os.path.splitext(original_new_fname)
                    new_fname = f"{name_only}_{counter}{ext}"
                    counter += 1

                renamed_files[new_fname] = True
                new_path = os.path.join(target_dir, new_fname)

                try:
                    StorageManager.move_item(old_path, new_path)
                    logger.debug(f"Moved and renamed '{old_path}' to '{new_path}'.")
                except OSError as e:
                    logger.error(f"Failed to move '{old_path}' to '{new_path}': {e}")

            # Remove the subdirectory if empty
            if root != folder_path:
                try:
                    os.rmdir(root)
                    logger.debug(f"Removed empty directory: '{root}'.")
                except OSError:
                    logger.warning(f"Could not remove directory (not empty): '{root}'.")

        logger.debug("Subdirectories flattened for ELID data.")

    def _build_new_filename(self, fname: str, root_dir: str, filename_prefix: str) -> str:
        """
        Builds a new file name for .elid/.odt files or files in analysis/export folders.
        """
        # Default: keep original
        new_fname = fname

        # If .elid/.odt: incorporate base_name
        if fname.endswith('.elid') or fname.endswith('.odt'):
            _, ext = os.path.splitext(fname)
            new_fname = f"{filename_prefix}{ext}"
            new_fname = new_fname.replace(' ', '_')

        # If inside an analysis directory, prefix that folder name
        dirname = os.path.basename(root_dir)
        if 'analysis' in dirname:
            new_fname = f"{dirname}_{fname}".replace(' ', '_')
            if 'analysis' in fname:
                new_fname = fname.replace(' ', '_')

        # If inside an export directory, do a simpler rename
        if 'export' in dirname:
            new_fname = fname.replace(' ', '_')

        return new_fname