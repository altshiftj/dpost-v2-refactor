"""File processing orchestrator: routes stable files into records via device plugins."""
from pathlib import Path
import queue
from typing import Tuple

from ipat_watchdog.metrics import FILES_FAILED
from ipat_watchdog.core.processing.file_processor_abstract import FileProcessorABS
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker
from ipat_watchdog.core.processing.processor_factory import FileProcessorFactory
from ipat_watchdog.core.config.settings_store import SettingsManager
from ipat_watchdog.core.storage.filesystem_utils import (
    parse_filename,
    get_record_path,
    generate_file_id,
    move_to_exception_folder,
)
from ipat_watchdog.core.processing.routing import (
    UNAPPENDABLE,
    APPEND_SYNCED,
    VALID_NAME,
    INVALID_NAME,
    fetch_record_for_prefix,
    determine_routing_state,
)
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.ui.ui_abstract import UserInterface
from ipat_watchdog.core.ui.ui_messages import WarningMessages, InfoMessages, ErrorMessages, DialogPrompts
from ipat_watchdog.core.processing.rename_flow import rename_flow_controller
from ipat_watchdog.core.processing.record_utils import (
    get_or_create_record,
    apply_device_defaults,
    update_record,
    manage_session,
)
from ipat_watchdog.core.processing.notifications import notify_success
from ipat_watchdog.core.processing.error_handling import (
    move_to_exception_and_inform as _move_to_exception_and_inform,
    handle_invalid_datatype as _handle_invalid_datatype,
)
from ipat_watchdog.core.processing.device_context import DeviceContext
from ipat_watchdog.core.processing.record_flow import (
    handle_unappendable_record as _handle_unappendable_record_flow,
    handle_append_to_synced_record as _handle_append_to_synced_record_flow,
)

logger = setup_logger(__name__)

