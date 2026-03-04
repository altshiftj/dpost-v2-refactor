"""Headless UI adapter for non-interactive runtime environments."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Mapping


class HeadlessUiError(RuntimeError):
    """Base error for headless UI adapter failures."""


class HeadlessUiPromptResolutionError(HeadlessUiError):
    """Raised when prompt cannot be resolved automatically."""


class HeadlessUiInputError(HeadlessUiError):
    """Raised when UI payload schema is malformed."""


class HeadlessUiSinkError(HeadlessUiError):
    """Raised when output sink cannot accept structured messages."""


class HeadlessUiLifecycleError(HeadlessUiError):
    """Raised on lifecycle misuse before init/after shutdown."""


class HeadlessUiAdapter:
    """Deterministic non-blocking UI adapter implementation."""

    def __init__(
        self,
        *,
        default_prompt_responses: Mapping[str, Mapping[str, Any]] | None = None,
        fail_on_prompt: bool = False,
        output_sink: Callable[[str], None] | None = None,
    ) -> None:
        self._defaults = {
            str(key).strip().lower(): dict(value)
            for key, value in dict(default_prompt_responses or {}).items()
            if isinstance(value, Mapping)
        }
        self._fail_on_prompt = bool(fail_on_prompt)
        self._sink = output_sink or (lambda _: None)
        self._initialized = False

    def initialize(self) -> None:
        """Initialize adapter lifecycle state."""
        self._initialized = True

    def notify(self, *, severity: str, title: str, message: str) -> None:
        """Emit a structured headless notification line."""
        self._require_initialized()
        self._write(
            {
                "kind": "notify",
                "severity": str(severity),
                "title": str(title),
                "message": str(message),
            }
        )

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Resolve prompt through deterministic default-response policy."""
        self._require_initialized()
        if not isinstance(payload, Mapping):
            raise HeadlessUiInputError("payload must be a mapping")

        normalized_prompt_type = str(prompt_type).strip().lower()
        if self._fail_on_prompt:
            raise HeadlessUiPromptResolutionError(
                f"headless prompt disallowed for type {normalized_prompt_type!r}"
            )

        response = dict(self._defaults.get(normalized_prompt_type, {}))
        if not response:
            response = {"action": "cancelled", "cancelled": True}
        response.setdefault("cancelled", response.get("action") == "cancelled")
        response["auto_response"] = True
        response["prompt_type"] = normalized_prompt_type

        self._write(
            {
                "kind": "prompt",
                "prompt_type": normalized_prompt_type,
                "payload": dict(payload),
                "response": dict(response),
            }
        )
        return response

    def show_status(self, *, message: str) -> None:
        """Emit a structured status line."""
        self._require_initialized()
        self._write({"kind": "status", "message": str(message)})

    def shutdown(self) -> None:
        """Shutdown lifecycle state."""
        self._initialized = False

    def healthcheck(self) -> Mapping[str, Any]:
        """Return lifecycle diagnostics."""
        return MappingProxyType({"ready": self._initialized, "adapter": "headless_ui"})

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise HeadlessUiLifecycleError("headless UI adapter is not initialized")

    def _write(self, payload: Mapping[str, Any]) -> None:
        try:
            self._sink(str(dict(payload)))
        except Exception as exc:  # noqa: BLE001
            raise HeadlessUiSinkError(str(exc)) from exc

