"""Runtime startup dependency resolver for deterministic bootstrap wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dpost_v2.infrastructure.observability.logging import (
    StructuredLoggingConfig,
    build_structured_logger,
)
from dpost_v2.infrastructure.runtime.ui.factory import build_ui_adapter
from dpost_v2.infrastructure.storage.file_ops import LocalFileOpsAdapter
from dpost_v2.infrastructure.storage.record_store import (
    RecordStoreConfig,
    SqliteRecordStoreAdapter,
)
from dpost_v2.infrastructure.sync.kadi import KadiSyncAdapter
from dpost_v2.infrastructure.sync.noop import NoopSyncAdapter
from dpost_v2.plugins.discovery import discover_from_namespaces
from dpost_v2.plugins.host import PluginHost

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
    backend_provenance = _resolve_backend_provenance(
        normalized_settings,
        selected_backends=selected_backends,
    )
    _validate_mode_backend_compatibility(selected_mode, selected_backends)
    _validate_backend_requirements(selected_backends, env, normalized_settings)

    factory_map: dict[str, DependencyFactory] = {
        "observability": _observability_factory_builder(
            selected_backends["observability"],
            normalized_settings,
        ),
        "storage": _storage_factory_builder(
            selected_backends["storage"],
            normalized_settings,
        ),
        "clock": _clock_factory,
        "event_sink": _event_sink_factory_builder(normalized_settings),
        "filesystem": _filesystem_factory_builder(normalized_settings),
        "ui": _ui_factory_builder(
            mode=selected_mode,
            backend=selected_backends["ui"],
        ),
        "sync": _sync_factory_builder(
            selected_backends["sync"],
            normalized_settings,
            env,
        ),
        "plugins": _plugins_factory_builder(
            selected_backends["plugins"],
            normalized_settings,
        ),
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
            "backend_provenance": backend_provenance,
            "plugin_backend": selected_backends["plugins"],
            "plugin_visibility": "configured",
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
        "paths": {
            "root": getattr(getattr(settings, "paths", None), "root", None),
            "watch": getattr(getattr(settings, "paths", None), "watch", None),
            "dest": getattr(getattr(settings, "paths", None), "dest", None),
            "staging": getattr(getattr(settings, "paths", None), "staging", None),
        },
        "sync": {
            "backend": getattr(getattr(settings, "sync", None), "backend", "noop"),
            "api_token": getattr(getattr(settings, "sync", None), "api_token", None),
        },
        "ui": {
            "backend": getattr(getattr(settings, "ui", None), "backend", "headless"),
        },
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


def _resolve_backend_provenance(
    settings: Mapping[str, Any],
    *,
    selected_backends: Mapping[str, str],
) -> dict[str, str]:
    raw_provenance = settings.get("provenance")
    provenance_map = raw_provenance if isinstance(raw_provenance, Mapping) else {}

    def _lookup(*keys: str, default: str = "unknown") -> str:
        for key in keys:
            raw_value = provenance_map.get(key)
            if raw_value is None:
                continue
            token = str(raw_value).strip().lower()
            if token:
                return token
        return default

    resolved = {
        "mode": _lookup("mode"),
        "profile": _lookup("profile"),
        "ui": _lookup("ui.backend", "backends.ui"),
        "sync": _lookup("sync.backend", "backends.sync"),
        "plugins": _lookup(
            "plugins.backend",
            "backends.plugins",
            default="resolver_default",
        ),
        "observability": _lookup(
            "observability.backend",
            "backends.observability",
            default="resolver_default",
        ),
        "storage": _lookup(
            "storage.backend",
            "backends.storage",
            default="resolver_default",
        ),
    }
    for backend_name in ("plugins", "observability", "storage"):
        if backend_name in selected_backends and resolved[backend_name] == "unknown":
            resolved[backend_name] = "resolver_default"
    return resolved


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
    settings: Mapping[str, Any],
) -> None:
    if selected_backends["sync"] != "kadi":
        return

    configured_token = _resolve_sync_api_token(settings, environment)
    if not configured_token:
        raise DependencyResolutionError(
            "KADI_API_TOKEN is required when sync backend 'kadi' is selected."
        )


def _clock_factory() -> object:
    return _SystemClock()


def _event_sink_factory_builder(settings: Mapping[str, Any]) -> DependencyFactory:
    runtime_metadata = {
        "mode": _resolve_mode(settings),
        "profile": _resolve_profile(settings) or "default",
    }

    def factory() -> object:
        return _RuntimeEventSink(runtime_metadata=runtime_metadata)

    return factory


def _filesystem_factory_builder(settings: Mapping[str, Any]) -> DependencyFactory:
    root = _resolve_runtime_root(settings)
    return lambda: LocalFileOpsAdapter(root=root)


def _observability_factory_builder(
    backend: str,
    settings: Mapping[str, Any],
) -> DependencyFactory:
    if backend != "structured":
        raise DependencyImportError(
            f"Unsupported observability backend import path for {backend!r}."
        )

    config = StructuredLoggingConfig(
        level="info",
        redacted_fields={"api_token"},
        runtime_metadata={
            "mode": _resolve_mode(settings),
            "profile": _resolve_profile(settings) or "default",
        },
    )
    return lambda: build_structured_logger(config)


def _storage_factory_builder(
    backend: str,
    settings: Mapping[str, Any],
) -> DependencyFactory:
    if backend != "filesystem":
        raise DependencyImportError(
            f"Unsupported storage backend import path for {backend!r}."
        )

    database_path = _resolve_runtime_root(settings) / "records.sqlite3"

    def factory() -> object:
        return SqliteRecordStoreAdapter(
            RecordStoreConfig(
                path=database_path,
            )
        )

    return factory


def _ui_factory_builder(*, mode: str, backend: str) -> DependencyFactory:
    def factory() -> object:
        selection = build_ui_adapter(mode=mode, backend_preference=backend)
        return selection.adapter

    return factory


def _sync_factory_builder(
    backend: str,
    settings: Mapping[str, Any],
    environment: Mapping[str, str],
) -> DependencyFactory:
    if backend == "kadi":
        endpoint = _resolve_sync_setting(
            settings,
            key="endpoint",
            default="https://kadi.invalid/api",
        )
        workspace_id = _resolve_sync_setting(
            settings,
            key="workspace_id",
            default="dpost_v2",
        )
        api_token = _resolve_sync_api_token(settings, environment)

        def factory() -> object:
            adapter = KadiSyncAdapter(
                endpoint=endpoint,
                api_token=api_token,
                workspace_id=workspace_id,
                client=_default_kadi_client,
            )
            adapter.initialize()
            return adapter

        return factory
    if backend == "noop":
        def factory() -> object:
            adapter = NoopSyncAdapter()
            adapter.initialize()
            return adapter

        return factory
    raise DependencyImportError(
        f"Unsupported sync backend import path for {backend!r}."
    )


def _plugins_factory_builder(
    backend: str,
    settings: Mapping[str, Any],
) -> DependencyFactory:
    if backend != "builtin":
        raise DependencyImportError(
            f"Unsupported plugins backend import path for {backend!r}."
        )

    def factory() -> object:
        discovery = discover_from_namespaces()
        host = PluginHost(discovery.descriptors)
        known_profiles = {
            profile
            for descriptor in discovery.descriptors
            for profile in descriptor.supported_profiles
        }
        selected_profile = _resolve_plugin_profile(settings, known_profiles)
        host.activate_profile(
            profile=selected_profile,
            known_profiles=known_profiles or None,
        )
        return host

    return factory


def _resolve_runtime_root(settings: Mapping[str, Any]) -> Path:
    raw_paths = settings.get("paths")
    if isinstance(raw_paths, Mapping):
        raw_root = raw_paths.get("root")
        if isinstance(raw_root, str) and raw_root.strip():
            return Path(raw_root).expanduser().resolve(strict=False)
    return (Path(tempfile.gettempdir()) / "dpost_v2_runtime").resolve()


def _resolve_profile(settings: Mapping[str, Any]) -> str | None:
    raw_profile = settings.get("profile")
    if raw_profile is None:
        return None
    token = str(raw_profile).strip().lower()
    return token or None


def _resolve_plugin_profile(
    settings: Mapping[str, Any],
    known_profiles: set[str],
) -> str:
    requested = _resolve_profile(settings)
    if requested and requested in known_profiles:
        return requested
    if "default" in known_profiles:
        return "default"
    if "prod" in known_profiles:
        return "prod"
    if known_profiles:
        return sorted(known_profiles)[0]
    return "default"


def _resolve_sync_setting(
    settings: Mapping[str, Any],
    *,
    key: str,
    default: str,
) -> str:
    raw_sync = settings.get("sync")
    if isinstance(raw_sync, Mapping):
        candidate = raw_sync.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return default


def _resolve_sync_api_token(
    settings: Mapping[str, Any],
    environment: Mapping[str, str],
) -> str:
    from_environment = str(environment.get("KADI_API_TOKEN", "")).strip()
    if from_environment:
        return from_environment

    raw_sync = settings.get("sync")
    if isinstance(raw_sync, Mapping):
        candidate = raw_sync.get("api_token")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _default_kadi_client(**kwargs: Any) -> Mapping[str, Any]:
    payload = kwargs.get("payload", {})
    record_id = None
    if isinstance(payload, Mapping):
        record_id = payload.get("record_id")
    return {
        "status_code": 202,
        "remote_id": str(record_id or "queued-record"),
    }


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class _RuntimeEventSink:
    def __init__(self, *, runtime_metadata: Mapping[str, Any]) -> None:
        self._runtime_metadata = MappingProxyType(dict(runtime_metadata))
        self.events: list[Mapping[str, Any]] = []

    def emit(self, event: object) -> None:
        if isinstance(event, Mapping):
            payload = dict(event)
        else:
            payload = {"event": event}
        payload.setdefault("runtime", dict(self._runtime_metadata))
        self.events.append(MappingProxyType(payload))
