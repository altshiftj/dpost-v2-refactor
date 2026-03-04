from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpost_v2.infrastructure.runtime.ui.headless import (
    HeadlessUiAdapter,
    HeadlessUiLifecycleError,
    HeadlessUiPromptResolutionError,
    HeadlessUiSinkError,
)


@dataclass
class _MemorySink:
    entries: list[str]

    def __call__(self, line: str) -> None:
        self.entries.append(line)


def test_headless_adapter_emits_notifications_and_status_to_sink() -> None:
    sink = _MemorySink(entries=[])
    adapter = HeadlessUiAdapter(output_sink=sink)
    adapter.initialize()

    adapter.notify(severity="info", title="t", message="m")
    adapter.show_status(message="running")

    assert any("notify" in entry for entry in sink.entries)
    assert any("status" in entry for entry in sink.entries)


def test_headless_prompt_uses_configured_default_response() -> None:
    adapter = HeadlessUiAdapter(
        default_prompt_responses={"confirm": {"accepted": True}}
    )
    adapter.initialize()

    response = adapter.prompt(prompt_type="confirm", payload={"question": "ok?"})

    assert response["accepted"] is True
    assert response["auto_response"] is True


def test_headless_prompt_can_fail_when_interaction_is_disallowed() -> None:
    adapter = HeadlessUiAdapter(fail_on_prompt=True)
    adapter.initialize()

    with pytest.raises(HeadlessUiPromptResolutionError):
        adapter.prompt(prompt_type="confirm", payload={"question": "ok?"})


def test_headless_adapter_enforces_lifecycle() -> None:
    adapter = HeadlessUiAdapter()

    with pytest.raises(HeadlessUiLifecycleError):
        adapter.show_status(message="nope")


def test_headless_adapter_maps_sink_failures() -> None:
    def _sink(_: str) -> None:
        raise RuntimeError("sink down")

    adapter = HeadlessUiAdapter(output_sink=_sink)
    adapter.initialize()

    with pytest.raises(HeadlessUiSinkError):
        adapter.notify(severity="warning", title="x", message="y")
