"""Migration tests for the dpost CLI entrypoint."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

from dpost import __main__ as main_module
from ipat_watchdog.core.app.bootstrap import MissingConfiguration, StartupError


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
