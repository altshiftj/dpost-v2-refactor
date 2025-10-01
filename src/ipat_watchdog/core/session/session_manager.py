"""Tracks user activity and session timeouts for watchdog processing runs.

Public API additions:
    - ``SessionManager.get_summary()`` returns a lightweight immutable snapshot
      for external consumers (logging, UI layers, potential REST exposure)
      without leaking internal mutable lists.

Headless / 'it just works' mode:
    Pass interactive=False to disable all UI prompts while still tracking
    users, records, and honoring (optional) timeouts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from ipat_watchdog.core.config import current
from ipat_watchdog.core.interactions import SessionPromptDetails, TaskScheduler, UserInteractionPort
from ipat_watchdog.core.logging.logger import setup_logger

if TYPE_CHECKING:
    from ipat_watchdog.core.records.local_record import LocalRecord

logger = setup_logger(__name__)


@dataclass(frozen=True)
class SessionSummary:
    """Immutable snapshot of current session state."""
    active: bool
    users: tuple[str, ...]
    records: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:  # pragma: no cover
        return {"active": self.active, "users": self.users, "records": self.records}


class SessionManager:
    """Manages the lifecycle of a user session, including timeouts and session state.

    interactive=False disables UI prompts (headless mode) while still tracking activity.
    """

    def __init__(
        self,
        interactions: UserInteractionPort,
        scheduler: TaskScheduler,
        end_session_callback=None,
        interactive: bool = True,
    ) -> None:
        self._interactions = interactions
        self._scheduler = scheduler
        self.end_session_callback = end_session_callback
        self.session_active = False
        self.timer_id: Optional[Any] = None
        self._session_users: list[str] = []
        self._session_records: list[str] = []
        self._interactive = interactive

    @property
    def is_active(self) -> bool:
        return self.session_active

    @property
    def interactive(self) -> bool:
        return self._interactive

    def set_interactive(self, enabled: bool) -> None:
        if self._interactive == enabled:
            return
        prev = self._interactive
        self._interactive = enabled
        logger.debug("SessionManager interactive mode changed: %s -> %s", prev, enabled)
        if enabled and self.session_active:
            self._refresh_prompt()

    def note_activity(self, record: "LocalRecord") -> None:
        """Record session activity; in headless mode suppress UI prompts."""
        user_tag = self._derive_user_tag(record)
        record_label = self._derive_sample_label(record)

        if not self.session_active:
            self._reset_session_activity()

        self._push_unique(self._session_users, user_tag)
        self._push_unique(self._session_records, record_label)

        if not self.session_active:
            self.start_session()
        else:
            self.reset_timer()
            self._refresh_prompt()

        if not self._interactive:
            logger.debug(
                "Headless session activity: users=%s records=%s",
                self._session_users,
                self._session_records,
            )

    def start_session(self) -> None:
        if not self.session_active:
            logger.debug("Starting a new session.")
            self.session_active = True
            self._schedule_timeout()
            self._refresh_prompt()

    def end_session(self) -> None:
        if self.session_active:
            logger.debug("Ending the current session.")
            self.session_active = False
            self._cancel_timer()
            if self.end_session_callback:
                self.end_session_callback()
            self._reset_session_activity()

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

    def _refresh_prompt(self) -> None:
        if not self.session_active or not self._interactive:
            return
        details = self._current_prompt_details()
        self._interactions.show_done_prompt(details, self.end_session)

    def _current_prompt_details(self) -> SessionPromptDetails:
        return SessionPromptDetails(
            users=tuple(self._session_users),
            records=tuple(self._format_record_label(label) for label in self._session_records),
        )

    def _format_record_label(self, label: Optional[str]) -> str:
        if not label:
            return "Unknown Sample"
        return label

    def _reset_session_activity(self) -> None:
        self._session_users = []
        self._session_records = []

    # Public convenience API
    def get_summary(self) -> SessionSummary:
        return SessionSummary(
            active=self.session_active,
            users=tuple(self._session_users),
            records=tuple(self._session_records),
        )

    @staticmethod
    def _push_unique(target: list[str], value: Optional[str]) -> None:
        if value and value not in target:
            target.append(value)

    def _derive_user_tag(self, record: "LocalRecord") -> Optional[str]:
        user = getattr(record, "user", None)
        institute = getattr(record, "institute", None)
        if not user or user == "null":
            return None
        if institute and institute != "null":
            return f"{user}-{institute}"
        return user

    def _derive_sample_label(self, record: "LocalRecord") -> Optional[str]:
        sample = getattr(record, "sample_name", None)
        if sample and sample != "null":
            return sample
        identifier = getattr(record, "identifier", None)
        if identifier and identifier != "null":
            parts = identifier.split("-")
            if len(parts) >= 4:
                return "-".join(parts[3:])
            return identifier
        return None