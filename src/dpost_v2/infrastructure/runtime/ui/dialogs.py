"""Backend-agnostic dialog helper utilities for UI prompt composition."""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Mapping

SUPPORTED_PROMPT_TYPES = frozenset({"confirm", "rename", "choice"})


class DialogError(RuntimeError):
    """Base dialog helper error."""


class DialogSpecValidationError(DialogError):
    """Raised when prompt specification payload is malformed."""


class DialogTypeError(DialogError):
    """Raised when prompt type token is unsupported."""


class DialogBackendError(DialogError):
    """Raised when backend dispatch fails."""


class DialogLifecycleError(DialogError):
    """Raised when backend result cannot be normalized."""


def dispatch_dialog(
    *,
    prompt_type: str,
    payload: Mapping[str, Any],
    backend_prompt: Callable[[dict[str, Any]], Mapping[str, Any] | None],
    prompt_id_factory: Callable[[], str] | None = None,
    monotonic_ns: Callable[[], int] | None = None,
) -> dict[str, Any]:
    """Validate/dispatch one prompt request and normalize backend response."""
    normalized_prompt_type = _normalize_prompt_type(prompt_type)
    normalized_payload = _normalize_payload(payload)
    id_factory = prompt_id_factory or (lambda: str(uuid.uuid4()))
    clock = monotonic_ns or time.monotonic_ns
    prompt_id = id_factory()

    request = {
        "prompt_id": prompt_id,
        "prompt_type": normalized_prompt_type,
        "payload": normalized_payload,
    }
    started = clock()
    try:
        backend_result = backend_prompt(request)
    except Exception as exc:  # noqa: BLE001
        raise DialogBackendError(str(exc)) from exc
    latency_ms = max(0.0, (clock() - started) / 1_000_000)

    if backend_result is None:
        return {
            "prompt_id": prompt_id,
            "action": "cancelled",
            "cancelled": True,
            "values": {},
            "latency_ms": latency_ms,
        }

    if not isinstance(backend_result, Mapping):
        raise DialogLifecycleError("backend dialog result must be mapping or None")

    action = backend_result.get("action")
    if not isinstance(action, str) or not action.strip():
        action = "accepted"
    values = backend_result.get("values")
    if values is None:
        values = {
            key: value
            for key, value in backend_result.items()
            if key not in {"action", "cancelled", "latency_ms"}
        }
    if not isinstance(values, Mapping):
        raise DialogLifecycleError("backend dialog values must be mapping")

    cancelled = bool(backend_result.get("cancelled", action == "cancelled"))
    return {
        "prompt_id": prompt_id,
        "action": action,
        "cancelled": cancelled,
        "values": dict(values),
        "latency_ms": latency_ms,
    }


def _normalize_prompt_type(prompt_type: str) -> str:
    if not isinstance(prompt_type, str) or not prompt_type.strip():
        raise DialogTypeError("prompt_type must be non-empty")
    normalized = prompt_type.strip().lower()
    if normalized not in SUPPORTED_PROMPT_TYPES:
        raise DialogTypeError(f"unsupported prompt type: {prompt_type!r}")
    return normalized


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise DialogSpecValidationError("payload must be a mapping")
    return dict(payload)

