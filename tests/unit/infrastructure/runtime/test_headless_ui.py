"""Unit coverage for headless runtime UI event-loop behavior."""

from __future__ import annotations

import threading

import pytest

from dpost.application.ports import SessionPromptDetails
from dpost.infrastructure.runtime_adapters.headless_ui import HeadlessRuntimeUI


def test_headless_ui_noninteractive_methods_return_expected_defaults() -> None:
    """Expose deterministic defaults for non-interactive dialog operations."""
    ui = HeadlessRuntimeUI()

    ui.initialize()
    ui.show_warning("w", "msg")
    ui.show_info("i", "msg")
    ui.show_error("e", "msg")

    assert ui.prompt_rename() is None
    assert ui.show_rename_dialog("name", {"reason": "bad"}) is None
    assert ui.prompt_append_record("record") is True
    assert ui.get_root() is None


def test_headless_ui_show_done_dialog_executes_callback_immediately() -> None:
    """Run done-callback immediately in headless mode."""
    ui = HeadlessRuntimeUI()
    callback_calls = 0

    def _callback() -> None:
        nonlocal callback_calls
        callback_calls += 1

    ui.show_done_dialog(SessionPromptDetails(), _callback)

    assert callback_calls == 1


def test_headless_ui_runs_scheduled_callback_and_stops_on_destroy() -> None:
    """Execute due callbacks in event loop and stop once destroyed."""
    ui = HeadlessRuntimeUI()
    callback_ran = threading.Event()

    def _callback() -> None:
        callback_ran.set()
        ui.destroy()

    ui.schedule_task(0, _callback)

    worker = threading.Thread(target=ui.run_main_loop)
    worker.start()
    worker.join(timeout=1.0)

    assert callback_ran.is_set()
    assert not worker.is_alive()


def test_headless_ui_waits_for_future_callbacks() -> None:
    """Wait for scheduled callbacks that are due in the future."""
    ui = HeadlessRuntimeUI()
    callback_ran = threading.Event()

    def _callback() -> None:
        callback_ran.set()
        ui.destroy()

    ui.schedule_task(50, _callback)

    worker = threading.Thread(target=ui.run_main_loop)
    worker.start()
    assert callback_ran.wait(timeout=1.0)
    worker.join(timeout=1.0)

    assert not worker.is_alive()


def test_headless_ui_cancel_task_skips_cancelled_callbacks() -> None:
    """Do not execute callbacks cancelled before they become due."""
    ui = HeadlessRuntimeUI()
    cancelled_ran = threading.Event()

    def _cancelled() -> None:
        cancelled_ran.set()

    handle = ui.schedule_task(0, _cancelled)
    ui.cancel_task(handle)
    ui.cancel_task("non-int-handle")
    ui.schedule_task(0, ui.destroy)

    worker = threading.Thread(target=ui.run_main_loop)
    worker.start()
    worker.join(timeout=1.0)

    assert not cancelled_ran.is_set()
    assert not worker.is_alive()


def test_headless_ui_routes_callback_exceptions_to_registered_handler() -> None:
    """Report callback errors through registered exception handler."""
    ui = HeadlessRuntimeUI()
    captured: list[tuple[type[BaseException], BaseException]] = []

    def _close_handler() -> None:
        return None

    def _exception_handler(
        exc_type: type[BaseException],
        exc: BaseException,
        _traceback: object,
    ) -> None:
        captured.append((exc_type, exc))

    def _explode() -> None:
        raise ValueError("boom")

    ui.set_close_handler(_close_handler)
    ui.set_exception_handler(_exception_handler)
    ui.schedule_task(0, _explode)
    ui.schedule_task(0, ui.destroy)

    worker = threading.Thread(target=ui.run_main_loop)
    worker.start()
    worker.join(timeout=1.0)

    assert captured
    assert captured[0][0] is ValueError
    assert str(captured[0][1]) == "boom"


def test_headless_ui_raises_when_no_exception_handler_is_registered() -> None:
    """Re-raise callback exceptions when no handler is configured."""
    ui = HeadlessRuntimeUI()

    def _explode() -> None:
        raise RuntimeError("unexpected")

    ui.schedule_task(0, _explode)

    with pytest.raises(RuntimeError, match="unexpected"):
        ui.run_main_loop()
