"""Metrics adapter with validation, cardinality guards, and snapshots."""

from __future__ import annotations

import math
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping

_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_.]*$")

MetricsBackend = Callable[..., None]


class MetricsError(RuntimeError):
    """Base exception for metrics adapter failures."""


class MetricsValidationError(MetricsError):
    """Raised when metric request shape is invalid."""


class MetricsCardinalityError(MetricsError):
    """Raised when tag cardinality exceeds configured bounds."""


class MetricsBackendError(MetricsError):
    """Raised when metrics backend call fails."""


class MetricsValueError(MetricsError):
    """Raised when metric value cannot be represented as float."""


class MetricsAdapter:
    """Simple metrics emitter with stable naming and error containment."""

    def __init__(
        self,
        *,
        namespace: str,
        backend: MetricsBackend | None = None,
        enabled: bool = True,
        max_tags: int = 8,
    ) -> None:
        self._namespace = self._normalize_name(namespace, field_name="namespace")
        self._backend = backend
        self._enabled = bool(enabled)
        self._max_tags = int(max_tags)
        self._counts = {"emitted": 0, "dropped": 0, "backend_error": 0}

    def emit_counter(
        self,
        name: str,
        *,
        value: int | float,
        tags: Mapping[str, str],
    ) -> Mapping[str, Any]:
        """Emit counter metric request."""
        return self._emit(kind="counter", name=name, value=value, tags=tags)

    def emit_timer(
        self,
        name: str,
        *,
        value: int | float,
        tags: Mapping[str, str],
    ) -> Mapping[str, Any]:
        """Emit timer metric request."""
        return self._emit(kind="timer", name=name, value=value, tags=tags)

    def emit_gauge(
        self,
        name: str,
        *,
        value: int | float,
        tags: Mapping[str, str],
    ) -> Mapping[str, Any]:
        """Emit gauge metric request."""
        return self._emit(kind="gauge", name=name, value=value, tags=tags)

    def snapshot(self) -> Mapping[str, int]:
        """Return immutable count snapshot of adapter outcomes."""
        return MappingProxyType(dict(self._counts))

    def _emit(
        self,
        *,
        kind: str,
        name: str,
        value: int | float,
        tags: Mapping[str, str],
    ) -> Mapping[str, Any]:
        metric_name = self._normalize_name(name, field_name="name")
        metric_value = self._normalize_value(value)
        normalized_tags = self._normalize_tags(tags)
        if len(normalized_tags) > self._max_tags:
            self._counts["dropped"] += 1
            return MappingProxyType(
                {
                    "status": "dropped",
                    "reason": "cardinality",
                    "name": metric_name,
                }
            )

        if not self._enabled or self._backend is None:
            self._counts["dropped"] += 1
            return MappingProxyType({"status": "dropped", "reason": "disabled"})

        fully_qualified_name = f"{self._namespace}.{metric_name}"
        try:
            self._backend(
                name=fully_qualified_name,
                kind=kind,
                value=metric_value,
                tags=normalized_tags,
            )
        except Exception as exc:  # noqa: BLE001
            self._counts["backend_error"] += 1
            return MappingProxyType({"status": "backend_error", "error": str(exc)})

        self._counts["emitted"] += 1
        return MappingProxyType({"status": "emitted"})

    @staticmethod
    def _normalize_name(value: str, *, field_name: str) -> str:
        if not isinstance(value, str):
            raise MetricsValidationError(f"{field_name} must be string")
        normalized = value.strip().lower()
        if not _NAME_PATTERN.fullmatch(normalized):
            raise MetricsValidationError(f"invalid metric {field_name}: {value!r}")
        return normalized

    @staticmethod
    def _normalize_value(value: int | float) -> float:
        try:
            normalized = float(value)
        except Exception as exc:  # noqa: BLE001
            raise MetricsValueError(f"invalid metric value: {value!r}") from exc
        if not math.isfinite(normalized):
            raise MetricsValueError(f"metric value must be finite: {value!r}")
        return normalized

    @staticmethod
    def _normalize_tags(tags: Mapping[str, str]) -> dict[str, str]:
        if not isinstance(tags, Mapping):
            raise MetricsValidationError("tags must be a mapping")
        normalized = {str(key): str(value) for key, value in tags.items()}
        return {key: normalized[key] for key in sorted(normalized)}
