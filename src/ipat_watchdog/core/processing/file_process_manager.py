"""
File Process Manager - Core file processing orchestrator for IPAT Data Watchdog.

This module handles the complete lifecycle of incoming files, from initial validation
through final placement in organized record structures. It coordinates between the
UI, session management, record management, and device-specific file processors.
"""
from pathlib import Path
import threading

from ipat_watchdog.metrics import FILES_FAILED
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.storage.filesystem_utils import (
    parse_filename,
    move_to_exception_folder,
    move_to_rename_folder,
    get_record_path,
    generate_record_id,
    generate_file_id,
    sanitize_and_validate,
    explain_filename_violation,
    analyze_user_input,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import WarningMessages, InfoMessages, ErrorMessages, DialogPrompts

logger = setup_logger(__name__)

# File processing routing states - determines how files are handled based on validation
UNAPPENDABLE = "unappendable_record"  # File cannot be added to existing record
APPEND_SYNCED = "append_to_synced"    # File being added to already-synced record
VALID_NAME = "valid_name"             # File has valid naming convention
INVALID_NAME = "invalid_name"         # File naming doesn't meet requirements


class FileProcessManager:
    """
    Central coordinator for file processing workflow.
    
    Manages the complete file processing pipeline from initial file detection
    through final placement in organized records. Handles validation, user
    interaction for naming issues, session management, and database synchronization.
    
    Key responsibilities:
    - Route files based on naming validation and record state
    - Handle user interactions for file naming corrections
    - Coordinate with device-specific file processors
    - Manage session lifecycle and database synchronization
    """
    
    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        session_manager: SessionManager,
        file_processor: FileProcessorABS = None,  # Made optional for backward compatibility
    ):
        """Initialize the file process manager with required dependencies."""
        self.ui = ui
        self.session_manager = session_manager
        self.records = RecordManager(sync_manager=sync_manager)
        self.file_processor = file_processor  # Keep for backward compatibility
        self._processor_cache = {}  # Cache processors by device_id to maintain state
        self._processing_lock = threading.Lock()  # Sequential processing lock

        # Sync pending records upon startup
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def _get_processor_for_file(self, src_path: str) -> FileProcessorABS:
        """
        Get the appropriate file processor for a given file.
        
        Args:
            src_path: Path to the file to process
            
        Returns:
            FileProcessorABS: The appropriate file processor
            
        Raises:
            RuntimeError: If no suitable processor is found
        """
        # If we have a legacy single processor, use it
        if self.file_processor is not None:
            return self.file_processor
        
        # Use settings manager to find appropriate device
        settings_manager = SettingsStore.get_manager()
        device_settings = settings_manager.select_device_for_file(src_path)
        
        if device_settings is None:
            raise RuntimeError(f"No device found that can process file: {src_path}")
        
        # Set the device context for this thread
        settings_manager.set_current_device(device_settings)
        
        # Import and get processor for the device
        device_id = device_settings.get_device_id()
        
        # Check cache first
        if device_id in self._processor_cache:
            return self._processor_cache[device_id]
        
        try:
            # Dynamic import of device plugin
            plugin_module = __import__(
                f'ipat_watchdog.device_plugins.{device_id}.plugin',
                fromlist=['']
            )
            
            # For sem_phenomxl2, the class is SEMPhenomXL2Plugin
            if device_id == 'sem_phenomxl2':
                plugin_class = getattr(plugin_module, 'SEMPhenomXL2Plugin')
            elif device_id == 'utm_zwick':
                plugin_class = getattr(plugin_module, 'UTMZwickPlugin')
            else:
                # Try to find the plugin class by convention
                plugin_class = None
                for attr_name in dir(plugin_module):
                    attr = getattr(plugin_module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, 'get_file_processor') and 
                        attr_name.endswith('Plugin') and
                        not getattr(attr, '__abstractmethods__', None)):  # Exclude abstract classes
                        plugin_class = attr
                        break
                
                if plugin_class is None:
                    raise ImportError(f"No plugin class found in {device_id}.plugin")
            
            plugin_instance = plugin_class()
            processor = plugin_instance.get_file_processor()
            
            # Cache the processor for this device
            self._processor_cache[device_id] = processor
            return processor
        except ImportError as e:
            logger.error(f"Failed to load processor for device {device_id}: {e}")
            raise RuntimeError(f"No processor available for device: {device_id}") from e

    def process_item(self, src_path: str):
        """
        Main entry point for processing a new file or folder.
        
        Orchestrates the complete processing workflow:
        1. Device selection and processor loading
        2. Device-specific preprocessing
        3. Filename parsing and validation
        4. Data type validation
        5. Routing to appropriate handling logic
        
        Args:
            src_path: Path to the file or folder to process
        """
        with self._processing_lock:
            try:
                # Get the appropriate processor for this file
                file_processor = self._get_processor_for_file(src_path)
                logger.debug(f"Selected processor for {src_path}: {type(file_processor).__name__}")
                
                # Extract filename prefix and extension before validation
                filename_prefix, extension = parse_filename(src_path)

                # Validate that this is a supported data type for the device
                if not file_processor.is_valid_datatype(src_path):
                    self._handle_invalid_datatype(src_path, filename_prefix, extension)
                    FILES_FAILED.inc()
                    return
                
                # Allow device-specific preprocessing (e.g., folder consolidation)
                preprocessed_src_path = file_processor.device_specific_preprocessing(src_path)
                if preprocessed_src_path is None:
                    return

                # Extract filename prefix and extension AFTER preprocessing to handle normalization
                final_filename_prefix, final_extension = parse_filename(preprocessed_src_path)

                # Route the item based on validation and record state
                # Pass original src_path for device processing, but use preprocessed filename for record ID
                self._route_item(src_path, final_filename_prefix, final_extension, file_processor)
                
            except RuntimeError as e:
                # Handle cases where no processor is found
                filename_prefix, extension = parse_filename(src_path)
                logger.error(f"No processor found for {src_path}: {e}")
                self._move_to_exception_and_inform(
                    src_path,
                    filename_prefix,
                    extension,
                    severity=WarningMessages.INVALID_DATA_TYPE,
                    message=f"No device available to process this file type: {Path(src_path).name}",
                )
                FILES_FAILED.inc()
            except Exception as e:
                filename_prefix, extension = parse_filename(src_path)
                logger.exception(f"Error while processing item: {e}")
                self._move_to_exception_and_inform(
                    src_path,
                    filename_prefix,
                    extension,
                    severity=ErrorMessages.PROCESSING_ERROR,
                    message=ErrorMessages.PROCESSING_ERROR_DETAILS.format(
                        filename=Path(src_path).name, error=str(e)
                    ),
                )
            finally:
                # Clear device context for this thread
                try:
                    settings_manager = SettingsStore.get_manager()
                    settings_manager.set_current_device(None)
                except Exception:
                    pass  # Ignore cleanup errors

    def _move_to_exception_and_inform(
        self, src_path: str, prefix: str, extension: str, severity: str, message: str
    ):
        """
        Move problematic files to exception folder and notify user.
        
        Used when files cannot be processed due to validation errors,
        processing failures, or other issues requiring manual intervention.
        """
        move_to_exception_folder(src_path, prefix, extension)
        if severity.lower() == "warning":
            self.ui.show_warning(severity, message)
        else:
            self.ui.show_error(severity, message)

        logger.debug(f"Moved item '{src_path}' to exception folder with severity '{severity}'.")

    def _handle_invalid_datatype(self, src_path: str, filename_prefix: str, extension: str):
        """Handle files that don't match the device's supported data types."""
        self._move_to_exception_and_inform(
            src_path,
            filename_prefix,
            extension,
            severity="Warning",
            message=WarningMessages.INVALID_DATA_TYPE_DETAILS,
        )
        logger.debug(f"Moved invalid item '{src_path}' to exception folder.")

    def _route_item(self, src_path: str, filename_prefix: str, extension: str, file_processor: FileProcessorABS):
        """
        Route files to appropriate handling based on naming validation and record state.
        
        Determines the current state of the file and record, then routes to:
        - Unappendable record handling (file can't be added to existing record)
        - Append to synced record handling (adding to already-uploaded record)
        - Valid name handling (standard processing)
        - Invalid name handling (rename flow)
        """
        # Get sanitized filename and check if record exists
        sanitized_prefix, is_valid_format, record = self._fetch_record_for_prefix(filename_prefix)
        
        # Determine routing state based on validation and record status
        state = self._determine_routing_state(record, is_valid_format, filename_prefix, extension, file_processor)

        # Route based on determined state
        if state == UNAPPENDABLE:
            self._handle_unappendable_record(src_path, sanitized_prefix, extension)
        elif state == APPEND_SYNCED:
            self._handle_append_to_synced_record(record, src_path, sanitized_prefix, extension, file_processor)
        elif state == VALID_NAME:
            self.add_item_to_record(record, src_path, sanitized_prefix, extension, file_processor, notify=False)
        else:
            self._rename_flow_controller(src_path, filename_prefix, extension)

    def _fetch_record_for_prefix(self, filename_prefix: str) -> tuple[str, bool, LocalRecord]:
        """
        Retrieve or validate record information for a filename prefix.
        
        Returns:
            tuple: (sanitized_prefix, is_valid_format, existing_record)
                - sanitized_prefix: Cleaned version of the filename prefix
                - is_valid_format: Whether the prefix follows naming conventions
                - existing_record: LocalRecord if one exists, None otherwise
        """
        sanitized_prefix, is_valid_format = sanitize_and_validate(filename_prefix)
        record_id = generate_record_id(sanitized_prefix)
        record = self.records.get_record_by_id(record_id)
        return sanitized_prefix, is_valid_format, record

    def _determine_routing_state(
        self, record: LocalRecord, is_valid_format: bool, filename_prefix: str, extension: str, file_processor: FileProcessorABS
    ) -> str:
        """
        Determine how to route the file based on validation and record state.
        
        Logic:
        1. If record exists but file can't be appended -> UNAPPENDABLE
        2. If record exists and is fully synced -> APPEND_SYNCED (needs user confirmation)
        3. If record exists or name is valid -> VALID_NAME (standard processing)
        4. Otherwise -> INVALID_NAME (requires rename flow)
        """
        if record and not file_processor.is_appendable(record, filename_prefix, extension):
            return UNAPPENDABLE
        if record and record.is_in_db and record.all_files_uploaded():
            return APPEND_SYNCED
        if record or is_valid_format:
            return VALID_NAME
        return INVALID_NAME

    def _handle_unappendable_record(self, src_path: str, filename_prefix: str, extension: str):
        """Handle files that cannot be appended to their target record."""
        self.ui.show_warning(
            WarningMessages.INVALID_RECORD, WarningMessages.INVALID_RECORD_DETAILS
        )
        # Force rename flow with context about why the file can't be appended
        self._rename_flow_controller(
            src_path,
            filename_prefix,
            extension,
            contextual_reason=DialogPrompts.UNAPPENDABLE_RECORD_CONTEXT.format(
                record_id=filename_prefix
            ),
        )

    def _handle_append_to_synced_record(self, record, src_path, filename_prefix, extension, file_processor: FileProcessorABS):
        """
        Handle files being added to records that have already been synced to database.
        
        Requires user confirmation since this will modify an already-uploaded record.
        """
        if self.ui.prompt_append_record(filename_prefix):
            # User confirmed - add the file to the existing record
            self.add_item_to_record(record, src_path, filename_prefix, extension, file_processor)
        else:
            # User declined - force rename flow
            self._rename_flow_controller(
                src_path,
                filename_prefix,
                extension,
                contextual_reason=DialogPrompts.APPEND_RECORD_CANCEL_CONTEXT.format(
                    record_id=filename_prefix
                ),
            )

    def _rename_flow_controller(
        self,
        src_path: str,
        filename_prefix: str,
        extension: str,
        contextual_reason: str = None,
    ):
        """
        Manage the interactive rename flow for files with naming issues.
        
        Guides user through correcting filename to meet naming conventions.
        If user cancels or rename fails, moves file to rename folder for manual handling.
        
        Args:
            contextual_reason: Additional context about why rename is needed
        """
        # Start interactive rename loop with user
        new_prefix = self._interactive_rename_loop(
            filename_prefix, last_attempt=None, contextual_reason=contextual_reason
        )

        if new_prefix is not None:
            # User provided valid new name - retry processing with new name
            try:
                file_processor = self._get_processor_for_file(src_path)
                self._route_item(src_path, new_prefix, extension, file_processor)
            except RuntimeError as e:
                logger.error(f"Failed to get processor for retry: {e}")
                move_to_rename_folder(src_path, filename_prefix, extension)
                self.ui.show_error("Processing Error", f"Unable to process file: {e}")
            return

        # User cancelled rename - move to rename folder for manual handling
        move_to_rename_folder(src_path, filename_prefix, extension)
        self.ui.show_info(
            InfoMessages.OPERATION_CANCELLED, InfoMessages.MOVED_TO_RENAME
        )

    def _interactive_rename_loop(
        self,
        filename_prefix: str,
        last_attempt: str = None,
        contextual_reason: str = None,
    ) -> str | None:
        """
        Interactive loop for getting valid filename from user.
        
        Continues until user provides valid name or cancels.
        Provides feedback on validation failures to guide user.
        
        Returns:
            str: Valid sanitized filename prefix, or None if user cancelled
        """
        # Start with original filename or user's last attempt
        attempted = last_attempt if last_attempt else filename_prefix
        last_analysis = explain_filename_violation(attempted)

        # Add contextual reason to help user understand why rename is needed
        if contextual_reason:
            last_analysis["reasons"].insert(0, contextual_reason)

        while True:
            # Show rename dialog with current attempt and validation feedback
            user_input = self.ui.show_rename_dialog(attempted, last_analysis)
            if user_input is None:
                return None  # User cancelled

            # Validate user's input
            analysis = analyze_user_input(user_input)
            if analysis["valid"]:
                return analysis["sanitized"]  # Valid input - return sanitized version
            else:
                # Invalid input - reconstruct attempted name and continue loop
                attempted = f"{user_input.get('name', '')}-{user_input.get('institute', '')}-{user_input.get('sample_ID', '')}"
                last_analysis = analysis

    def add_item_to_record(self, record, src_path, filename_prefix, extension, file_processor: FileProcessorABS = None, notify=True):
        """
        Add a validated file/folder to a record and organize it properly.
        
        This is the final step of successful file processing:
        1. Get or create the target record
        2. Determine target path and perform device-specific processing
        3. Update record metadata
        4. Manage session state
        
        Args:
            record: Existing LocalRecord or None to create new one
            src_path: Source path of file/folder to process
            filename_prefix: Validated filename prefix
            extension: File extension
            file_processor: File processor to use (falls back to self.file_processor if None)
            notify: Whether to show success notification to user
        """
        try:
            # Use provided processor or fall back to instance processor
            processor = file_processor or self.file_processor
            if processor is None:
                raise RuntimeError("No file processor available")
            
            # Ensure we have a record to work with
            record = self._get_or_create_record(record, filename_prefix)

            # Determine device abbreviation for sorting
            settings_manager = SettingsStore.get_manager()
            device_settings = settings_manager.get_current_device()
            device_abbr = getattr(device_settings, "DEVICE_ABBR", None) if device_settings else None
            # Determine target paths and perform device-specific processing
            record_path = get_record_path(filename_prefix, device_abbr)
            file_id = generate_file_id(filename_prefix)
            final_path, datatype = processor.device_specific_processing(
                src_path, record_path, file_id, extension
            )

            # Update record with data type information
            record.datatype = datatype

            # Notify user of successful processing if requested
            if notify:
                self._notify_success(src_path, final_path)

            logger.debug(
                f"{'Folder' if Path(src_path).is_dir() else 'File'} '{src_path}' moved/renamed to '{final_path}'."
            )

            # Update record tracking and manage session
            self._update_record(final_path, record)
            self._manage_session()

        except Exception as e:
            # Handle processing failures gracefully
            self.ui.show_error("Error", ErrorMessages.RENAME_FAILED.format(error=str(e)))
            self._move_to_exception_and_inform(
                src_path,
                filename_prefix,
                extension,
                severity="Error",
                message="Failed to rename.",
            )

    def _notify_success(self, src_path: str, final_path: str):
        """Show success notification to user about processed item."""
        item_type = "Folder" if Path(src_path).is_dir() else "File"
        self.ui.show_info(
            InfoMessages.SUCCESS,
            InfoMessages.ITEM_RENAMED.format(
                item_type=item_type, filename=Path(final_path).name
            ),
        )

    def _update_record(self, final_path: str, record: LocalRecord):
        """Update record tracking with newly processed item."""
        self.records.add_item_to_record(final_path, record)

    def _manage_session(self):
        """
        Manage session lifecycle based on file processing activity.
        
        Starts new session if none active, or resets timer if session ongoing.
        Sessions group related files and trigger database sync on timeout.
        """
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            logger.debug("Started a new session.")
        else:
            self.session_manager.reset_timer()
            logger.debug("Session is active. Timer reset.")

    def _get_or_create_record(self, record: LocalRecord, filename_prefix: str) -> LocalRecord:
        """Get existing record or create new one if none exists."""
        return record if record else self.records.create_record(filename_prefix)

    def sync_records_to_database(self):
        """Synchronize all pending records to database with proper device context."""
        if self.records.all_records_uploaded():
            logger.debug("All records already uploaded, skipping sync.")
            return
            
        logger.debug("Syncing records to database with device context.")
        settings_manager = SettingsStore.get_manager()
        
        for record in self.records.get_all_records().values():
            if record.all_files_uploaded():
                continue
                
            device_settings = self._get_device_for_record(record)
            if not device_settings:
                logger.warning(f"No device found for record {record.identifier}, skipping")
                continue
                
            settings_manager.set_current_device(device_settings)
            try:
                self.records.sync.sync_record_to_database(record)
                self.records.save_records()
            except Exception as e:
                logger.error(f"Failed to sync record {record.identifier}: {e}")
            finally:
                settings_manager.set_current_device(None)

    def _get_device_for_record(self, record: LocalRecord):
        """Get compatible device for record based on file paths."""
        settings_manager = SettingsStore.get_manager()
        
        for file_path in record.files_uploaded.keys():
            return settings_manager.select_device_for_file(file_path)
        
        return None
