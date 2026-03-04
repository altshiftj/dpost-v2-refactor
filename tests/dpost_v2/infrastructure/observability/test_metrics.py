from __future__ import annotations

from typing import Any

import pytest

from dpost_v2.infrastructure.observability.metrics import (
    MetricsAdapter,
    MetricsValidationError,
    MetricsValueError,
)


def test_metrics_emits_counter_with_namespaced_name_and_sorted_tags() -> None:
    calls: list[dict[str, Any]] = []

    def _backend(*, name: str, kind: str, value: float, tags: dict[str, str]) -> None:
        calls.append({"name": name, "kind": kind, "value": value, "tags": tags})

    metrics = MetricsAdapter(namespace="dpost", backend=_backend)

    result = metrics.emit_counter(
        "ingestion.success",
        value=1,
        tags={"profile": "qa", "mode": "headless"},
    )

    assert result["status"] == "emitted"
    assert calls == [
        {
            "name": "dpost.ingestion.success",
            "kind": "counter",
            "value": 1.0,
            "tags": {"mode": "headless", "profile": "qa"},
        }
    ]


def test_metrics_rejects_invalid_metric_name() -> None:
    metrics = MetricsAdapter(namespace="dpost")

    with pytest.raises(MetricsValidationError):
        metrics.emit_counter("invalid name", value=1, tags={})


def test_metrics_drops_high_cardinality_tags() -> None:
    calls: list[dict[str, Any]] = []

    metrics = MetricsAdapter(
        namespace="dpost",
        backend=lambda **kwargs: calls.append(kwargs),
        max_tags=1,
    )

    result = metrics.emit_counter(
        "ingestion.success", value=1, tags={"a": "1", "b": "2"}
    )

    assert result["status"] == "dropped"
    assert result["reason"] == "cardinality"
    assert calls == []


def test_metrics_contains_backend_errors_without_throwing() -> None:
    metrics = MetricsAdapter(
        namespace="dpost",
        backend=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("down")),
    )

    result = metrics.emit_counter("ingestion.success", value=1, tags={})

    assert result["status"] == "backend_error"
    assert "down" in result["error"]


def test_metrics_snapshot_tracks_outcomes() -> None:
    metrics = MetricsAdapter(
        namespace="dpost", backend=lambda **kwargs: None, max_tags=1
    )

    metrics.emit_counter("ingestion.success", value=1, tags={})
    metrics.emit_counter("ingestion.success", value=1, tags={"a": "1", "b": "2"})

    snapshot = metrics.snapshot()

    assert snapshot["emitted"] == 1
    assert snapshot["dropped"] == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_metrics_rejects_non_finite_values(value: float) -> None:
    metrics = MetricsAdapter(namespace="dpost")

    with pytest.raises(MetricsValueError):
        metrics.emit_counter("ingestion.success", value=value, tags={})
