"""Synchronous stability guard that blocks until a file stops changing."""

from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from dpost.application.config import DeviceConfig, StabilityOverride
from dpost.application.processing.stability_timing_policy import (
    StabilityTimingPolicy,
    resolve_stability_timing_policy,
)
from dpost.infrastructure.logging import setup_logger

logger = setup_logger(__name__)


class StabilityOutcomeKind(str, Enum):
    """Explicit outcomes returned by the stability tracker stage."""

    STABLE = "stable"
    DEFER = "defer"
    REJECT = "reject"


@dataclass(frozen=True)
class StabilityOutcome:
    """Result of waiting for a file/folder to settle."""

    path: Path
    stable: bool
    reason: Optional[str] = None
    kind: StabilityOutcomeKind | None = None
    retry_delay: float | None = None

    def __post_init__(self) -> None:
        inferred = self.kind
        if inferred is None:
            inferred = (
                StabilityOutcomeKind.STABLE
                if self.stable
                else StabilityOutcomeKind.REJECT
            )
            object.__setattr__(self, "kind", inferred)

        if self.stable and inferred is not StabilityOutcomeKind.STABLE:
            raise ValueError("Stable outcomes must use StabilityOutcomeKind.STABLE")
        if not self.stable and inferred is StabilityOutcomeKind.STABLE:
            raise ValueError(
                "Non-stable outcomes cannot use StabilityOutcomeKind.STABLE"
            )
        if inferred is not StabilityOutcomeKind.DEFER and self.retry_delay is not None:
            raise ValueError(
                "retry_delay is only valid for deferred stability outcomes"
            )

    @classmethod
    def stable_result(cls, path: Path) -> "StabilityOutcome":
        """Build a stable outcome with explicit kind semantics."""
        return cls(path=path, stable=True, kind=StabilityOutcomeKind.STABLE)

    @classmethod
    def defer(
        cls,
        path: Path,
        *,
        reason: str,
        retry_delay: float | None = None,
    ) -> "StabilityOutcome":
        """Build a deferred (non-rejected) stability outcome."""
        return cls(
            path=path,
            stable=False,
            reason=reason,
            kind=StabilityOutcomeKind.DEFER,
            retry_delay=retry_delay,
        )

    @classmethod
    def reject(
        cls,
        path: Path,
        *,
        reason: str,
    ) -> "StabilityOutcome":
        """Build a rejected stability outcome."""
        return cls(
            path=path,
            stable=False,
            reason=reason,
            kind=StabilityOutcomeKind.REJECT,
        )

    @property
    def rejected(self) -> bool:
        return self.kind is StabilityOutcomeKind.REJECT

    @property
    def deferred(self) -> bool:
        """Return True when the path should be retried instead of rejected."""
        return self.kind is StabilityOutcomeKind.DEFER


class FileStabilityTracker:
    """Inline (blocking) stability tracker used by the processing pipeline."""

    def __init__(self, file_path: Path, device: DeviceConfig | None) -> None:
        self.file_path = Path(file_path)
        self.device = device
        self._stability_override: Optional[StabilityOverride] = self._resolve_override()
        self._timing_policy: StabilityTimingPolicy = resolve_stability_timing_policy(
            self.device,
            self._stability_override,
        )

    def wait(self) -> StabilityOutcome:
        timing = self._timing_policy
        deadline = dt.datetime.now() + dt.timedelta(seconds=timing.max_wait_seconds)
        last_snapshot = self._snapshot()
        stable_cycles = 0

        poll_seconds = timing.poll_seconds
        # Optional disappear/reappear grace window (e.g., Office safe-save)
        reappear_deadline: Optional[dt.datetime] = None
        reappear_window = timing.reappear_window_seconds
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
                return StabilityOutcome.reject(
                    self.file_path,
                    reason="Path disappeared before becoming stable",
                )

            if dt.datetime.now() >= deadline:
                return StabilityOutcome.reject(
                    self.file_path,
                    reason=f"Timeout (> {timing.max_wait_seconds}s)",
                )

            current_snapshot = self._snapshot()
            if current_snapshot != last_snapshot:
                last_snapshot = current_snapshot
                stable_cycles = 0
                self._sleep(poll_seconds)
                continue

            stable_cycles += 1
            if stable_cycles < timing.stable_cycles:
                self._sleep(poll_seconds)
                continue

            if self._await_sentinel(poll_seconds):
                continue

            logger.info("File/folder is stable: %s", self.file_path.name)
            return StabilityOutcome.stable_result(self.file_path)

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
        return self._timing_policy.poll_seconds

    def _max_wait_seconds(self) -> int:
        return self._timing_policy.max_wait_seconds

    def _stable_cycles(self) -> int:
        return self._timing_policy.stable_cycles

    def _reappear_window_seconds(self) -> float:
        return self._timing_policy.reappear_window_seconds

    @staticmethod
    def _sleep(seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)
