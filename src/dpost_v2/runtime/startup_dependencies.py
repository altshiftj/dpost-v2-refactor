"""Runtime startup dependency resolver for deterministic bootstrap wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping

DependencyFactory = Callable[[], object]


class DependencyResolutionError(RuntimeError):
    """Raised when required dependency input is unavailable."""


class DependencyBackendSelectionError(DependencyResolutionError):
    """Raised when startup asks for an unknown backend token."""


class DependencyImportError(DependencyResolutionError):
    """Raised when optional backend imports are unavailable."""


class DependencyCompatibilityError(DependencyResolutionError):
    """Raised when selected backends are mode-incompatible."""


@dataclass(frozen=True)
class StartupDependencies:
    """Immutable startup dependency container used by composition."""

    factories: Mapping[str, DependencyFactory]
    selected_backends: Mapping[str, str]
    lazy_factories: frozenset[str] = field(default_factory=frozenset)
    warnings: tuple[str, ...] = ()
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    cleanup: Callable[[], None] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "factories", MappingProxyType(dict(self.factories)))
        object.__setattr__(
            self,
            "selected_backends",
            MappingProxyType(dict(self.selected_backends)),
        )
        object.__setattr__(self, "lazy_factories", frozenset(self.lazy_factories))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self, "diagnostics", MappingProxyType(dict(self.diagnostics))
        )


def resolve_startup_dependencies(
    *,
    settings: Mapping[str, Any] | Any,
    environment: Mapping[str, str] | None = None,
    overrides: Mapping[str, DependencyFactory] | None = None,
) -> StartupDependencies:
    """Resolve mode/profile dependency backend selections into factory bindings."""
    env = dict(environment or {})
    normalized_settings = _normalize_settings_payload(settings)
    selected_mode = _resolve_mode(normalized_settings)
    selected_backends = _resolve_backend_tokens(normalized_settings)
    _validate_mode_backend_compatibility(selected_mode, selected_backends)
    _validate_backend_requirements(selected_backends, env)

    factory_map: dict[str, DependencyFactory] = {
        "observability": _observability_factory_builder(
            selected_backends["observability"]
        ),
        "storage": _storage_factory_builder(selected_backends["storage"]),
        "clock": _clock_factory,
        "event_sink": _event_sink_factory,
        "filesystem": _filesystem_factory,
        "ui": _ui_factory_builder(selected_backends["ui"]),
        "sync": _sync_factory_builder(selected_backends["sync"]),
        "plugins": _plugins_factory_builder(selected_backends["plugins"]),
    }

    for binding_name, binding_factory in dict(overrides or {}).items():
        factory_map[binding_name] = binding_factory

    warnings: list[str] = []
    if selected_backends["sync"] == "noop":
        warnings.append("sync backend is noop; outbound sync is disabled")
    if selected_mode == "desktop" and not env.get("DISPLAY"):
        warnings.append("DISPLAY environment variable is not set for desktop mode")

    return StartupDependencies(
        factories=factory_map,
        selected_backends=selected_backends,
        lazy_factories=frozenset({"sync", "plugins"}),
        warnings=tuple(warnings),
        diagnostics={
            "mode": selected_mode,
            "profile": normalized_settings.get("profile"),
            "selected_backends": dict(selected_backends),
            "warnings": tuple(warnings),
        },
        cleanup=None,
    )


def _normalize_settings_payload(settings: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(settings, Mapping):
        return dict(settings)
    if hasattr(settings, "to_dependency_payload"):
        payload = settings.to_dependency_payload()
        if isinstance(payload, Mapping):
            return dict(payload)
    return {
        "mode": getattr(settings, "mode", "headless"),
        "profile": getattr(settings, "profile", None),
        "backends": {
            "ui": getattr(getattr(settings, "ui", None), "backend", "headless"),
            "sync": getattr(getattr(settings, "sync", None), "backend", "noop"),
            "plugins": "builtin",
            "observability": "structured",
            "storage": "filesystem",
        },
    }


def _resolve_mode(settings: Mapping[str, Any]) -> str:
    raw_mode = settings.get("mode", "headless")
    mode = str(raw_mode).strip().lower()
    if mode not in {"headless", "desktop"}:
        raise DependencyBackendSelectionError(
            f"Unknown runtime mode {raw_mode!r}. Supported modes: headless, desktop."
        )
    return mode


def _resolve_backend_tokens(settings: Mapping[str, Any]) -> dict[str, str]:
    raw_backends = settings.get("backends") or {}
    if not isinstance(raw_backends, Mapping):
        raise DependencyBackendSelectionError("Backends selection must be a mapping.")

    selected = {
        "ui": _normalize_backend_token(
            raw_backends.get("ui", "headless"),
            family="ui",
            allowed={"headless", "desktop"},
        ),
        "sync": _normalize_backend_token(
            raw_backends.get("sync", "noop"),
            family="sync",
            allowed={"noop", "kadi"},
        ),
        "plugins": _normalize_backend_token(
            raw_backends.get("plugins", "builtin"),
            family="plugins",
            allowed={"builtin"},
        ),
        "observability": _normalize_backend_token(
            raw_backends.get("observability", "structured"),
            family="observability",
            allowed={"structured"},
        ),
        "storage": _normalize_backend_token(
            raw_backends.get("storage", "filesystem"),
            family="storage",
            allowed={"filesystem"},
        ),
    }
    return selected


def _normalize_backend_token(
    value: Any,
    *,
    family: str,
    allowed: set[str],
) -> str:
    token = str(value).strip().lower()
    if token not in allowed:
        allowed_tokens = ", ".join(sorted(allowed))
        raise DependencyBackendSelectionError(
            f"Unknown backend {token!r} for '{family}'. Allowed: {allowed_tokens}."
        )
    return token


def _validate_mode_backend_compatibility(
    mode: str,
    selected_backends: Mapping[str, str],
) -> None:
    if mode == "desktop" and selected_backends["ui"] != "desktop":
        raise DependencyCompatibilityError(
            "desktop mode requires a desktop-capable 'ui' backend."
        )


def _validate_backend_requirements(
    selected_backends: Mapping[str, str],
    environment: Mapping[str, str],
) -> None:
    if selected_backends["sync"] == "kadi" and not environment.get("KADI_API_TOKEN"):
        raise DependencyResolutionError(
            "KADI_API_TOKEN is required when sync backend 'kadi' is selected."
        )


def _clock_factory() -> object:
    return {"kind": "clock"}


def _event_sink_factory() -> object:
    return {"kind": "event_sink"}


def _filesystem_factory() -> object:
    return {"kind": "filesystem"}


def _observability_factory_builder(backend: str) -> DependencyFactory:
    return lambda: {"kind": "observability", "backend": backend}


def _storage_factory_builder(backend: str) -> DependencyFactory:
    return lambda: {"kind": "storage", "backend": backend}


def _ui_factory_builder(backend: str) -> DependencyFactory:
    return lambda: {"kind": "ui", "backend": backend}


def _sync_factory_builder(backend: str) -> DependencyFactory:
    if backend == "kadi":
        return lambda: {"kind": "sync", "backend": "kadi"}
    if backend == "noop":
        return lambda: {"kind": "sync", "backend": "noop"}
    raise DependencyImportError(
        f"Unsupported sync backend import path for {backend!r}."
    )


def _plugins_factory_builder(backend: str) -> DependencyFactory:
    if backend != "builtin":
        raise DependencyImportError(
            f"Unsupported plugins backend import path for {backend!r}."
        )
    return lambda: {"kind": "plugins", "backend": "builtin"}
