from __future__ import annotations

from typing import Any

import pytest

from dpost_v2.infrastructure.observability.logging import (
    LoggingConfigError,
    StructuredLoggingConfig,
    build_structured_logger,
)


def test_logger_validates_log_level() -> None:
    with pytest.raises(LoggingConfigError):
        build_structured_logger(StructuredLoggingConfig(level="verbose"))


def test_logger_redacts_sensitive_fields_and_keeps_stable_schema() -> None:
    entries: list[dict[str, Any]] = []
    logger = build_structured_logger(
        StructuredLoggingConfig(
            level="info",
            redacted_fields={"password", "token"},
            runtime_metadata={"service": "dpost"},
        ),
        sink=lambda entry: entries.append(entry),
    )

    result = logger.emit(
        level="info",
        message="sync",
        payload={"password": "secret", "count": 2},
        correlation={"trace_id": "t-1", "event_id": "e-1"},
    )

    assert result["status"] == "emitted"
    entry = entries[0]
    assert set(entry) == {
        "timestamp",
        "level",
        "message",
        "payload",
        "correlation",
        "runtime",
    }
    assert entry["payload"]["password"] == "***REDACTED***"
    assert entry["payload"]["count"] == 2


def test_logger_contains_sink_errors_without_raising() -> None:
    logger = build_structured_logger(
        StructuredLoggingConfig(level="info"),
        sink=lambda entry: (_ for _ in ()).throw(RuntimeError("sink down")),
    )

    result = logger.emit(level="info", message="hello", payload={}, correlation={})

    assert result["status"] == "sink_error"
    assert "sink down" in result["error"]


def test_logger_builder_is_idempotent_for_same_config_object() -> None:
    config = StructuredLoggingConfig(level="info")
    first = build_structured_logger(config)
    second = build_structured_logger(config)

    assert first is second
