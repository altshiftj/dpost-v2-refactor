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
    steps = 0
    while steps < max_steps and ui.scheduled_tasks:
        tasks = list(ui.scheduled_tasks)
        ui.scheduled_tasks.clear()
        for _, callback in tasks:
            callback()
        steps += 1
    return steps
