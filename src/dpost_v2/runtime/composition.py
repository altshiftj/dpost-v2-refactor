"""Runtime composition root for V2 startup context wiring."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

from dpost_v2.application.startup.context import StartupContext

DEFAULT_REQUIRED_PORTS: tuple[str, ...] = (
    "observability",
    "storage",
    "sync",
    "ui",
    "event_sink",
    "plugins",
)


class CompositionError(RuntimeError):
    """Base type for composition failures."""


class CompositionBindingError(CompositionError):
    """Raised when required port bindings are missing."""


class CompositionInitializationError(CompositionError):
    """Raised when adapter/app initialization fails."""


class CompositionDuplicateBindingError(CompositionError):
    """Raised when composition attempts to bind a port more than once."""


class CompositionPluginBindingError(CompositionError):
    """Raised when plugin host binding is invalid for runtime composition."""


@dataclass(frozen=True)
class CompositionBundle:
    """Fully wired runtime application bundle."""

    app: Any
    port_bindings: Mapping[str, object]
    diagnostics: Mapping[str, Any]
    shutdown_all: Callable[[], None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "port_bindings", MappingProxyType(dict(self.port_bindings)))
        object.__setattr__(self, "diagnostics", MappingProxyType(dict(self.diagnostics)))


def compose_runtime(
    context: StartupContext,
    *,
    required_ports: Sequence[str] = DEFAULT_REQUIRED_PORTS,
    app_factory: Callable[[Mapping[str, object], StartupContext], Any] | None = None,
    healthchecks: Sequence[Callable[[Mapping[str, object]], None]] = (),
) -> CompositionBundle:
    """Compose adapters and return a runnable runtime bundle."""
    normalized_ports = tuple(required_ports)
    _validate_no_duplicate_ports(normalized_ports)
    _validate_required_bindings(context.dependencies.factories, normalized_ports)
    ordered_ports = _deterministic_port_order(normalized_ports)

    bindings = _instantiate_bindings(context.dependencies.factories, ordered_ports)
    _validate_plugin_binding(bindings.get("plugins"))
    _run_healthchecks(bindings, healthchecks)

    try:
        app = (
            app_factory(bindings, context)
            if app_factory is not None
            else _default_app_factory(bindings, context)
        )
    except Exception as exc:
        raise CompositionInitializationError("Failed to build runtime app.") from exc

    return CompositionBundle(
        app=app,
        port_bindings=bindings,
        diagnostics={
            "mode": context.launch.requested_mode,
            "profile": context.launch.requested_profile,
            "required_ports": ordered_ports,
            "selected_backends": dict(context.dependencies.selected_backends),
            "warnings": tuple(context.dependencies.warnings),
        },
        shutdown_all=_build_shutdown_hook(bindings),
    )


def _validate_no_duplicate_ports(required_ports: Sequence[str]) -> None:
    seen: set[str] = set()
    for port in required_ports:
        if port in seen:
            raise CompositionDuplicateBindingError(
                f"Duplicate port binding requested for {port!r}."
            )
        seen.add(port)


def _validate_required_bindings(
    factories: Mapping[str, Callable[[], object]],
    required_ports: Sequence[str],
) -> None:
    for port in required_ports:
        if port not in factories:
            raise CompositionBindingError(f"Missing required port binding: {port!r}.")


def _deterministic_port_order(required_ports: Sequence[str]) -> tuple[str, ...]:
    priority = {
        "observability": 0,
        "storage": 1,
        "sync": 2,
        "ui": 3,
        "event_sink": 4,
        "plugins": 5,
    }
    return tuple(
        sorted(
            required_ports,
            key=lambda name: (priority.get(name, 100), name),
        )
    )


def _instantiate_bindings(
    factories: Mapping[str, Callable[[], object]],
    required_ports: Sequence[str],
) -> dict[str, object]:
    bindings: dict[str, object] = {}
    for port in required_ports:
        factory = factories[port]
        try:
            bindings[port] = factory()
        except Exception as exc:
            raise CompositionInitializationError(
                f"Failed to initialize adapter for port {port!r}."
            ) from exc
    return bindings


def _run_healthchecks(
    bindings: Mapping[str, object],
    healthchecks: Sequence[Callable[[Mapping[str, object]], None]],
) -> None:
    for healthcheck in healthchecks:
        try:
            healthcheck(bindings)
        except Exception as exc:
            raise CompositionInitializationError(
                "Composition healthcheck failed."
            ) from exc


def _validate_plugin_binding(plugin_binding: object | None) -> None:
    if plugin_binding is None:
        raise CompositionPluginBindingError(
            "Missing plugin host binding for required 'plugins' port."
        )


def _default_app_factory(
    bindings: Mapping[str, object],
    context: StartupContext,
) -> dict[str, Any]:
    return {
        "bindings": tuple(bindings.keys()),
        "trace_id": context.launch.trace_id,
    }


def _build_shutdown_hook(bindings: Mapping[str, object]) -> Callable[[], None]:
    hooks: list[Callable[[], None]] = []
    for adapter in bindings.values():
        shutdown = _extract_shutdown_hook(adapter)
        if shutdown is not None:
            hooks.append(shutdown)

    def shutdown_all() -> None:
        for hook in reversed(hooks):
            hook()

    return shutdown_all


def _extract_shutdown_hook(adapter: object) -> Callable[[], None] | None:
    for attr_name in ("shutdown", "close", "stop"):
        candidate = getattr(adapter, attr_name, None)
        if callable(candidate):
            return candidate
    return None
