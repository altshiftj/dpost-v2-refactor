"""Main application loop that orchestrates file watching, processing, and UI."""

from __future__ import annotations

import queue
import sys
import threading
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from ipat_watchdog.metrics import (
    EVENTS_PROCESSED,
    EXCEPTIONS_THROWN,
    FILE_PROCESS_TIME,
    FILES_FAILED,
    FILES_PROCESSED,
    SESSION_DURATION,
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


class QueueingEventHandler(FileSystemEventHandler):
    """Minimal handler that forwards created paths into a queue."""

    def __init__(self, event_queue: queue.Queue[str]):
        super().__init__()
        self._event_queue = event_queue

    def on_created(self, event: FileSystemEvent) -> None:
        kind = "Folder" if event.is_directory else "File"
        logger.debug("%s detected: %s", kind, event.src_path)
        self._event_queue.put(event.src_path)


class DeviceWatchdogApp:
    """Coordinates file system monitoring, processing, UI handling, and syncing."""

    def __init__(
        self,
        ui: UserInterface,
        sync_manager: ISyncManager,
        config_service: ConfigService,
        interactions: UiInteractionAdapter | None = None,
        scheduler: UiTaskScheduler | None = None,
        session_manager_cls=SessionManager,
        file_process_manager_cls=FileProcessManager,
    ) -> None:
        self.start_time = datetime.now()
        logger.info("WatchdogApp started at %s", self.start_time.isoformat())

        self.config_service = config_service
        self.watch_dir = self.config_service.pc.paths.watch_dir

        self.ui = ui
        self.interactions = interactions or UiInteractionAdapter(ui)
        self.scheduler = scheduler or UiTaskScheduler(ui)

        # Headless session manager (interactive disabled) — end_session_callback removed
        self.session_manager = session_manager_cls(
            interactions=self.interactions,
            scheduler=self.scheduler,
            end_session_callback=None,
            interactive=False,
        )
        self.file_processing = file_process_manager_cls(
            interactions=self.interactions,
            sync_manager=sync_manager,
            session_manager=self.session_manager,
            config_service=self.config_service,
            immediate_sync=True,
        )

        if hasattr(sync_manager, "interactions"):
            sync_manager.interactions = self.interactions

        self._processing_lock = threading.Lock()
        self._event_poll_handle: int | None = None
        self.event_queue: queue.Queue[str] = queue.Queue()
        self.event_handler: QueueingEventHandler | None = None
        self.observer: BaseObserver | None = None

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """Initialise the file observer and UI loop hooks."""
        logger.info("Monitoring directory: %s", self.watch_dir)

        self._start_observer()
        self._schedule_next_event_check()
        self.ui.set_close_handler(self.on_closing)
        self.ui.set_exception_handler(self.handle_exception)

    def run(self) -> None:
        self.initialize()
        try:
            self.ui.run_main_loop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())

    def _start_observer(self) -> None:
        if self.observer is not None:
            return

        handler = QueueingEventHandler(self.event_queue)
        observer = Observer()
        observer.schedule(handler, path=str(self.watch_dir), recursive=False)
        observer.start()

        self.event_handler = handler
        self.observer = observer

    def _stop_observer(self) -> None:
        observer = self.observer
        if observer is None:
            return

        observer.stop()
        observer.join()

        self.observer = None
        self.event_handler = None

    def _schedule_next_event_check(self) -> None:
        if self._event_poll_handle is None:
            self._event_poll_handle = self.scheduler.schedule(100, self.process_events)

    def _cancel_event_poll(self) -> None:
        if self._event_poll_handle is not None:
            self.scheduler.cancel(self._event_poll_handle)
            self._event_poll_handle = None

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------
    def process_events(self) -> None:
        """Drain a single queue item, surface rejections, and reschedule."""
        self._event_poll_handle = None
        self._process_next_event()
        self._handle_rejections()
        self._schedule_next_event_check()

    def _process_next_event(self) -> None:
        try:
            src_path = self.event_queue.get_nowait()
        except queue.Empty:
            return

        logger.debug("Processing queued item: %s", src_path)
        EVENTS_PROCESSED.inc()

        try:
            with self._processing_lock:
                with FILE_PROCESS_TIME.time():
                    self.file_processing.process_item(src_path)
        except Exception as exc:  # noqa: BLE001 - keep broad to surface unexpected errors
            logger.exception("Error processing file: %s", exc)

    def _handle_rejections(self) -> None:
        for path_str, reason in self.file_processing.get_and_clear_rejected():
            path_name = Path(path_str).name
            self.interactions.show_error(
                "Unsupported Input",
                f"The file or folder '{path_name}' was rejected.\n\n{reason}",
            )

    # ------------------------------------------------------------------
    # Exception & shutdown handling
    # ------------------------------------------------------------------
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

    # end_session removed: syncing now occurs immediately per processed file.

    def on_closing(self) -> None:
        end_time = datetime.now()
        duration = end_time - self.start_time
        SESSION_DURATION.set(duration.total_seconds())
        SESSION_EXIT_STATUS.set(0)

        logger.info("WatchdogApp shutdown at %s (uptime: %s)", end_time.isoformat(), duration)

        # Session manager no-op for activity; explicit end not required.

        self._stop_observer()
        self._cancel_event_poll()
        self.ui.destroy()

        total_processed = self._collect_total_processed()
        logger.info(
            "WatchdogApp shutdown summary: uptime=%s, files processed=%d",
            duration,
            total_processed,
        )

    def _collect_total_processed(self) -> int:
        try:
            from prometheus_client import REGISTRY

            metric = next(m for m in REGISTRY.collect() if m.name == FILES_PROCESSED._name)
            accumulated = sum(
                sample.counter.value for sample in metric.samples if sample.name == FILES_PROCESSED._name
            )
            return int(accumulated)
        except Exception:  # noqa: BLE001 - metrics registry absent during tests/dev
            return 0
