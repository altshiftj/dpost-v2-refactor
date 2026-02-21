"""Application UI port contracts for dpost runtime typing boundaries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Sequence


@dataclass(frozen=True)
class SessionPromptDetails:
    """Snapshot of session activity for done-prompt presentation."""

    users: Sequence[str] = ()
    records: Sequence[str] = ()


class UserInterface(ABC):
    """Abstract UI contract used by runtime orchestration code."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize UI resources before main-loop execution."""

    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """Display a warning message."""

    @abstractmethod
    def show_info(self, title: str, message: str) -> None:
        """Display an informational message."""

    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """Display an error message."""

    @abstractmethod
    def prompt_rename(self) -> Optional[Dict[str, str]]:
        """Collect rename values from the user, or return None when cancelled."""

    @abstractmethod
    def show_rename_dialog(
        self, attempted_filename: str, violation_info: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """Collect rename values for a specific attempted filename."""

    @abstractmethod
    def prompt_append_record(self, record_name: str) -> bool:
        """Ask whether the current artifact should append to an existing record."""

    @abstractmethod
    def show_done_dialog(
        self,
        session_details: SessionPromptDetails,
        on_done_callback: Callable[[], None],
    ) -> None:
        """Present a completion prompt and invoke callback when acknowledged."""

    @abstractmethod
    def get_root(self) -> Any:
        """Return the backing UI root object when available."""

    @abstractmethod
    def destroy(self) -> None:
        """Dispose UI resources and stop the event loop."""

    @abstractmethod
    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> Any:
        """Schedule a one-shot callback and return a cancellation handle."""

    @abstractmethod
    def cancel_task(self, handle: Any) -> None:
        """Cancel a previously scheduled callback."""

    @abstractmethod
    def set_close_handler(self, callback: Callable[[], None]) -> None:
        """Register callback invoked for user close events."""

    @abstractmethod
    def set_exception_handler(self, callback: Callable[..., None]) -> None:
        """Register callback invoked for unhandled UI exceptions."""

    @abstractmethod
    def run_main_loop(self) -> None:
        """Start and block on the UI event loop."""
