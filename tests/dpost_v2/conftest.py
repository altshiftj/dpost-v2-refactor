"""Shared fixtures for deterministic V2 tests and harnesses."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from typing import Any

import pytest

from tests.dpost_v2._support.factories import (
    build_bootstrap_request,
    build_runtime_context,
    build_startup_context,
    build_startup_dependencies,
    build_startup_settings,
)


def pytest_configure(config: pytest.Config) -> None:
    """Use importlib collection mode to avoid duplicate basename collisions."""
    config.option.importmode = "importlib"


@pytest.fixture
def v2_workspace_root(tmp_path: Path) -> Path:
    """Provide a deterministic workspace root for V2 settings/path tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def v2_golden_corpus_path() -> Path:
    """Return the default sample golden corpus fixture file path."""
    return Path(__file__).parent / "harness" / "fixtures" / "golden_corpus.sample.json"


@pytest.fixture
def v2_now_utc() -> Callable[[], datetime]:
    """Expose deterministic wall-clock time for bootstrap tests."""
    fixed_now = datetime(2026, 3, 4, 12, 0, 0, tzinfo=UTC)
    return lambda: fixed_now


@pytest.fixture
def v2_trace_id_factory() -> Callable[[], str]:
    """Return a deterministic trace-id sequence generator."""
    trace_counter = count(1)

    def _next_trace_id() -> str:
        return f"trace-{next(trace_counter):04d}"

    return _next_trace_id


@pytest.fixture
def v2_bootstrap_request_factory(
    v2_trace_id_factory: Callable[[], str],
) -> Callable[..., Any]:
    """Build deterministic bootstrap requests with optional overrides."""

    def _factory(
        *,
        mode: str = "headless",
        profile: str | None = "ci",
        trace_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ):
        return build_bootstrap_request(
            mode=mode,
            profile=profile,
            trace_id=trace_id or v2_trace_id_factory(),
            metadata=metadata,
        )

    return _factory


@pytest.fixture
def v2_startup_settings_factory(v2_workspace_root: Path) -> Callable[..., Any]:
    """Build startup settings rooted in the per-test workspace."""

    def _factory(**overrides: object):
        return build_startup_settings(
            root_hint=v2_workspace_root,
            **overrides,
        )

    return _factory


@pytest.fixture
def v2_startup_dependencies_factory() -> Callable[..., Any]:
    """Build startup dependencies with deterministic default bindings."""

    def _factory(**overrides: object):
        return build_startup_dependencies(**overrides)

    return _factory


@pytest.fixture
def v2_startup_context_factory(
    v2_workspace_root: Path,
    v2_trace_id_factory: Callable[[], str],
) -> Callable[..., Any]:
    """Build startup context using deterministic launch metadata defaults."""

    def _factory(**overrides: object):
        trace_id = str(overrides.pop("trace_id", v2_trace_id_factory()))
        return build_startup_context(
            root_hint=v2_workspace_root,
            trace_id=trace_id,
            **overrides,
        )

    return _factory


@pytest.fixture
def v2_runtime_context_factory(
    v2_trace_id_factory: Callable[[], str],
) -> Callable[..., Any]:
    """Build runtime context fixtures with deterministic trace ids."""

    def _factory(**overrides: object):
        trace_id = str(overrides.pop("trace_id", v2_trace_id_factory()))
        return build_runtime_context(
            trace_id=trace_id,
            **overrides,
        )

    return _factory
