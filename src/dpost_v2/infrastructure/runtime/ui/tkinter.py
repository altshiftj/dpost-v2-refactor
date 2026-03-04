"""Tkinter-backed UI adapter wrapper with thread-safety guards."""

from __future__ import annotations

import threading
from typing import Any, Mapping


class TkinterUiError(RuntimeError):
    """Base tkinter adapter failure."""


class TkinterUiUnavailableError(TkinterUiError):
    """Raised when tkinter backend is unavailable in current environment."""


class TkinterUiThreadError(TkinterUiError):
    """Raised when UI operation executes off designated UI thread."""


class TkinterUiRenderError(TkinterUiError):
    """Raised when backend rendering/prompt dispatch fails."""


class TkinterUiAdapter:
    """Thin wrapper around tkinter-compatible backend implementation."""

    def __init__(
        self,
        *,
        backend: object | None,
        ui_thread_id: int | None = None,
    ) -> None:
        self._backend = backend
        self._ui_thread_id = ui_thread_id
        self._initialized = False

    def initialize(self) -> None:
        """Initialize tkinter backend and bind UI-thread identity."""
        if self._backend is None:
            raise TkinterUiUnavailableError("tkinter backend is unavailable")
        if self._ui_thread_id is None:
            self._ui_thread_id = threading.get_ident()
        self._initialized = True
        self._call_backend("initialize")

    def notify(self, *, severity: str, title: str, message: str) -> None:
        """Forward notification rendering to backend."""
        self._require_initialized()
        self._assert_ui_thread()
        self._call_backend(
            "notify",
            severity=str(severity),
            title=str(title),
            message=str(message),
        )

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Render prompt and normalize cancel path to explicit result payload."""
        self._require_initialized()
        self._assert_ui_thread()
        if not isinstance(payload, Mapping):
            raise TkinterUiRenderError("payload must be a mapping")
        response = self._call_backend(
            "prompt",
            prompt_type=str(prompt_type),
            payload=dict(payload),
        )
        if response is None:
            return {"action": "cancelled", "cancelled": True, "values": {}}
        if not isinstance(response, Mapping):
            raise TkinterUiRenderError("prompt response must be mapping or None")
        return dict(response)

    def show_status(self, *, message: str) -> None:
        """Forward status update rendering to backend."""
        self._require_initialized()
        self._assert_ui_thread()
        self._call_backend("show_status", message=str(message))

    def shutdown(self) -> None:
        """Shutdown backend resources."""
        if not self._initialized:
            return
        self._call_backend("shutdown")
        self._initialized = False

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise TkinterUiUnavailableError("tkinter adapter is not initialized")

    def _assert_ui_thread(self) -> None:
        if self._ui_thread_id is None:
            raise TkinterUiThreadError("ui thread id is undefined")
        current_thread = threading.get_ident()
        if current_thread != self._ui_thread_id:
            raise TkinterUiThreadError(
                f"ui call on wrong thread: expected {self._ui_thread_id}, got {current_thread}"
            )

    def _call_backend(self, method_name: str, **kwargs: Any) -> Any:
        if self._backend is None:
            raise TkinterUiUnavailableError("tkinter backend is unavailable")
        method = getattr(self._backend, method_name, None)
        if not callable(method):
            raise TkinterUiUnavailableError(
                f"backend missing required method {method_name!r}"
            )
        try:
            return method(**kwargs)
        except TkinterUiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise TkinterUiRenderError(str(exc)) from exc

