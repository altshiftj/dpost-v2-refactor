from __future__ import annotations

import pytest

from dpost_v2.runtime.startup_dependencies import (
    DependencyBackendSelectionError,
    DependencyCompatibilityError,
    DependencyResolutionError,
    resolve_startup_dependencies,
)


def test_dependency_resolution_uses_mode_defaults_and_lazy_markers() -> None:
    dependencies = resolve_startup_dependencies(
        settings={"mode": "headless", "profile": "ci", "backends": {}},
        environment={},
    )

    assert dependencies.selected_backends == {
        "ui": "headless",
        "sync": "noop",
        "plugins": "builtin",
        "observability": "structured",
        "storage": "filesystem",
    }
    assert {"sync", "plugins"} <= dependencies.lazy_factories
    assert set(dependencies.factories) == {
        "observability",
        "storage",
        "clock",
        "event_sink",
        "filesystem",
        "plugins",
        "sync",
        "ui",
    }


def test_dependency_resolution_rejects_unknown_backend() -> None:
    with pytest.raises(DependencyBackendSelectionError, match="Unknown backend"):
        resolve_startup_dependencies(
            settings={
                "mode": "headless",
                "profile": "ci",
                "backends": {"sync": "mystery"},
            },
            environment={},
        )


def test_dependency_resolution_requires_desktop_capable_ui() -> None:
    with pytest.raises(DependencyCompatibilityError, match="desktop"):
        resolve_startup_dependencies(
            settings={
                "mode": "desktop",
                "profile": "ci",
                "backends": {"ui": "headless"},
            },
            environment={},
        )


def test_dependency_resolution_requires_kadi_token() -> None:
    with pytest.raises(DependencyResolutionError, match="KADI_API_TOKEN"):
        resolve_startup_dependencies(
            settings={
                "mode": "headless",
                "profile": "ci",
                "backends": {"sync": "kadi"},
            },
            environment={},
        )
