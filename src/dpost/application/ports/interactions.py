"""Abstract interaction contracts that keep UI concerns decoupled."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from dpost.application.ports.ui import SessionPromptDetails


@dataclass(frozen=True)
class RenamePrompt:
    """Request data for asking the user to repair an invalid filename."""

    attempted_prefix: str
    analysis: Dict[str, Any]
    contextual_reason: Optional[str] = None


@dataclass(frozen=True)
class RenameDecision:
    """Response returned from a rename interaction."""

    cancelled: bool
    values: Optional[Dict[str, str]] = None


class UserInteractionPort(ABC):
    """Abstract boundary for presenting information or collecting user input."""

    @abstractmethod
    def show_info(self, title: str, message: str) -> None:
        """Display an informational message to the user."""

    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """Display a warning message to the user."""

    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """Display an error message to the user."""

    @abstractmethod
    def prompt_append_record(self, record_name: str) -> bool:
        """Ask whether a file should be appended to an existing record."""

    @abstractmethod
    def request_rename(self, prompt: RenamePrompt) -> RenameDecision:
        """Collect rename input from the user and return their decision."""

    @abstractmethod
    def show_done_prompt(
        self,
        session_details: SessionPromptDetails,
        on_done_callback: Callable[[], None],
    ) -> None:
        """Ask the user to confirm they are done with the current session."""


class TaskScheduler(ABC):
    """Simple scheduling abstraction so domain code stays UI-framework agnostic."""

    @abstractmethod
    def schedule(self, interval_ms: int, callback: Callable[[], None]) -> Any:
        """Schedule callback to run after interval milliseconds."""

    @abstractmethod
    def cancel(self, handle: Any) -> None:
        """Cancel a previously scheduled callback."""
