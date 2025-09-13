"""
Stability service: manage file/folder stability trackers and rejections.

Creates and owns FileStabilityTracker instances per path, wiring completion
and rejection callbacks. Also exposes a small queue of rejected items for
diagnostics/metrics.
"""
from __future__ import annotations

from pathlib import Path
import threading
import queue
from typing import Callable, Any

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.stability_tracker import FileStabilityTracker
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


class StabilityService:
    def __init__(self) -> None:
        self._trackers: dict[str, FileStabilityTracker] = {}
        self._lock = threading.RLock()
        self._rejected_queue: queue.Queue[tuple[str, str]] = queue.Queue()

    def start_tracking(
        self,
        file_path: Path,
        device_settings: Any,
        completion_callback: Callable[[str], None],
        rejection_callback: Callable[[str, str], None],
    ) -> bool:
        """
        Begin tracking stability for a path using the provided device settings.
        Returns True if tracking started; False if ignored.
        """
        # Ignore temp folders immediately
        if file_path.is_dir() and device_settings.TEMP_FOLDER_REGEX.search(file_path.name):
            logger.debug(f"Ignoring temp folder: {file_path.name}")
            return False

        with self._lock:
            key = str(file_path)
            # Stop existing tracker if any
            if key in self._trackers:
                self._trackers[key].stop()

            # Wrap callbacks to ensure cleanup
            def on_complete(path: str):
                with self._lock:
                    self._trackers.pop(key, None)
                completion_callback(path)

            def on_reject(path: str, reason: str):
                with self._lock:
                    self._trackers.pop(key, None)
                self._rejected_queue.put((path, reason))
                rejection_callback(path, reason)

            tracker = FileStabilityTracker(
                file_path=file_path,
                device_settings=device_settings,
                completion_callback=on_complete,
                rejection_callback=on_reject,
            )
            self._trackers[key] = tracker
            return True

    def reject_immediately(self, file_path: Path, reason: str) -> None:
        """Reject a file/folder without tracking and move it to exceptions."""
        logger.warning(f"Rejected immediately: {file_path.name} — {reason}")
        move_to_exception_folder(file_path)
        self._rejected_queue.put((str(file_path), reason))

    def get_and_clear_rejected(self) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        while not self._rejected_queue.empty():
            try:
                items.append(self._rejected_queue.get_nowait())
            except queue.Empty:
                break
        return items

    def shutdown(self) -> None:
        """Stop and clear all active trackers."""
        with self._lock:
            for tracker in list(self._trackers.values()):
                tracker.stop()
            self._trackers.clear()
