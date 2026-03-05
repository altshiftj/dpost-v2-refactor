"""Synchronous stability guard that blocks until a file stops changing."""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from ipat_watchdog.core.config import DeviceConfig, StabilityOverride
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


@dataclass(frozen=True)
class StabilityOutcome:
    """Result of waiting for a file/folder to settle."""

    path: Path
    stable: bool
    reason: Optional[str] = None

    @property
    def rejected(self) -> bool:
        return not self.stable


class FileStabilityTracker:
    """Inline (blocking) stability tracker used by the processing pipeline."""

    def __init__(self, file_path: Path, device: DeviceConfig | None) -> None:
        self.file_path = Path(file_path)
        self.device = device
        self._stability_override: Optional[StabilityOverride] = self._resolve_override()

    def wait(self) -> StabilityOutcome:
        deadline = dt.datetime.now() + dt.timedelta(seconds=self._max_wait_seconds())
        last_snapshot = self._snapshot()
        stable_cycles = 0

        poll_seconds = self._poll_seconds()
        # Optional disappear/reappear grace window (e.g., Office safe-save)
        reappear_deadline: Optional[dt.datetime] = None
        reappear_window = self._reappear_window_seconds()
        if reappear_window > 0:
            reappear_deadline = dt.datetime.now() + dt.timedelta(
                seconds=reappear_window
            )

        while True:
            if not self.file_path.exists():
                # If configured, allow a short window for the path to reappear (safe-save pattern)
                if (
                    reappear_deadline is not None
                    and dt.datetime.now() < reappear_deadline
                ):
                    self._sleep(poll_seconds)
                    continue
                return StabilityOutcome(
                    path=self.file_path,
                    stable=False,
                    reason="Path disappeared before becoming stable",
                )

            if dt.datetime.now() >= deadline:
                return StabilityOutcome(
                    path=self.file_path,
                    stable=False,
                    reason=f"Timeout (> {self._max_wait_seconds()}s)",
                )

            current_snapshot = self._snapshot()
            if current_snapshot != last_snapshot:
                last_snapshot = current_snapshot
                stable_cycles = 0
                self._sleep(poll_seconds)
                continue

            stable_cycles += 1
            if stable_cycles < self._stable_cycles():
                self._sleep(poll_seconds)
                continue

            if self._await_sentinel(poll_seconds):
                continue

            logger.info("File/folder is stable: %s", self.file_path.name)
            return StabilityOutcome(path=self.file_path, stable=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _await_sentinel(self, poll_seconds: float) -> bool:
        """Return True if we must wait for a sentinel to appear."""
        if self.device is None or not self.file_path.is_dir():
            return False
        sentinel_name = self.device.watcher.sentinel_name
        if not sentinel_name:
            return False
        sentinel_path = self.file_path / sentinel_name
        if sentinel_path.exists():
            return False
        logger.debug("Waiting for sentinel '%s' in %s", sentinel_name, self.file_path)
        self._sleep(poll_seconds)
        return True

    def _snapshot(self):
        if not self.file_path.exists():
            return None
        if self.file_path.is_file():
            stat = self.file_path.stat()
            return stat.st_size, stat.st_mtime
        file_count = 0
        total_size = 0
        newest_mtime = 0.0
        for child in self._iter_files(self.file_path):
            try:
                stat = child.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_size += stat.st_size
            newest_mtime = max(newest_mtime, stat.st_mtime)
        return file_count, total_size, newest_mtime

    def _iter_files(self, directory: Path) -> Iterable[Path]:
        temp_patterns: tuple[str, ...] = tuple()
        if self.device is not None:
            patterns = self.device.watcher.temp_patterns
            if isinstance(patterns, str):
                temp_patterns = (patterns.lower(),)
            else:
                temp_patterns = tuple(p.lower() for p in patterns)
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if temp_patterns and path.name.lower().endswith(temp_patterns):
                continue
            yield path

    def _resolve_override(self) -> Optional[StabilityOverride]:
        if self.device is None:
            return None
        overrides = getattr(self.device.watcher, "stability_overrides", tuple())
        if not overrides:
            return None
        for override in overrides:
            if override.matches(self.file_path):
                return override
        return None

    def _poll_seconds(self) -> float:
        override = self._stability_override
        if override is not None and override.poll_seconds is not None:
            return max(float(override.poll_seconds), 0.0)
        if self.device is None:
            return 1.0
        return max(float(self.device.watcher.poll_seconds), 0.0)

    def _max_wait_seconds(self) -> int:
        override = self._stability_override
        if override is not None and override.max_wait_seconds is not None:
            return int(override.max_wait_seconds)
        if self.device is None:
            return 300
        return int(self.device.watcher.max_wait_seconds)

    def _stable_cycles(self) -> int:
        override = self._stability_override
        if override is not None and override.stable_cycles is not None:
            return int(override.stable_cycles)
        if self.device is None:
            return 3
        return int(self.device.watcher.stable_cycles)

    def _reappear_window_seconds(self) -> float:
        """Return optional disappear/reappear grace period in seconds (0 disables)."""
        # If an override structure supports this in future, it can be added here similarly to _poll_seconds.
        if self.device is None:
            return 0.0
        try:
            value = getattr(self.device.watcher, "reappear_window_seconds", 0.0)
            return float(value) if value else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _sleep(seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)
