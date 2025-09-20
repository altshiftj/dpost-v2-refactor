"""Main application loop that orchestrates file watching, processing, and UI."""

import sys
from datetime import datetime
import queue
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ipat_watchdog.metrics import (
    FILES_PROCESSED,
    SESSION_DURATION,
    EXCEPTIONS_THROWN,
    FILES_FAILED,
    EVENTS_PROCESSED,
    FILE_PROCESS_TIME,
    SESSION_EXIT_STATUS,
)

from ipat_watchdog.core.config import ConfigService
from ipat_watchdog.core.interactions import ErrorMessages
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_process_manager import FileProcessManager
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.sync.sync_abstract import ISyncManager
from ipat_watchdog.core.ui.adapters import UiInteractionAdapter, UiTaskScheduler
from ipat_watchdog.core.ui.ui_abstract import UserInterface

logger = setup_logger(__name__)


class BasicFileEventHandler(FileSystemEventHandler):
    """Simple file detection handler - just queues new files/folders."""

    def __init__(self, event_queue: queue.Queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            logger.debug("File detected: %s", event.src_path)
            self.event_queue.put(event.src_path)
        else:
            logger.debug("Folder detected: %s", event.src_path)
            self.event_queue.put(event.src_path)


class DeviceWatchdogApp:
    """Coordinates file system monitoring, processing, UI handling, and syncing."""

    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        config_service: ConfigService,
        session_manager_cls=SessionManager,
        file_process_manager_cls=FileProcessManager,
    ) -> None:
        self.start_time = datetime.now()
        logger.info("WatchdogApp started at %s", self.start_time.isoformat())

        self.files_processed = 0
        self.config_service = config_service
        self.watch_dir = self.config_service.pc.paths.watch_dir

        self.ui = ui
        self.interactions = UiInteractionAdapter(ui)
        self.scheduler = UiTaskScheduler(ui)

        self.session_manager = session_manager_cls(
            interactions=self.interactions,
            scheduler=self.scheduler,
            end_session_callback=self.end_session,
        )
        self._processing_lock = threading.Lock()
        self._event_poll_handle = None

        self.observer = None
        self.event_handler = None
        self.event_queue: queue.Queue[str] = queue.Queue()

        if hasattr(sync_manager, "interactions"):
            sync_manager.interactions = self.interactions

        self.file_processing = file_process_manager_cls(
            interactions=self.interactions,
            sync_manager=sync_manager,
            session_manager=self.session_manager,
            config_service=self.config_service,
        )

    def initialize(self) -> None:
        """Initializes the file observer and UI loop."""
        logger.info("Monitoring directory: %s", self.watch_dir)

        self.event_handler = BasicFileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=str(self.watch_dir), recursive=False)
        self.observer.start()

        self._schedule_next_event_check()
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

    def _schedule_next_event_check(self) -> None:
        if self._event_poll_handle is None:
            self._event_poll_handle = self.scheduler.schedule(100, self.process_events)

    def process_events(self) -> None:
        """Check for processed files and handle rejections."""
        self._event_poll_handle = None
        try:
            src_path = self.event_queue.get_nowait()
            logger.debug("Processing queued item: %s", src_path)
            EVENTS_PROCESSED.inc()

            with self._processing_lock:
                with FILE_PROCESS_TIME.time():
                    self.file_processing.process_item(src_path)
        except queue.Empty:
            pass
        except Exception as exc:
            logger.exception("Error processing file: %s", exc)

        rejected = self.file_processing.get_and_clear_rejected()
        for path_str, reason in rejected:
            path_name = Path(path_str).name
            self.interactions.show_error(
                "Unsupported Input",
                f"The file or folder '{path_name}' was rejected.\n\n{reason}",
            )

        self._schedule_next_event_check()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        EXCEPTIONS_THROWN.inc()
        FILES_FAILED.inc()
        SESSION_EXIT_STATUS.set(1)
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.interactions.show_error(
            ErrorMessages.APPLICATION_ERROR,
            ErrorMessages.APPLICATION_ERROR_DETAILS,
        )
        self.on_closing()

    def end_session(self) -> None:
        logger.debug("End session called.")
        try:
            self.file_processing.sync_records_to_database()
        except Exception as exc:
            logger.exception("An error occurred during session end: %s", exc)
            self.interactions.show_error(
                ErrorMessages.SESSION_END_ERROR,
                ErrorMessages.SESSION_END_ERROR_DETAILS.format(error=exc),
            )
        finally:
            logger.debug("End session completed.")

    def on_closing(self) -> None:
        end_time = datetime.now()
        duration = end_time - self.start_time
        SESSION_DURATION.set(duration.total_seconds())
        logger.info("WatchdogApp shutdown at %s (uptime: %s)", end_time.isoformat(), duration)
        SESSION_EXIT_STATUS.set(0)

        if self.session_manager.session_active:
            self.session_manager.end_session()

        if self.observer:
            self.observer.stop()
            self.observer.join()

        if self._event_poll_handle is not None:
            self.scheduler.cancel(self._event_poll_handle)
            self._event_poll_handle = None

        self.ui.destroy()

        try:
            from prometheus_client import REGISTRY

            metric = next(m for m in REGISTRY.collect() if m.name == FILES_PROCESSED._name)
            total_processed = sum(
                sample.counter.value for sample in metric.samples if sample.name == FILES_PROCESSED._name
            )
        except Exception:
            total_processed = self.files_processed

        logger.info(
            "WatchdogApp shutdown summary: uptime=%s, files processed=%d",
            duration,
            int(total_processed),
        )

    def run(self) -> None:
        self.initialize()
        try:
            self.ui.run_main_loop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())
