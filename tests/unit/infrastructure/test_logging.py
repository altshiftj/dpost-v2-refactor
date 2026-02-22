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


def test_parse_bool_env_supports_false_and_invalid_values() -> None:
    """Boolean env parsing should recognize false values and ignore invalid text."""

    assert logging_module._parse_bool_env("false") is False
    assert logging_module._parse_bool_env(" OFF ") is False
    assert logging_module._parse_bool_env("maybe") is None


def test_setup_logger_ignores_console_handler_failures(monkeypatch) -> None:
    """Continue logger setup when stdout stream-handler creation raises."""
    logger_name = "unit.logging.setup.failure"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False
    monkeypatch.setenv("DPOST_LOG_FILE_ENABLED", "1")

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


def test_setup_logger_disables_file_handler_by_default_under_pytest(monkeypatch) -> None:
    """Pytest runs should default to console-only logging unless explicitly enabled."""
    logger_name = "unit.logging.setup.pytest_default"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False
    monkeypatch.delenv("DPOST_LOG_FILE_ENABLED", raising=False)

    calls: list[str] = []

    def _unexpected_file_handler(*_args, **_kwargs):
        calls.append("file")
        return logging.NullHandler()

    monkeypatch.setattr(logging_module, "RotatingFileHandler", _unexpected_file_handler)

    configured = logging_module.setup_logger(logger_name)

    assert configured is logger
    assert calls == []
    assert len(configured.handlers) >= 1
    configured.handlers.clear()


def test_setup_logger_can_enable_file_handler_in_pytest_with_env(
    monkeypatch, tmp_path
) -> None:
    """An explicit env override should re-enable file logging during pytest."""
    logger_name = "unit.logging.setup.pytest_forced_file"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False
    monkeypatch.setenv("DPOST_LOG_FILE_ENABLED", "true")
    monkeypatch.setenv("DPOST_LOG_FILE_PATH", str(tmp_path / "logs" / "watchdog.log"))
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class _DummyFileHandler(logging.Handler):
        """No-op file handler test double used to observe attachment."""

        def emit(self, _record: logging.LogRecord) -> None:
            return None

    def _fake_rotating_file_handler(*args, **kwargs):
        calls.append((args, kwargs))
        return _DummyFileHandler()

    monkeypatch.setattr(logging_module, "RotatingFileHandler", _fake_rotating_file_handler)

    configured = logging_module.setup_logger(logger_name)

    assert configured is logger
    assert len(calls) == 1
    assert len(configured.handlers) >= 1
    configured.handlers.clear()


def test_setup_logger_ignores_file_handler_failures_and_keeps_console(
    monkeypatch,
) -> None:
    """File-handler errors should not prevent console logging from being attached."""
    logger_name = "unit.logging.setup.file_failure"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False
    monkeypatch.setenv("DPOST_LOG_FILE_ENABLED", "1")
    monkeypatch.setattr(
        logging_module,
        "RotatingFileHandler",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("denied")),
    )

    configured = logging_module.setup_logger(logger_name)

    assert configured is logger
    assert any(isinstance(handler, logging.StreamHandler) for handler in configured.handlers)
    configured.handlers.clear()


def test_setup_logger_falls_back_to_null_handler_when_all_handler_setup_fails(
    monkeypatch,
) -> None:
    """Attach a NullHandler when file and console handlers both fail."""
    logger_name = "unit.logging.setup.null_fallback"
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.propagate = False
    monkeypatch.setenv("DPOST_LOG_FILE_ENABLED", "1")
    monkeypatch.setattr(
        logging_module,
        "RotatingFileHandler",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("denied")),
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
    assert isinstance(configured.handlers[0], logging.NullHandler)
    configured.handlers.clear()
