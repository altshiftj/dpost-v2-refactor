"""Structured logging adapter with redaction and sink-failure containment."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Callable, Mapping

_VALID_LEVELS = frozenset({"debug", "info", "warning", "error"})
_LOGGER_CACHE: dict[int, "StructuredLogger"] = {}


class LoggingError(RuntimeError):
    """Base exception for logging adapter failures."""


class LoggingConfigError(LoggingError):
    """Raised when logger configuration is malformed."""


class LoggingSinkInitError(LoggingError):
    """Raised when logger sink setup fails."""


class LoggingSerializationError(LoggingError):
    """Raised when payload cannot be serialized safely."""


class LoggingSinkWriteError(LoggingError):
    """Raised when sink write fails at runtime."""


@dataclass(frozen=True, slots=True)
class StructuredLoggingConfig:
    """Configuration for structured logging adapter."""

    level: str = "info"
    redacted_fields: set[str] = field(default_factory=set)
    runtime_metadata: Mapping[str, Any] = field(default_factory=dict)

    def normalized_level(self) -> str:
        """Return normalized lowercase log level token."""
        return self.level.strip().lower()


class StructuredLogger:
    """Structured logger that emits normalized payload dictionaries."""

    def __init__(
        self,
        *,
        config: StructuredLoggingConfig,
        sink: Callable[[dict[str, Any]], None],
    ) -> None:
        self._config = config
        self._sink = sink

    def emit(
        self,
        *,
        level: str,
        message: str,
        payload: Mapping[str, Any],
        correlation: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Emit one structured log entry and return status diagnostics."""
        normalized_level = str(level).strip().lower()
        if normalized_level not in _VALID_LEVELS:
            raise LoggingConfigError(f"invalid log level: {level!r}")

        entry = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": normalized_level,
            "message": str(message),
            "payload": self._redact_mapping(payload),
            "correlation": self._normalize_mapping(correlation),
            "runtime": self._normalize_mapping(self._config.runtime_metadata),
        }
        try:
            self._sink(entry)
        except Exception as exc:  # noqa: BLE001
            return MappingProxyType({"status": "sink_error", "error": str(exc)})
        return MappingProxyType({"status": "emitted"})

    def _redact_mapping(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_mapping(payload)
        redacted_fields = {
            name.strip().lower() for name in self._config.redacted_fields
        }
        redacted: dict[str, Any] = {}
        for key, value in normalized.items():
            if key.lower() in redacted_fields:
                redacted[key] = "***REDACTED***"
            elif isinstance(value, Mapping):
                redacted[key] = self._redact_mapping(value)
            else:
                redacted[key] = value
        return redacted

    def _normalize_mapping(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise LoggingSerializationError("payload must be a mapping")
        return {str(key): _normalize_primitive(value) for key, value in payload.items()}


def build_structured_logger(
    config: StructuredLoggingConfig,
    *,
    sink: Callable[[dict[str, Any]], None] | None = None,
) -> StructuredLogger:
    """Build a configured logger instance with cache keyed by config identity."""
    if not isinstance(config, StructuredLoggingConfig):
        raise LoggingConfigError("config must be StructuredLoggingConfig")
    level = config.normalized_level()
    if level not in _VALID_LEVELS:
        raise LoggingConfigError(f"invalid log level: {config.level!r}")

    cache_key = id(config)
    if sink is None and cache_key in _LOGGER_CACHE:
        return _LOGGER_CACHE[cache_key]

    logger = StructuredLogger(config=config, sink=sink or (lambda entry: None))
    if sink is None:
        _LOGGER_CACHE[cache_key] = logger
    return logger


def _normalize_primitive(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalize_primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_primitive(item) for item in value]
    raise LoggingSerializationError(f"unsupported payload type: {type(value)!r}")
