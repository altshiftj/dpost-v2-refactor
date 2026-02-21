"""Headless runtime UI adapter used for non-desktop startup mode."""

from __future__ import annotations

import heapq
import itertools
import threading
import time
from typing import Any, Callable

from dpost.application.ports import SessionPromptDetails, UserInterface


class HeadlessRuntimeUI(UserInterface):
    """Minimal non-interactive UI implementation with an in-process scheduler."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._scheduled: list[tuple[float, int]] = []
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._handles = itertools.count(1)
        self._close_handler: Callable[[], None] | None = None
        self._exception_handler: Callable[..., None] | None = None
        self._destroyed = False

    def initialize(self) -> None:
        """Initialize headless UI state."""

    def show_warning(self, title: str, message: str) -> None:
        """Suppress warning dialogs in headless runtime mode."""

    def show_info(self, title: str, message: str) -> None:
        """Suppress informational dialogs in headless runtime mode."""

    def show_error(self, title: str, message: str) -> None:
        """Suppress error dialogs in headless runtime mode."""

    def prompt_rename(self) -> dict[str, str] | None:
        """Return no rename input in non-interactive mode."""
        return None

    def show_rename_dialog(
        self, attempted_filename: str, violation_info: dict[str, str]
    ) -> dict[str, str] | None:
        """Return no rename input in non-interactive mode."""
        return None

    def prompt_append_record(self, record_name: str) -> bool:
        """Auto-approve append prompts in non-interactive mode."""
        return True

    def show_done_dialog(
        self,
        session_details: SessionPromptDetails,
        on_done_callback: Callable[[], None],
    ) -> None:
        """Execute callback immediately in headless mode."""
        on_done_callback()

    def get_root(self) -> Any:
        """Return no UI root object for headless mode."""
        return None

    def destroy(self) -> None:
        """Signal the headless event loop to stop."""
        with self._condition:
            self._destroyed = True
            self._condition.notify_all()

    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> int:
        """Schedule a callback to run after the given interval."""
        delay_seconds = max(interval_ms, 0) / 1000.0
        run_at = time.monotonic() + delay_seconds
        handle = next(self._handles)
        with self._condition:
            self._callbacks[handle] = callback
            heapq.heappush(self._scheduled, (run_at, handle))
            self._condition.notify_all()
        return handle

    def cancel_task(self, handle: Any) -> None:
        """Cancel a previously scheduled callback handle."""
        if isinstance(handle, int):
            with self._condition:
                self._callbacks.pop(handle, None)

    def set_close_handler(self, callback: Callable[[], None]) -> None:
        """Store the close handler for API compatibility."""
        self._close_handler = callback

    def set_exception_handler(self, callback: Callable[..., None]) -> None:
        """Store exception handler used by scheduled callbacks."""
        self._exception_handler = callback

    def run_main_loop(self) -> None:
        """Run scheduled callbacks until destroyed."""
        while True:
            due_callbacks: list[Callable[[], None]] = []
            with self._condition:
                if self._destroyed:
                    return

                now = time.monotonic()
                while self._scheduled and self._scheduled[0][0] <= now:
                    _run_at, handle = heapq.heappop(self._scheduled)
                    callback = self._callbacks.pop(handle, None)
                    if callback is not None:
                        due_callbacks.append(callback)

                if not due_callbacks:
                    wait_timeout = 0.1
                    if self._scheduled:
                        wait_timeout = max(self._scheduled[0][0] - now, 0.01)
                    self._condition.wait(timeout=wait_timeout)
                    continue

            for callback in due_callbacks:
                try:
                    callback()
                except Exception as exc:  # noqa: BLE001
                    if self._exception_handler is None:
                        raise
                    self._exception_handler(type(exc), exc, exc.__traceback__)
