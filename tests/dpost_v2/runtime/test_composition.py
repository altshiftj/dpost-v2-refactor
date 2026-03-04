from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping

import pytest

from dpost_v2.application.runtime.dpost_app import DPostApp
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
            "clock": lambda: object(),
            "filesystem": lambda: object(),
        }
    )

    with pytest.raises(CompositionInitializationError, match="healthcheck"):
        compose_runtime(
            context,
            healthchecks=(
                lambda _bindings: (_ for _ in ()).throw(RuntimeError("boom")),
            ),
        )


def test_composition_default_factory_returns_runtime_app_surface() -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.emitted: list[object] = []

        def emit(self, event: object) -> None:
            self.emitted.append(event)

    class FixedClock:
        def now(self) -> datetime:
            return datetime(2026, 3, 4, 15, 0, tzinfo=UTC)

    event_sink = EventSinkAdapter()
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: event_sink,
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: FixedClock(),
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert isinstance(bundle.app, DPostApp)
    assert result.terminal_reason == "end_of_stream"
    assert event_sink.emitted[0]["kind"] == "runtime_started"
    assert event_sink.emitted[-1]["kind"] == "runtime_completed"


def test_composition_rejects_invalid_event_sink_binding_for_default_app() -> None:
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: object(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    with pytest.raises(CompositionBindingError, match="event"):
        compose_runtime(context)


def test_composition_exposes_application_port_diagnostics() -> None:
    class EventSinkAdapter:
        def emit(self, event: object) -> None:
            return None

    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: {"kind": "ui", "backend": "headless"},
            "event_sink": lambda: EventSinkAdapter(),
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: {"kind": "clock"},
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)

    assert bundle.diagnostics["application_ports"] == (
        "clock",
        "event",
        "file_ops",
        "filesystem",
        "plugin_host",
        "record_store",
        "sync",
        "ui",
    )


def test_composition_default_app_consumes_ui_event_source() -> None:
    class EventSinkAdapter:
        def __init__(self) -> None:
            self.events: list[Mapping[str, object]] = []

        def emit(self, event: Mapping[str, object]) -> None:
            self.events.append(dict(event))

    class UiAdapter:
        def initialize(self) -> None:
            return None

        def notify(self, *, severity: str, title: str, message: str) -> None:
            return None

        def prompt(
            self, *, prompt_type: str, payload: dict[str, object]
        ) -> dict[str, object]:
            return {"accepted": True}

        def show_status(self, *, message: str) -> None:
            return None

        def shutdown(self) -> None:
            return None

        def iter_events(self):
            return (
                {
                    "event_id": "evt-ui-001",
                    "path": "/tmp/ui-file.txt",
                    "event_kind": "created",
                },
            )

    class ClockAdapter:
        def now(self) -> datetime:
            return datetime(2026, 3, 4, 16, 0, tzinfo=UTC)

    event_sink = EventSinkAdapter()
    context = _build_context(
        factories={
            "observability": lambda: object(),
            "storage": lambda: {"kind": "storage", "backend": "filesystem"},
            "sync": lambda: {"kind": "sync", "backend": "noop"},
            "ui": lambda: UiAdapter(),
            "event_sink": lambda: event_sink,
            "plugins": lambda: {"kind": "plugins", "backend": "builtin"},
            "clock": lambda: ClockAdapter(),
            "filesystem": lambda: {"kind": "filesystem"},
        }
    )

    bundle = compose_runtime(context)
    result = bundle.app.run()

    assert result.processed_count == 1
    assert any(event["kind"] == "ingestion_succeeded" for event in event_sink.events)
    assert event_sink.events[-1]["kind"] == "runtime_completed"
