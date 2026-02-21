"""Unit coverage for JSON logging formatter and setup helper edge branches."""

from __future__ import annotations

import json
import logging

import dpost.infrastructure.logging as logging_module


def test_json_formatter_includes_optional_session_id() -> None:
    """Serialize session_id field when present on the log record."""
    formatter = logging_module.JSONFormatter()
    record = logging.LogRecord(
        name="unit.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.session_id = "session-123"

    payload = json.loads(formatter.format(record))

    assert payload["session_id"] == "session-123"
    assert payload["message"] == "hello world"


def test_setup_logger_ignores_console_handler_failures(monkeypatch) -> None:
    """Continue logger setup when stdout stream-handler creation raises."""
    logger_name = "unit.logging.setup.failure"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False

    class _DummyFileHandler(logging.Handler):
        """No-op handler replacing rotating file output in unit tests."""

        def emit(self, _record: logging.LogRecord) -> None:
            return None

    monkeypatch.setattr(
        logging_module,
        "RotatingFileHandler",
        lambda *_args, **_kwargs: _DummyFileHandler(),
    )
    monkeypatch.setattr(logging_module.sys, "stdout", object())
    monkeypatch.setattr(
        logging_module.logging,
        "StreamHandler",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("stream failed")),
    )

    configured = logging_module.setup_logger(logger_name)

    assert configured is logger
    assert len(configured.handlers) == 1
    configured.handlers.clear()
