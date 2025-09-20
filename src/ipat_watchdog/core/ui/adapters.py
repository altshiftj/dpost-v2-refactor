"""Adapters that translate domain interaction calls into UI implementation calls."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict

from ipat_watchdog.core.interactions import (
    RenameDecision,
    RenamePrompt,
    SessionPromptDetails,
    TaskScheduler,
    UserInteractionPort,
)

from .ui_abstract import UserInterface


class UiInteractionAdapter(UserInteractionPort):
    """Bridges domain interaction requests onto a concrete ``UserInterface`` implementation."""

    def __init__(self, ui: UserInterface):
        self._ui = ui

    def show_info(self, title: str, message: str) -> None:
        self._ui.show_info(title, message)

    def show_warning(self, title: str, message: str) -> None:
        self._ui.show_warning(title, message)

    def show_error(self, title: str, message: str) -> None:
        self._ui.show_error(title, message)

    def prompt_append_record(self, record_name: str) -> bool:
        return self._ui.prompt_append_record(record_name)

    def request_rename(self, prompt: RenamePrompt) -> RenameDecision:
        analysis_payload: Dict[str, Any] = deepcopy(prompt.analysis)
        if prompt.contextual_reason:
            reasons = list(analysis_payload.get("reasons", []))
            reasons.insert(0, prompt.contextual_reason)
            analysis_payload["reasons"] = reasons

        result = self._ui.show_rename_dialog(prompt.attempted_prefix, analysis_payload)
        if result is None:
            return RenameDecision(cancelled=True, values=None)
        return RenameDecision(cancelled=False, values=result)

    def show_done_prompt(
        self, session_details: SessionPromptDetails, on_done_callback: Callable[[], None]
    ) -> None:
        self._ui.show_done_dialog(session_details, on_done_callback)


class UiTaskScheduler(TaskScheduler):
    """Task scheduler backed by a ``UserInterface`` event loop implementation."""

    def __init__(self, ui: UserInterface):
        self._ui = ui

    def schedule(self, interval_ms: int, callback: Callable[[], None]) -> Any:
        return self._ui.schedule_task(interval_ms, callback)

    def cancel(self, handle: Any) -> None:
        self._ui.cancel_task(handle)
