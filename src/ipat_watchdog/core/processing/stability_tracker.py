"""
Device-aware file/folder stability tracking utilities.

This module provides a reusable FileStabilityTracker that can be used by
components that need to wait until files or directories are fully written
before proceeding.

Kept intentionally independent from FileProcessManager so it can be reused
by watchers or other orchestrators in the future.
"""
from __future__ import annotations

from pathlib import Path
import threading
import datetime as dt
from typing import Callable, Any

from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.storage.filesystem_utils import move_to_exception_folder

logger = setup_logger(__name__)


class FileStabilityTracker:
    """
    Device-aware file stability tracker.

    Uses device-specific settings for polling intervals, stability criteria,
    temp file patterns, and sentinel file requirements.

    Callbacks:
    - completion_callback(path: str): invoked when the path is stable
    - rejection_callback(path: str, reason: str): invoked if rejected
    """

    def __init__(
        self,
        file_path: Path,
        device_settings: Any,
        completion_callback: Callable[[str], None],
        rejection_callback: Callable[[str, str], None],
    ) -> None:
        self.file_path = file_path
        self.device_settings = device_settings
        self.completion_callback = completion_callback
        self.rejection_callback = rejection_callback

        self._start_time = dt.datetime.now()
        self._last_metrics = self._snapshot()
        self._stable_count = 0
        self._timer: threading.Timer | None = None
        self._stopped = False

        logger.debug(
            f"Stability tracker started for {file_path.name} with device {getattr(device_settings, 'DEVICE_ID', 'unknown')}"
        )
        self._schedule_probe()

    def _snapshot(self):
        """Take snapshot of file/folder state for stability comparison."""
        if not self.file_path.exists():
            return None

        if self.file_path.is_file():
            s = self.file_path.stat()
            return s.st_size, s.st_mtime

        # For folders - count files and total size, excluding temp files
        file_count = 0
        total_size = 0
        newest_mtime = 0.0

        for p in self.file_path.rglob("*"):
            if p.is_file() and not p.name.endswith(self.device_settings.TEMP_PATTERNS):
                try:
                    s = p.stat()
                    file_count += 1
                    total_size += s.st_size
                    newest_mtime = max(newest_mtime, s.st_mtime)
                except FileNotFoundError:
                    continue

        return file_count, total_size, newest_mtime

    def _schedule_probe(self) -> None:
        """Schedule next stability check."""
        if self._stopped:
            return
        self._timer = threading.Timer(self.device_settings.POLL_SECONDS, self._probe)
        self._timer.start()

    def _probe(self) -> None:
        """Check file stability and handle completion or continuation."""
        try:
            if self._stopped:
                return

            if not self.file_path.exists():
                self._reject("Path disappeared before becoming stable")
                return

            # Check for timeout
            elapsed = (dt.datetime.now() - self._start_time).total_seconds()
            if elapsed >= self.device_settings.MAX_WAIT_SECONDS:
                self._reject(f"Timeout (> {self.device_settings.MAX_WAIT_SECONDS}s)")
                return

            # Compare current state with last snapshot
            current = self._snapshot()
            if current != self._last_metrics:
                # Still changing - reset stability counter
                self._last_metrics = current
                self._stable_count = 0
                self._schedule_probe()
                return

            # Increment stability counter
            self._stable_count += 1
            if self._stable_count < self.device_settings.STABLE_CYCLES:
                # Not stable enough yet
                self._schedule_probe()
                return

            # Check sentinel file requirement for folders
            if self.file_path.is_dir() and getattr(self.device_settings, "SENTINEL_NAME", None):
                sentinel = self.file_path / self.device_settings.SENTINEL_NAME
                if not sentinel.exists():
                    logger.debug(
                        f"Waiting for sentinel {sentinel.name} in {self.file_path.name}"
                    )
                    self._schedule_probe()
                    return

            # File/folder is stable - notify completion
            logger.info(
                f"{'Folder' if self.file_path.is_dir() else 'File'} stable & ready: {self.file_path.name}"
            )
            self.completion_callback(str(self.file_path))

        except Exception as e:
            logger.exception(f"Stability tracker error for {self.file_path}: {e}")
            self._reject(f"Tracking error: {e}")

    def _reject(self, reason: str) -> None:
        """Handle rejection of unstable or problematic files."""
        if not self.file_path.exists():
            logger.debug(f"Path vanished during rejection: {self.file_path.name}")
            self.stop()
            return

        logger.warning(f"File/Folder rejected: {self.file_path.name} — {reason}")
        move_to_exception_folder(self.file_path)
        self.rejection_callback(str(self.file_path), reason)
        self.stop()

    def stop(self) -> None:
        """Stop the stability tracker."""
        self._stopped = True
        if self._timer:
            self._timer.cancel()
            self._timer = None
