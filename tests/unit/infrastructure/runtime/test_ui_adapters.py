"""Unit coverage for runtime UI interaction and scheduler adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from dpost.application.ports import RenamePrompt, SessionPromptDetails
from dpost.infrastructure.runtime_adapters.ui_adapters import (
    UiInteractionAdapter,
    UiTaskScheduler,
)


@dataclass
class _UiStub:
    """Simple UI stub capturing interactions for adapter assertions."""

    info_calls: list[tuple[str, str]] = field(default_factory=list)
    warning_calls: list[tuple[str, str]] = field(default_factory=list)
    error_calls: list[tuple[str, str]] = field(default_factory=list)
    append_calls: list[str] = field(default_factory=list)
    rename_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    done_calls: list[SessionPromptDetails] = field(default_factory=list)
    scheduled_calls: list[tuple[int, Callable[[], None]]] = field(default_factory=list)
    cancelled_handles: list[Any] = field(default_factory=list)
    rename_result: dict[str, str] | None = None

    def show_info(self, title: str, message: str) -> None:
        """Capture informational dialog calls."""
        self.info_calls.append((title, message))

    def show_warning(self, title: str, message: str) -> None:
        """Capture warning dialog calls."""
        self.warning_calls.append((title, message))

    def show_error(self, title: str, message: str) -> None:
        """Capture error dialog calls."""
        self.error_calls.append((title, message))

    def prompt_append_record(self, record_name: str) -> bool:
        """Capture append prompts and return deterministic acceptance."""
        self.append_calls.append(record_name)
        return True

    def show_rename_dialog(
        self,
        attempted_filename: str,
        violation_info: dict[str, Any],
    ) -> dict[str, str] | None:
        """Capture rename prompts and return configured response."""
        self.rename_calls.append((attempted_filename, dict(violation_info)))
        return self.rename_result

    def show_done_dialog(
        self,
        session_details: SessionPromptDetails,
        on_done_callback: Callable[[], None],
    ) -> None:
        """Capture done prompts and execute callback immediately."""
        self.done_calls.append(session_details)
        on_done_callback()

    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> str:
        """Capture schedule requests and return synthetic handle."""
        self.scheduled_calls.append((interval_ms, callback))
        return "handle-1"

    def cancel_task(self, handle: Any) -> None:
        """Capture cancellation handles."""
        self.cancelled_handles.append(handle)


def test_ui_interaction_adapter_delegates_message_and_append_calls() -> None:
    """Forward message display and append prompts to the wrapped UI."""
    ui = _UiStub()
    adapter = UiInteractionAdapter(ui)

    adapter.show_info("Info", "ok")
    adapter.show_warning("Warn", "caution")
    adapter.show_error("Error", "boom")
    accepted = adapter.prompt_append_record("record-1")

    assert ui.info_calls == [("Info", "ok")]
    assert ui.warning_calls == [("Warn", "caution")]
    assert ui.error_calls == [("Error", "boom")]
    assert ui.append_calls == ["record-1"]
    assert accepted is True


def test_ui_interaction_adapter_request_rename_adds_contextual_reason() -> None:
    """Insert contextual reason at the front of analysis reasons list."""
    ui = _UiStub(rename_result={"sample": "renamed"})
    adapter = UiInteractionAdapter(ui)
    prompt = RenamePrompt(
        attempted_prefix="bad-prefix",
        analysis={"reasons": ["suffix invalid"], "other": "value"},
        contextual_reason="record exists",
    )

    decision = adapter.request_rename(prompt)

    assert decision.cancelled is False
    assert decision.values == {"sample": "renamed"}
    assert ui.rename_calls[0][0] == "bad-prefix"
    assert ui.rename_calls[0][1]["reasons"] == ["record exists", "suffix invalid"]
    assert prompt.analysis["reasons"] == ["suffix invalid"]


def test_ui_interaction_adapter_request_rename_returns_cancelled_when_ui_returns_none() -> (
    None
):
    """Return cancelled decision when rename UI reports cancellation."""
    ui = _UiStub(rename_result=None)
    adapter = UiInteractionAdapter(ui)
    prompt = RenamePrompt(attempted_prefix="bad", analysis={"reasons": []})

    decision = adapter.request_rename(prompt)

    assert decision.cancelled is True
    assert decision.values is None


def test_ui_interaction_adapter_show_done_prompt_delegates_callback() -> None:
    """Forward done-prompt details and execute provided callback via UI."""
    ui = _UiStub()
    adapter = UiInteractionAdapter(ui)
    details = SessionPromptDetails(users=("u1",), records=("r1",))
    callback_calls = 0

    def _on_done() -> None:
        nonlocal callback_calls
        callback_calls += 1

    adapter.show_done_prompt(details, _on_done)

    assert ui.done_calls == [details]
    assert callback_calls == 1


def test_ui_task_scheduler_delegates_schedule_and_cancel() -> None:
    """Route scheduling operations through the wrapped UI."""
    ui = _UiStub()
    scheduler = UiTaskScheduler(ui)

    def callback() -> None:
        return None

    handle = scheduler.schedule(250, callback)
    scheduler.cancel(handle)

    assert handle == "handle-1"
    assert ui.scheduled_calls[0][0] == 250
    assert ui.scheduled_calls[0][1] is callback
    assert ui.cancelled_handles == ["handle-1"]
