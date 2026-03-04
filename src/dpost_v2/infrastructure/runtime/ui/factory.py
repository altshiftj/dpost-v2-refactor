"""Factory for selecting and initializing concrete UiPort adapters."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dpost_v2.application.contracts.ports import UiPort
from dpost_v2.infrastructure.runtime.ui.desktop import DesktopUiAdapter
from dpost_v2.infrastructure.runtime.ui.dialogs import dispatch_dialog
from dpost_v2.infrastructure.runtime.ui.headless import HeadlessUiAdapter
from dpost_v2.infrastructure.runtime.ui.tkinter import TkinterUiAdapter

UiConstructor = Callable[[], object]


class UiFactoryError(RuntimeError):
    """Base error for UI adapter selection failures."""


class UiFactoryModeError(UiFactoryError):
    """Raised when runtime requests unknown UI mode token."""


class UiFactoryBackendUnavailableError(UiFactoryError):
    """Raised when requested backend is unavailable for current environment."""


class UiFactoryInitializationError(UiFactoryError):
    """Raised when selected adapter fails during initialization."""


class UiFactoryContractError(UiFactoryError):
    """Raised when selected adapter does not satisfy UiPort contract."""


@dataclass(frozen=True, slots=True)
class UiSelection:
    """Result envelope for resolved UI adapter and diagnostics."""

    adapter: UiPort
    descriptor: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "descriptor", MappingProxyType(dict(self.descriptor)))


def build_ui_adapter(
    *,
    mode: str,
    backend_preference: str | None = None,
    constructors: Mapping[str, UiConstructor] | None = None,
    probes: Mapping[str, Callable[[], bool]] | None = None,
) -> UiSelection:
    """Select, validate, and initialize a concrete UI adapter instance."""
    normalized_mode = str(mode).strip().lower()
    if normalized_mode not in {"headless", "desktop"}:
        raise UiFactoryModeError(f"unknown ui mode: {mode!r}")

    probe_map = _build_probe_map(probes)
    selected_backend = (backend_preference or normalized_mode).strip().lower()

    constructor_map = {
        "headless": lambda: HeadlessUiAdapter(),
        "desktop": _default_desktop_constructor,
    }
    constructor_map.update(dict(constructors or {}))

    if normalized_mode == "desktop":
        display_available = probe_map["display_available"]()
        tkinter_available = probe_map["tkinter_available"]()
        if not display_available or not tkinter_available:
            raise UiFactoryBackendUnavailableError(
                "desktop ui backend is unavailable for current environment"
            )

    constructor = constructor_map.get(selected_backend)
    if constructor is None:
        raise UiFactoryBackendUnavailableError(
            f"no constructor registered for ui backend {selected_backend!r}"
        )

    try:
        adapter = constructor()
    except Exception as exc:  # noqa: BLE001
        raise UiFactoryInitializationError(str(exc)) from exc

    if not isinstance(adapter, UiPort):
        raise UiFactoryContractError("constructed adapter does not satisfy UiPort")

    try:
        adapter.initialize()
    except Exception as exc:  # noqa: BLE001
        raise UiFactoryInitializationError(str(exc)) from exc

    return UiSelection(
        adapter=adapter,
        descriptor={
            "mode": normalized_mode,
            "backend": selected_backend,
            "display_available": probe_map["display_available"](),
            "tkinter_available": probe_map["tkinter_available"](),
        },
    )


def _default_desktop_constructor() -> object:
    backend = TkinterUiAdapter(backend=None)
    return DesktopUiAdapter(backend=backend, dialog_dispatch=dispatch_dialog)


def _build_probe_map(
    probes: Mapping[str, Callable[[], bool]] | None,
) -> dict[str, Callable[[], bool]]:
    defaults = {
        "display_available": _probe_display_available,
        "tkinter_available": _probe_tkinter_available,
    }
    defaults.update(dict(probes or {}))
    return defaults


def _probe_display_available() -> bool:
    import os

    return bool(os.environ.get("DISPLAY") or os.name == "nt")


def _probe_tkinter_available() -> bool:
    try:
        import tkinter  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False

