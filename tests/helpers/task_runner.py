"""Test utilities for driving HeadlessUI scheduled callbacks."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.helpers.fake_ui import HeadlessUI


def drain_scheduled_tasks(ui: "HeadlessUI", max_steps: int = 50) -> int:
    """Run queued HeadlessUI scheduled callbacks up to ``max_steps`` iterations.

    Returns the number of scheduler batches that were executed to help tests
    assert progress when needed.
    """
    if getattr(ui, "use_virtual_time", False):
        return _drain_virtual_scheduled_tasks(ui, max_steps=max_steps)

    steps = 0
    while steps < max_steps and ui.scheduled_tasks:
        tasks = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, callback in tasks:
            callback()
        steps += 1
    return steps


def advance_scheduled_time(
    ui: "HeadlessUI",
    milliseconds: int,
    *,
    max_steps: int = 50,
) -> int:
    """Advance virtual scheduler time and run due callbacks.

    Falls back to ``drain_scheduled_tasks`` when the UI does not support virtual
    time semantics.
    """
    if not getattr(ui, "use_virtual_time", False):
        return drain_scheduled_tasks(ui, max_steps=max_steps)

    ui.advance_virtual_time(milliseconds)
    steps = 0
    while steps < max_steps:
        ran = ui.run_due_virtual_tasks()
        if ran == 0:
            break
        steps += 1
    return steps


def _drain_virtual_scheduled_tasks(ui: "HeadlessUI", max_steps: int) -> int:
    """Drain all virtual scheduled callbacks by advancing to each next due time."""
    steps = 0
    while steps < max_steps:
        ran_now = ui.run_due_virtual_tasks()
        if ran_now > 0:
            steps += 1
            continue
        next_due = ui.next_virtual_due_time_ms()
        if next_due is None:
            break
        ui.advance_virtual_time(next_due - ui.virtual_time_ms)
        steps += 1
    return steps
