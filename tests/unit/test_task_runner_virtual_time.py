"""Unit tests for virtual-time scheduling helpers used by integration suites."""

from __future__ import annotations

from tests.helpers.fake_ui import HeadlessUI
from tests.helpers.task_runner import advance_scheduled_time, drain_scheduled_tasks


def test_advance_scheduled_time_respects_virtual_delays_and_cancellations() -> None:
    """Only due tasks should run, and cancelled handles should be skipped."""
    ui = HeadlessUI(use_virtual_time=True)
    calls: list[str] = []

    first = ui.schedule_task(100, lambda: calls.append("first"))
    second = ui.schedule_task(200, lambda: calls.append("second"))
    ui.cancel_task(second)

    assert first == 1
    assert second == 2
    assert advance_scheduled_time(ui, 99) == 0
    assert calls == []

    assert advance_scheduled_time(ui, 1) == 0
    assert calls == ["first"]

    assert advance_scheduled_time(ui, 100) == 0
    assert calls == ["first"]


def test_drain_scheduled_tasks_advances_virtual_time_to_future_callbacks() -> None:
    """Virtual drain should advance to each next due callback until idle."""
    ui = HeadlessUI(use_virtual_time=True)
    calls: list[str] = []

    ui.schedule_task(250, lambda: calls.append("a"))
    ui.schedule_task(500, lambda: calls.append("b"))

    steps = drain_scheduled_tasks(ui, max_steps=10)

    assert calls == ["a", "b"]
    assert ui.virtual_time_ms == 500
    assert steps >= 2

