from __future__ import annotations

from typing import Any, Optional

from ipat_watchdog.core.config import current
from ipat_watchdog.core.interactions import TaskScheduler, UserInteractionPort
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


class SessionManager:
    """Manages the lifecycle of a user session, including timeouts and session state."""

    def __init__(
        self,
        interactions: UserInteractionPort,
        scheduler: TaskScheduler,
        end_session_callback=None,
    ) -> None:
        """Initialise a new session manager detached from concrete UI concerns."""
        self._interactions = interactions
        self._scheduler = scheduler
        self.end_session_callback = end_session_callback
        self.session_active = False
        self.timer_id: Optional[Any] = None

    @property
    def is_active(self) -> bool:
        return self.session_active

    def start_session(self) -> None:
        if not self.session_active:
            logger.debug("Starting a new session.")
            self.session_active = True
            self._schedule_timeout()
            self._interactions.show_done_prompt(self.end_session)

    def end_session(self) -> None:
        if self.session_active:
            logger.debug("Ending the current session.")
            self.session_active = False
            self._cancel_timer()
            if self.end_session_callback:
                self.end_session_callback()

    def reset_timer(self) -> None:
        if self.session_active:
            logger.debug("Resetting session timeout timer.")
            self._schedule_timeout()

    def _schedule_timeout(self) -> None:
        self._cancel_timer()
        timeout_seconds = current().session_timeout
        if timeout_seconds < 0:
            logger.debug("Session timeout disabled (value: %s).", timeout_seconds)
            return
        timeout_ms = timeout_seconds * 1000
        self.timer_id = self._scheduler.schedule(timeout_ms, self.end_session)

    def _cancel_timer(self) -> None:
        if self.timer_id is not None:
            self._scheduler.cancel(self.timer_id)
            self.timer_id = None
