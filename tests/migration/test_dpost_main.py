"""Migration tests for the dpost CLI entrypoint."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

from dpost import __main__ as main_module
from ipat_watchdog.core.app.bootstrap import MissingConfiguration, StartupError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DPOST_MAIN_PATH = PROJECT_ROOT / "src" / "dpost" / "__main__.py"
DPOST_RUNTIME_BOOTSTRAP_PATH = (
    PROJECT_ROOT / "src" / "dpost" / "runtime" / "bootstrap.py"
)


class DummyApp:
    """Minimal app stub used to test entrypoint control flow."""

    def __init__(self, raise_on_run: bool = False) -> None:
        """Create a dummy app that optionally fails on run."""
        self._raise_on_run = raise_on_run

    def run(self) -> None:
        """Execute the app run path."""
        if self._raise_on_run:
            raise RuntimeError("boom")


def test_main_success(monkeypatch) -> None:
    """Return zero when bootstrap and run both succeed."""
    app = DummyApp()

    monkeypatch.setattr(
        main_module,
        "compose_bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 0


def test_main_missing_configuration(monkeypatch) -> None:
    """Return one when required startup config is missing."""

    def raise_missing() -> None:
        raise MissingConfiguration("no config")

    monkeypatch.setattr(main_module, "compose_bootstrap", raise_missing)

    assert main_module.main() == 1


def test_main_startup_error(monkeypatch) -> None:
    """Return one when bootstrap raises a startup error."""

    def raise_startup() -> None:
        raise StartupError("startup failed")

    monkeypatch.setattr(main_module, "compose_bootstrap", raise_startup)

    assert main_module.main() == 1


def test_main_run_error(monkeypatch) -> None:
    """Return one when app.run() raises an unexpected error."""
    app = DummyApp(raise_on_run=True)

    monkeypatch.setattr(
        main_module,
        "compose_bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 1


def test_main_unknown_sync_adapter_from_env(monkeypatch) -> None:
    """Return one when env-selected sync adapter name is unknown."""
    from dpost.runtime.composition import compose_bootstrap
    from ipat_watchdog.core.app.bootstrap import StartupError as CurrentStartupError

    bootstrap_module = importlib.import_module("ipat_watchdog.core.app.bootstrap")

    monkeypatch.setenv("DPOST_SYNC_ADAPTER", "missing-adapter")
    monkeypatch.setattr(
        bootstrap_module,
        "bootstrap",
        lambda *args, **kwargs: SimpleNamespace(app=DummyApp()),
    )
    monkeypatch.setattr(main_module, "StartupError", CurrentStartupError)
    monkeypatch.setattr(main_module, "compose_bootstrap", compose_bootstrap)

    assert main_module.main() == 1


def test_dpost_main_no_longer_uses_transition_exception_class_helpers() -> None:
    """Require post-sunset main to avoid class-indirection helper imports."""
    main_contents = DPOST_MAIN_PATH.read_text(encoding="utf-8")

    assert "missing_configuration_cls" not in main_contents
    assert "startup_error_cls" not in main_contents


def test_runtime_bootstrap_no_longer_exports_transition_exception_helpers() -> None:
    """Require post-sunset runtime bootstrap to retire class helper exports."""
    bootstrap_contents = DPOST_RUNTIME_BOOTSTRAP_PATH.read_text(encoding="utf-8")

    assert "def startup_error_cls" not in bootstrap_contents
    assert "def missing_configuration_cls" not in bootstrap_contents
