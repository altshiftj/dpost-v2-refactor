from __future__ import annotations

import pytest

from dpost_v2.application.ingestion.runtime_services import (
    RuntimeCallStatus,
    RuntimeServiceTimeoutError,
    RuntimeServices,
)


def test_runtime_services_propagates_correlation_to_adapters() -> None:
    captured: dict[str, object] = {}

    def move_to_target(source: str, target: str, correlation: dict[str, object]) -> str:
        captured.update(correlation)
        return target

    runtime = RuntimeServices(file_ops={"move_to_target": move_to_target})
    result = runtime.move_to_target(
        source="in.txt",
        target="out.txt",
        correlation={"event_id": "e1"},
    )

    assert result.status is RuntimeCallStatus.SUCCESS
    assert result.value == "out.txt"
    assert captured["event_id"] == "e1"


def test_runtime_services_returns_disabled_for_optional_capability() -> None:
    runtime = RuntimeServices(sync_port=None)

    result = runtime.trigger_sync(record_id="r1", correlation={"event_id": "e1"})

    assert result.status is RuntimeCallStatus.DISABLED


def test_runtime_services_normalizes_timeout_errors() -> None:
    def read_source(path: str, correlation: dict[str, object]) -> dict[str, object]:
        raise TimeoutError("slow")

    runtime = RuntimeServices(file_ops={"read_source": read_source})

    with pytest.raises(RuntimeServiceTimeoutError):
        runtime.read_source(path="in.txt", correlation={"event_id": "e1"})
