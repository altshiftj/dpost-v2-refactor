"""Main application loop that orchestrates file watching, processing, and UI."""

from __future__ import annotations

import queue
import sys
import threading
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from dpost.application.config import ConfigService
from dpost.application.interactions import ErrorMessages
from dpost.application.metrics import (
    EVENTS_PROCESSED,
    EXCEPTIONS_THROWN,
    FILE_PROCESS_TIME,
    FILES_FAILED,
    FILES_PROCESSED,
    SESSION_DURATION,
    SESSION_EXIT_STATUS,
)
from dpost.application.ports import SyncAdapterPort, UserInterface
from dpost.application.processing import (
    FileProcessManager,
    ProcessingResult,
)
from dpost.application.runtime.retry_planner import build_retry_plan
from dpost.application.retry_delay_policy import RetryDelayPolicy
from dpost.application.session import SessionManager
from dpost.infrastructure.logging import setup_logger
from dpost.infrastructure.runtime import UiInteractionAdapter, UiTaskScheduler

logger = setup_logger(__name__)


class QueueingEventHandler(FileSystemEventHandler):
    """Minimal handler that forwards created/modified paths into a queue."""

    def __init__(
        self, event_queue: queue.Queue[str], should_queue_modified=None
    ) -> None:
        super().__init__()
        self._event_queue = event_queue
        self._should_queue_modified = should_queue_modified

    def on_created(self, event: FileSystemEvent) -> None:
        kind = "Folder" if event.is_directory else "File"
        logger.debug("%s detected: %s", kind, event.src_path)
        self._event_queue.put(str(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._should_queue_modified is None:
            return
        try:
            if not self._should_queue_modified(event.src_path):
                return
        except Exception as exc:  # noqa: BLE001
            logger.debug("Modified event skipped for %s: %s", event.src_path, exc)
            return
        logger.debug("File modified: %s", event.src_path)
        self._event_queue.put(str(event.src_path))


class DeviceWatchdogApp:
    """Coordinates file system monitoring, processing, UI handling, and syncing."""

    def __init__(
        self,
        ui: UserInterface,
        sync_manager: SyncAdapterPort,
        config_service: ConfigService,
        interactions: UiInteractionAdapter | None = None,
        scheduler: UiTaskScheduler | None = None,
        session_manager_cls=SessionManager,
        file_process_manager_cls=FileProcessManager,
        observer_factory: Callable[[], BaseObserver] | None = None,
    ) -> None:
        self.start_time = datetime.now()
        logger.info("WatchdogApp started at %s", self.start_time.isoformat())

        self.config_service = config_service
        self.watch_dir = self.config_service.pc.paths.watch_dir

        self.ui = ui
        self.interactions = interactions or UiInteractionAdapter(ui)
        self.scheduler = scheduler or UiTaskScheduler(ui)

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
        self._session_failed = False

        if hasattr(sync_manager, "interactions"):
            sync_manager.interactions = self.interactions

        self._processing_lock = threading.Lock()
        self._event_poll_handle: int | None = None
        self.event_queue: queue.Queue[str] = queue.Queue()
        self.event_handler: QueueingEventHandler | None = None
        self.observer: BaseObserver | None = None
        self._observer_factory = observer_factory

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

        handler = QueueingEventHandler(
            self.event_queue,
            should_queue_modified=self.file_processing.should_queue_modified,
        )
        observer_factory = self._observer_factory or Observer
        observer = observer_factory()
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
                    result = self.file_processing.process_item(src_path)
                self._handle_processing_result(src_path, result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error processing file: %s", exc)

    def _handle_processing_result(
        self, src_path: str, result: ProcessingResult | None
    ) -> None:
        retry_plan = build_retry_plan(
            src_path,
            result,
            default_delay_seconds=self._default_retry_delay(),
        )
        if retry_plan is not None:
            self._schedule_retry(retry_plan.path, retry_plan.delay_seconds)

    def _handle_rejections(self) -> None:
        for path_str, reason in self.file_processing.get_and_clear_rejected():
            path_name = Path(path_str).name
            self.interactions.show_error(
                "Unsupported Input",
                f"The file or folder '{path_name}' was rejected.\n\n{reason}",
            )

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        EXCEPTIONS_THROWN.inc()
        FILES_FAILED.inc()
        self._session_failed = True
        SESSION_EXIT_STATUS.set(1)
        logger.error(
            "An unexpected error occurred",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        self.interactions.show_error(
            ErrorMessages.APPLICATION_ERROR,
            ErrorMessages.APPLICATION_ERROR_DETAILS,
        )
        self.on_closing()

    def on_closing(self) -> None:
        end_time = datetime.now()
        duration = end_time - self.start_time
        SESSION_DURATION.set(duration.total_seconds())
        if not self._session_failed:
            SESSION_EXIT_STATUS.set(0)

        logger.info(
            "WatchdogApp shutdown at %s (uptime: %s)", end_time.isoformat(), duration
        )

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

            metric = next(
                m for m in REGISTRY.collect() if m.name == FILES_PROCESSED._name
            )
            accumulated = sum(
                sample.value
                for sample in metric.samples
                if sample.name == FILES_PROCESSED._name
            )
            return int(accumulated)
        except Exception:
            return 0

    def _schedule_retry(self, path: str, delay_seconds: float) -> None:
        safe_delay = RetryDelayPolicy(
            default_delay_seconds=self._default_retry_delay()
        ).normalize(delay_seconds)
        logger.debug("Re-queuing %s in %.2f seconds", path, safe_delay)
        milliseconds = int(safe_delay * 1000)
        self.scheduler.schedule(milliseconds, partial(self._enqueue_if_present, path))

    def _default_retry_delay(self) -> float:
        return RetryDelayPolicy().coerce(
            getattr(self.config_service.pc.watcher, "retry_delay_seconds", None)
        )

    def _enqueue_if_present(self, path: str) -> None:
        if Path(path).exists():
            self.event_queue.put(path)
            return
        logger.debug("Skipping retry for vanished path: %s", path)
