"""Unit coverage for metrics collector reuse helper branches."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

import dpost.application.metrics as metrics


def test_counter_returns_existing_counter_instance(monkeypatch) -> None:
    """Reuse an existing counter collector when one is already registered."""
    existing = Counter(
        "unit_counter_existing_total",
        "doc",
        registry=CollectorRegistry(),
    )
    monkeypatch.setattr(metrics, "_existing_collector", lambda _name: existing)

    resolved = metrics._counter("unit_counter_existing", "doc")

    assert resolved is existing


def test_gauge_returns_existing_gauge_instance(monkeypatch) -> None:
    """Reuse an existing gauge collector when one is already registered."""
    existing = Gauge("unit_gauge_existing", "doc", registry=CollectorRegistry())
    monkeypatch.setattr(metrics, "_existing_collector", lambda _name: existing)

    resolved = metrics._gauge("unit_gauge_existing", "doc")

    assert resolved is existing


def test_histogram_returns_existing_histogram_instance(monkeypatch) -> None:
    """Reuse an existing histogram collector when one is already registered."""
    existing = Histogram(
        "unit_histogram_existing",
        "doc",
        registry=CollectorRegistry(),
    )
    monkeypatch.setattr(metrics, "_existing_collector", lambda _name: existing)

    resolved = metrics._histogram("unit_histogram_existing", "doc")

    assert resolved is existing
