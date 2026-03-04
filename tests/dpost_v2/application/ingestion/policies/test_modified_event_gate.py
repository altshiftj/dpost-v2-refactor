from __future__ import annotations

import pytest

from dpost_v2.application.ingestion.policies.modified_event_gate import (
    ModifiedEventDecision,
    ModifiedEventGate,
    ModifiedEventGateConfig,
    ModifiedEventGateTimeError,
)


def test_modified_event_gate_drops_duplicates_inside_window() -> None:
    gate = ModifiedEventGate(ModifiedEventGateConfig(window_seconds=5.0))

    first = gate.evaluate(event_key="k1", event_timestamp=100.0)
    second = gate.evaluate(event_key="k1", event_timestamp=103.0)
    third = gate.evaluate(event_key="k1", event_timestamp=106.0)

    assert first.decision is ModifiedEventDecision.ALLOW
    assert second.decision is ModifiedEventDecision.DROP_DUPLICATE
    assert third.decision is ModifiedEventDecision.ALLOW


def test_modified_event_gate_raises_on_time_regression() -> None:
    gate = ModifiedEventGate(ModifiedEventGateConfig(window_seconds=5.0))
    gate.evaluate(event_key="k1", event_timestamp=100.0)

    with pytest.raises(ModifiedEventGateTimeError):
        gate.evaluate(event_key="k1", event_timestamp=99.0)
