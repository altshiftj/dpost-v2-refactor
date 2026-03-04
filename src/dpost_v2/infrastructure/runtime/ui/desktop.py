"""Desktop UI orchestration adapter bridging dialogs and UI backend calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


class DesktopUiError(RuntimeError):
    """Base desktop UI adapter error."""


class DesktopUiPayloadError(DesktopUiError):
    """Raised when desktop prompt payload is malformed."""


class DesktopUiAdapterError(DesktopUiError):
    """Raised for dialog/backend adapter failures."""


class DesktopUiStateError(DesktopUiError):
    """Raised when view model state cannot be updated safely."""


class DesktopUiCallbackError(DesktopUiError):
    """Raised when on_user_action callback fails."""


@dataclass(frozen=True, slots=True)
class DesktopViewModel:
    """Minimal view-model snapshot maintained by desktop adapter."""

    last_status: str | None = None
    notification_count: int = 0
    prompt_count: int = 0


class DesktopUiAdapter:
    """Desktop UI adapter coordinating backend and dialog helper pipeline."""

    def __init__(
        self,
        *,
        backend: object,
        dialog_dispatch: Callable[..., Mapping[str, Any]],
        on_user_action: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self._backend = backend
        self._dialog_dispatch = dialog_dispatch
        self._on_user_action = on_user_action
        self.view_model = DesktopViewModel()

    def initialize(self) -> None:
        """Initialize desktop backend dependencies."""
        try:
            self._backend.initialize()
        except Exception as exc:  # noqa: BLE001
            raise DesktopUiAdapterError(str(exc)) from exc

    def notify(self, *, severity: str, title: str, message: str) -> None:
        """Forward notifications and update view model counters."""
        try:
            self._backend.notify(severity=severity, title=title, message=message)
            self.view_model = DesktopViewModel(
                last_status=self.view_model.last_status,
                notification_count=self.view_model.notification_count + 1,
                prompt_count=self.view_model.prompt_count,
            )
        except Exception as exc:  # noqa: BLE001
            raise DesktopUiAdapterError(str(exc)) from exc

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch prompt through dialog helper and optional callback."""
        if not isinstance(payload, Mapping):
            raise DesktopUiPayloadError("payload must be a mapping")

        try:
            result = self._dialog_dispatch(
                prompt_type=prompt_type,
                payload=dict(payload),
                backend_prompt=self._dispatch_backend_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            raise DesktopUiAdapterError(str(exc)) from exc

        if not isinstance(result, Mapping):
            raise DesktopUiStateError("dialog dispatch result must be a mapping")

        self.view_model = DesktopViewModel(
            last_status=self.view_model.last_status,
            notification_count=self.view_model.notification_count,
            prompt_count=self.view_model.prompt_count + 1,
        )

        if self._on_user_action is not None:
            try:
                self._on_user_action(result)
            except Exception as exc:  # noqa: BLE001
                raise DesktopUiCallbackError(str(exc)) from exc

        return dict(result)

    def _dispatch_backend_prompt(
        self, request: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        if not isinstance(request, Mapping):
            raise DesktopUiPayloadError("dialog request must be a mapping")
        backend_prompt_type = request.get("prompt_type")
        if not isinstance(backend_prompt_type, str) or not backend_prompt_type.strip():
            raise DesktopUiPayloadError("dialog request prompt_type must be non-empty")
        backend_payload = request.get("payload", {})
        if not isinstance(backend_payload, Mapping):
            raise DesktopUiPayloadError("dialog request payload must be a mapping")
        return self._backend.prompt(
            prompt_type=backend_prompt_type,
            payload=dict(backend_payload),
        )

    def show_status(self, *, message: str) -> None:
        """Forward status update and store latest message."""
        try:
            self._backend.show_status(message=message)
            self.view_model = DesktopViewModel(
                last_status=message,
                notification_count=self.view_model.notification_count,
                prompt_count=self.view_model.prompt_count,
            )
        except Exception as exc:  # noqa: BLE001
            raise DesktopUiAdapterError(str(exc)) from exc

    def shutdown(self) -> None:
        """Shutdown backend resources."""
        try:
            self._backend.shutdown()
        except Exception as exc:  # noqa: BLE001
            raise DesktopUiAdapterError(str(exc)) from exc
