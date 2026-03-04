from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpost_v2.application.startup.context import LaunchMetadata, build_startup_context
from dpost_v2.runtime.composition import (
    CompositionBindingError,
    CompositionDuplicateBindingError,
    CompositionInitializationError,
    compose_runtime,
)
from dpost_v2.runtime.startup_dependencies import StartupDependencies


@dataclass(frozen=True)
class FakeSettings:
    mode: str = "headless"
    profile: str = "ci"


def _build_context(factories):
    dependencies = StartupDependencies(
        factories=factories,
        selected_backends={"ui": "headless", "sync": "noop", "plugins": "builtin"},
        lazy_factories=frozenset(),
        warnings=(),
        cleanup=None,
    )
    return build_startup_context(
        settings=FakeSettings(),
        dependencies=dependencies,
        launch_meta=LaunchMetadata(
            requested_mode="headless",
            requested_profile="ci",
            trace_id="trace-compose",
            process_id=77,
            boot_timestamp_utc="2026-03-04T11:00:00Z",
        ),
    )


def test_composition_raises_for_missing_required_port() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "ui": lambda: object(),
            "event_sink": lambda: object(),
        }
    )

    with pytest.raises(CompositionBindingError, match="storage"):
        compose_runtime(
            context,
            required_ports=("observability", "storage", "ui", "event_sink"),
        )


def test_composition_raises_for_duplicate_required_port() -> None:
    context = _build_context(
        factories={
            "ui": lambda: object(),
            "event_sink": lambda: object(),
            "observability": lambda: object(),
            "storage": lambda: object(),
        }
    )

    with pytest.raises(CompositionDuplicateBindingError, match="ui"):
        compose_runtime(context, required_ports=("ui", "event_sink", "ui"))


def test_composition_initializes_ports_in_deterministic_order() -> None:
    init_calls: list[str] = []

    def _factory(name: str):
        return lambda: init_calls.append(name) or {"adapter": name}

    context = _build_context(
        factories={
            "observability": _factory("observability"),
            "storage": _factory("storage"),
            "sync": _factory("sync"),
            "ui": _factory("ui"),
            "event_sink": _factory("event_sink"),
            "plugins": _factory("plugins"),
        }
    )

    bundle = compose_runtime(
        context,
        required_ports=(
            "observability",
            "storage",
            "sync",
            "ui",
            "event_sink",
            "plugins",
        ),
        app_factory=lambda bindings, _context: {
            "ports": tuple(bindings.keys()),
            "mode": _context.launch.requested_mode,
        },
    )

    assert init_calls == [
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
    ]
    assert tuple(bundle.port_bindings) == (
        "observability",
        "storage",
        "sync",
        "ui",
        "event_sink",
        "plugins",
    )
    assert bundle.app["mode"] == "headless"


def test_composition_wraps_healthcheck_failures() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: object(),
            "sync": lambda: object(),
            "ui": lambda: object(),
            "event_sink": lambda: object(),
            "plugins": lambda: object(),
        }
    )

    with pytest.raises(CompositionInitializationError, match="healthcheck"):
        compose_runtime(
            context,
            healthchecks=(
                lambda _bindings: (_ for _ in ()).throw(RuntimeError("boom")),
            ),
        )
