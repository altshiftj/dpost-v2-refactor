from __future__ import annotations

from dataclasses import dataclass

import pytest

from dpost_v2.application.startup.context import (
    LaunchMetadata,
    StartupContextBindingError,
    StartupContextOverrideError,
    build_startup_context,
    with_override,
)
from dpost_v2.runtime.startup_dependencies import StartupDependencies


@dataclass(frozen=True)
class FakeSettings:
    mode: str = "headless"
    profile: str = "ci"


def _meta(mode: str) -> LaunchMetadata:
    return LaunchMetadata(
        requested_mode=mode,
        requested_profile="ci",
        trace_id="trace-context",
        process_id=99,
        boot_timestamp_utc="2026-03-04T10:00:00Z",
    )


def test_build_startup_context_requires_ui_binding_for_desktop_mode() -> None:
    dependencies = StartupDependencies(
        factories={"event_sink": lambda: object()},
        selected_backends={"ui": "headless"},
        lazy_factories=frozenset(),
        warnings=(),
        cleanup=None,
    )

    with pytest.raises(StartupContextBindingError, match="ui"):
        build_startup_context(
            settings=FakeSettings(mode="desktop"),
            dependencies=dependencies,
            launch_meta=_meta("desktop"),
        )


def test_startup_context_is_immutable() -> None:
    dependencies = StartupDependencies(
        factories={
            "ui": lambda: object(),
            "event_sink": lambda: object(),
        },
        selected_backends={"ui": "headless"},
        lazy_factories=frozenset(),
        warnings=(),
        cleanup=None,
    )

    context = build_startup_context(
        settings=FakeSettings(mode="headless"),
        dependencies=dependencies,
        launch_meta=_meta("headless"),
    )

    with pytest.raises(AttributeError):
        context.settings = FakeSettings(mode="desktop")


def test_with_override_rejects_duplicate_override_keys() -> None:
    dependencies = StartupDependencies(
        factories={
            "ui": lambda: object(),
            "event_sink": lambda: object(),
        },
        selected_backends={"ui": "headless"},
        lazy_factories=frozenset(),
        warnings=(),
        cleanup=None,
    )
    context = build_startup_context(
        settings=FakeSettings(mode="headless"),
        dependencies=dependencies,
        launch_meta=_meta("headless"),
    )

    with pytest.raises(StartupContextOverrideError, match="settings"):
        with_override(
            context,
            override_map={"settings": FakeSettings(mode="desktop")},
            settings=FakeSettings(mode="headless"),
        )