# File processing routing states are provided by routing module

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
        settings_manager: SettingsManager | None = None,
        file_processor: FileProcessorABS | None = None,
    ):
        """Initialize the file process manager with required dependencies."""
        self.ui = ui
        self.session_manager = session_manager
        if settings_manager is None:
            # Fallback to global settings manager (used in tests)
            from ipat_watchdog.core.config.settings_store import SettingsStore
            settings_manager = SettingsStore.get_manager()
        self.settings_manager = settings_manager
        # Optional injection for testing
        self.file_processor = file_processor
        self.records = RecordManager(sync_manager=sync_manager)
        self._processor_factory = FileProcessorFactory()  # Cache processors by device_id

        # Single-threaded stability tracking — synchronous inline mode (no tracker storage needed)
        self._rejected_queue = queue.Queue()

        # Sync pending records upon startup
        if not self.records.all_records_uploaded():
            logger.debug("Syncing records to database upon startup.")
            self.sync_records_to_database()

    def process_item(self, src_path: str):
        """
        Main entry point for processing a new file or folder.
        Starts device-aware stability tracking, then processes when stable.
        """
        path = Path(src_path)
        device_settings = self.settings_manager.select_device_for_file(src_path)
        if device_settings is None:
            self._reject_immediately(path, "No device found that can process this file type")
            return
        # Ignore temp folders immediately
        if path.is_dir() and device_settings.TEMP_FOLDER_REGEX.search(path.name):
            logger.debug(f"Ignoring temp folder: {path.name}")
            return

        # Define callbacks that proceed after stability tracking
        def on_complete(p: str):
            self._handle_stable_file(p)

        def on_reject(p: str, reason: str):
            # Collect for DeviceWatchdogApp to surface to user
            self._rejected_queue.put((p, reason))
            self._handle_rejected_file(p, reason)

        tracker = FileStabilityTracker(
            file_path=path,
            device_settings=device_settings,
            completion_callback=on_complete,
            rejection_callback=on_reject,
        )
        # Synchronous tracker completes inline; nothing to store

    def _handle_stable_file(self, src_path: str):
        """Handle a file that has become stable - process it fully."""
        try:
            # Set device context for this processing
            with DeviceContext.from_file(self.settings_manager, src_path):
                file_processor = self._get_processor_for_file(src_path)
                logger.debug(
                    f"Selected processor for {src_path}: {type(file_processor).__name__}"
                )

                filename_prefix, extension = parse_filename(src_path)

                if not file_processor.is_valid_datatype(src_path):
                    self._handle_invalid_datatype(src_path, filename_prefix, extension)
                    FILES_FAILED.inc()
                    return

                preprocessed_src_path = file_processor.device_specific_preprocessing(
                    src_path
                )
                if preprocessed_src_path is None:
                    return

                final_filename_prefix, final_extension = parse_filename(
                    preprocessed_src_path
                )
                self._route_item(
                    src_path, final_filename_prefix, final_extension, file_processor
                )

        except Exception as e:
            logger.exception(f"Error processing stable file {src_path}: {e}")
            filename_prefix, extension = parse_filename(src_path)
            self._move_to_exception_and_inform(
                src_path,
                filename_prefix,
                extension,
                severity=ErrorMessages.PROCESSING_ERROR,
                message=ErrorMessages.PROCESSING_ERROR_DETAILS.format(
                    filename=Path(src_path).name, error=str(e)
                ),
            )

    def _handle_rejected_file(self, src_path: str, reason: str):
        """Handle a file that was rejected during stability tracking."""
        # Already removed by service callback; enqueue for external retrieval as well
        # (Service also enqueues; this keeps compatibility if needed.)
        pass

    def _reject_immediately(self, path: Path, reason: str):
        """Reject a file/folder without tracking and move it to exceptions."""
        logger.warning(f"Rejected immediately: {path.name} — {reason}")
        try:
            move_to_exception_folder(path)
        finally:
            self._rejected_queue.put((str(path), reason))

    def get_and_clear_rejected(self) -> list[Tuple[str, str]]:
        """Get and clear rejected files list."""
        items: list[Tuple[str, str]] = []
        while not self._rejected_queue.empty():
            try:
                items.append(self._rejected_queue.get_nowait())
            except queue.Empty:
                break
        return items

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
        # Prefer injected processor when available (backward-compat/testing)
        if getattr(self, "file_processor", None) is not None:
            return self.file_processor

        device_settings = self.settings_manager.select_device_for_file(src_path)
        
        if device_settings is None:
            raise RuntimeError(f"No device found that can process file: {src_path}")
        
        # Set the device context for this thread
        self.settings_manager.set_current_device(device_settings)

        # Import and get processor for the device via factory
        device_id = device_settings.get_device_id()
        try:
            return self._processor_factory.get_for_device(device_id)
        except ImportError as e:
            logger.error(f"Failed to load processor for device {device_id}: {e}")
            raise RuntimeError(f"No processor available for device: {device_id}") from e

    

    def _move_to_exception_and_inform(
        self, src_path: str, prefix: str, extension: str, severity: str, message: str
    ):
        _move_to_exception_and_inform(self.ui, src_path, prefix, extension, severity, message)
        logger.debug(
            f"Moved item '{src_path}' to exception folder with severity '{severity}'."
        )

    def _handle_invalid_datatype(self, src_path: str, filename_prefix: str, extension: str):
        _handle_invalid_datatype(self.ui, src_path, filename_prefix, extension)
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
        sanitized_prefix, is_valid_format, record = fetch_record_for_prefix(self.records, filename_prefix)
        
        # Determine routing state based on validation and record status
        state = determine_routing_state(record, is_valid_format, filename_prefix, extension, file_processor)

        # Route based on determined state
        if state == UNAPPENDABLE:
            _handle_unappendable_record_flow(
                self.ui,
                self._rename_flow_controller,
                src_path,
                sanitized_prefix,
                extension,
            )
        elif state == APPEND_SYNCED:
            _handle_append_to_synced_record_flow(
                self.ui,
                self.add_item_to_record,
                self._rename_flow_controller,
                record,
                src_path,
                sanitized_prefix,
                extension,
                file_processor,
            )
        elif state == VALID_NAME:
            self.add_item_to_record(record, src_path, sanitized_prefix, extension, file_processor, notify=False)
        else:
            rename_flow_controller(
                self.ui,
                self._get_processor_for_file,
                self._route_item,
                src_path,
                filename_prefix,
                extension,
            )

    # Backwards-compatible shim for tests or external callers that may still patch this method
    def _rename_flow_controller(self, src_path: str, filename_prefix: str, extension: str, contextual_reason: str = None):
        rename_flow_controller(
            self.ui,
            self._get_processor_for_file,
            self._route_item,
            src_path,
            filename_prefix,
            extension,
            contextual_reason=contextual_reason,
        )

    # Routing helpers moved to routing module

    # Append/unappend flows extracted to record_flow module

    # Rename flow is delegated to rename_flow module

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
            processor = file_processor
            if processor is None:
                raise RuntimeError("No file processor available")
            
            # Ensure we have a record to work with
            record = get_or_create_record(self.records, record, filename_prefix)

            # Determine device abbreviation for sorting
            device_settings = self.settings_manager.get_current_device()
            device_abbr = getattr(device_settings, "DEVICE_ABBR", None) if device_settings else None
            apply_device_defaults(record, device_settings)
            
            # Determine target paths and perform device-specific processing
            record_path = get_record_path(filename_prefix, device_abbr)
            file_id = generate_file_id(filename_prefix, device_abbr)
            final_path, datatype = processor.device_specific_processing(
                src_path, record_path, file_id, extension
            )

            # Update record with data type information
            record.datatype = datatype

            # Notify user of successful processing if requested
            if notify:
                notify_success(self.ui, src_path, final_path)

            logger.debug(
                f"{'Folder' if Path(src_path).is_dir() else 'File'} '{src_path}' moved/renamed to '{final_path}'."
            )

            # Update record tracking and manage session
            update_record(self.records, final_path, record)
            manage_session(self.session_manager)

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

    # record/session helper methods moved to record_utils module

    def sync_records_to_database(self):
        """Synchronize all pending records to database."""
        if self.records.all_records_uploaded():
            logger.debug("All records already uploaded, skipping sync.")
            return
            
        logger.debug("Syncing records to database.")
        self.records.sync_records_to_database()

    def shutdown(self):
        """Shutdown hook (no-op for synchronous tracking)."""
        return


