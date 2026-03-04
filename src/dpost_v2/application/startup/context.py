"""Startup context contracts and validators."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from dpost_v2.runtime.startup_dependencies import StartupDependencies


class StartupContextError(RuntimeError):
    """Base type for startup context failures."""


class StartupContextBindingError(StartupContextError):
    """Raised when required dependency bindings are missing."""


class StartupContextValidationError(StartupContextError):
    """Raised when startup settings and launch metadata are incompatible."""


class StartupContextOverrideError(StartupContextError):
    """Raised when context override hooks are invalid or ambiguous."""


@dataclass(frozen=True)
class LaunchMetadata:
    """Runtime metadata attached to one bootstrap execution."""

    requested_mode: str
    requested_profile: str | None
    trace_id: str
    process_id: int
    boot_timestamp_utc: str


@dataclass(frozen=True)
class StartupContext:
    """Immutable startup context passed through composition and launch."""

    settings: Any
    dependencies: StartupDependencies
    launch: LaunchMetadata


def build_startup_context(
    *,
    settings: Any,
    dependencies: StartupDependencies,
    launch_meta: LaunchMetadata,
) -> StartupContext:
    """Build and validate immutable startup context."""
    context = StartupContext(
        settings=settings,
        dependencies=dependencies,
        launch=launch_meta,
    )
    validate_startup_context(context)
    return context


def validate_startup_context(context: StartupContext) -> None:
    """Validate mode/binding compatibility for startup context."""
    if not context.dependencies.factories:
        raise StartupContextBindingError(
            "Startup dependencies must contain at least one factory binding."
        )

    mode = _resolve_mode(context.settings, context.launch)
    launch_mode = str(context.launch.requested_mode).strip().lower()
    if launch_mode != mode:
        raise StartupContextValidationError(
            "Launch metadata mode does not match normalized settings mode."
        )

    if "event_sink" not in context.dependencies.factories:
        raise StartupContextBindingError("Missing required dependency binding: 'event_sink'.")

    if mode == "desktop" and "ui" not in context.dependencies.factories:
        raise StartupContextBindingError(
            "Missing required dependency binding: 'ui' for desktop mode."
        )

    if mode == "desktop":
        selected_ui = str(
            context.dependencies.selected_backends.get("ui", "")
        ).strip().lower()
        if selected_ui and selected_ui != "desktop":
            raise StartupContextValidationError(
                "Desktop startup context requires desktop UI backend."
            )


def serialize_startup_context(context: StartupContext) -> Mapping[str, Any]:
    """Return a stable diagnostics payload for startup context."""
    settings_mode = _resolve_mode(context.settings, context.launch)
    payload = {
        "mode": settings_mode,
        "requested_mode": context.launch.requested_mode,
        "requested_profile": context.launch.requested_profile,
        "trace_id": context.launch.trace_id,
        "process_id": context.launch.process_id,
        "boot_timestamp_utc": context.launch.boot_timestamp_utc,
        "available_bindings": tuple(sorted(context.dependencies.factories)),
        "selected_backends": dict(context.dependencies.selected_backends),
        "lazy_bindings": tuple(sorted(context.dependencies.lazy_factories)),
    }
    return MappingProxyType(payload)


def with_override(
    context: StartupContext,
    *,
    override_map: Mapping[str, Any] | None = None,
    **overrides: Any,
) -> StartupContext:
    """Return a derived context with explicit overrides for deterministic tests."""
    combined: dict[str, Any] = dict(override_map or {})
    duplicate_keys = set(combined).intersection(overrides)
    if duplicate_keys:
        duplicate = ", ".join(sorted(duplicate_keys))
        raise StartupContextOverrideError(
            f"Duplicate override keys detected: {duplicate}."
        )

    combined.update(overrides)
    allowed = {"settings", "dependencies", "launch"}
    unknown = set(combined).difference(allowed)
    if unknown:
        unknown_keys = ", ".join(sorted(unknown))
        raise StartupContextOverrideError(
            f"Unknown startup context override keys: {unknown_keys}."
        )

    return build_startup_context(
        settings=combined.get("settings", context.settings),
        dependencies=combined.get("dependencies", context.dependencies),
        launch_meta=combined.get("launch", context.launch),
    )


def _resolve_mode(settings: Any, launch_meta: LaunchMetadata) -> str:
    mode = getattr(settings, "mode", launch_meta.requested_mode)
    normalized = str(mode).strip().lower()
    if normalized not in {"headless", "desktop"}:
        raise StartupContextValidationError(f"Unsupported startup mode: {mode!r}.")
    return normalized
