from __future__ import annotations

from types import SimpleNamespace

from ipat_watchdog import __main__ as main_module
from ipat_watchdog.core.app.bootstrap import MissingConfiguration, StartupError


class DummyApp:
    def __init__(self, raise_on_run=False):
        self._raise_on_run = raise_on_run

    def run(self):
        if self._raise_on_run:
            raise RuntimeError("boom")


def test_main_success(monkeypatch):
    app = DummyApp()

    monkeypatch.setattr(
        main_module,
        "bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 0


def test_main_missing_configuration(monkeypatch):
    def raise_missing():
        raise MissingConfiguration("no config")

    monkeypatch.setattr(main_module, "bootstrap", raise_missing)

    assert main_module.main() == 1


def test_main_startup_error(monkeypatch):
    def raise_startup():
        raise StartupError("startup failed")

    monkeypatch.setattr(main_module, "bootstrap", raise_startup)

    assert main_module.main() == 1


def test_main_run_error(monkeypatch):
    app = DummyApp(raise_on_run=True)

    monkeypatch.setattr(
        main_module,
        "bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 1
