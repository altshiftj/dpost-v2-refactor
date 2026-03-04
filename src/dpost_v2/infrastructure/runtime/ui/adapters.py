"""UI adapter shim wrappers implementing normalized UiPort semantics."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


class UiAdapterError(RuntimeError):
    """Base class for UI shim adapter failures."""


class UiAdapterContractError(UiAdapterError):
    """Raised when wrapped backend misses required UI contract methods."""


class UiAdapterInputError(UiAdapterError):
    """Raised when incoming UI payload is malformed."""


class UiAdapterRuntimeError(UiAdapterError):
    """Raised when backend adapter fails at runtime."""


class UiAdapterCapabilityError(UiAdapterError):
    """Raised when prompt type is not supported by wrapped backend."""


class UiAdapterShim:
    """Wrapper that normalizes backend behavior to UiPort semantics."""

    _REQUIRED_METHODS = ("initialize", "notify", "prompt", "show_status", "shutdown")

    def __init__(
        self,
        backend: object,
        *,
        supported_prompt_types: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._backend = backend
        self._supported_prompt_types = (
            {token.strip().lower() for token in supported_prompt_types}
            if supported_prompt_types is not None
            else None
        )
        self._validate_contract()

    def supports(self, prompt_type: str) -> bool:
        """Return whether prompt type is supported by this shim instance."""
        if self._supported_prompt_types is None:
            return True
        return str(prompt_type).strip().lower() in self._supported_prompt_types

    def initialize(self) -> None:
        """Initialize wrapped backend."""
        self._call_backend("initialize")

    def notify(self, *, severity: str, title: str, message: str) -> None:
        """Forward notification call to backend."""
        self._call_backend(
            "notify",
            severity=str(severity),
            title=str(title),
            message=str(message),
        )

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Forward prompt request with capability and payload normalization."""
        normalized_prompt_type = str(prompt_type).strip().lower()
        if not self.supports(normalized_prompt_type):
            raise UiAdapterCapabilityError(
                f"prompt type not supported: {normalized_prompt_type!r}"
            )
        if not isinstance(payload, Mapping):
            raise UiAdapterInputError("payload must be a mapping")
        result = self._call_backend(
            "prompt",
            prompt_type=normalized_prompt_type,
            payload=dict(payload),
        )
        if not isinstance(result, MutableMapping):
            raise UiAdapterInputError("prompt result must be a mapping")
        return dict(result)

    def show_status(self, *, message: str) -> None:
        """Forward status update request."""
        self._call_backend("show_status", message=str(message))

    def shutdown(self) -> None:
        """Shutdown wrapped backend."""
        self._call_backend("shutdown")

    def _validate_contract(self) -> None:
        for method_name in self._REQUIRED_METHODS:
            candidate = getattr(self._backend, method_name, None)
            if not callable(candidate):
                raise UiAdapterContractError(
                    f"backend missing required method {method_name!r}"
                )

    def _call_backend(self, method_name: str, **kwargs: Any) -> Any:
        method = getattr(self._backend, method_name)
        try:
            return method(**kwargs)
        except UiAdapterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise UiAdapterRuntimeError(str(exc)) from exc
