from __future__ import annotations

import runpy
from types import SimpleNamespace

import pytest

from dpost import __main__ as main_module
from dpost.runtime.bootstrap import MissingConfiguration, StartupError


class DummyApp:
    def __init__(self, raise_on_run: bool = False):
        self._raise_on_run = raise_on_run

    def run(self) -> None:
        if self._raise_on_run:
            raise RuntimeError("boom")


def test_main_success(monkeypatch) -> None:
    app = DummyApp()

    monkeypatch.setattr(
        main_module,
        "compose_bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 0


def test_main_missing_configuration(monkeypatch) -> None:
    def raise_missing() -> None:
        raise MissingConfiguration("no config")

    monkeypatch.setattr(main_module, "compose_bootstrap", raise_missing)

    assert main_module.main() == 1


def test_main_startup_error(monkeypatch) -> None:
    def raise_startup() -> None:
        raise StartupError("startup failed")

    monkeypatch.setattr(main_module, "compose_bootstrap", raise_startup)

    assert main_module.main() == 1


def test_main_run_error(monkeypatch) -> None:
    app = DummyApp(raise_on_run=True)

    monkeypatch.setattr(
        main_module,
        "compose_bootstrap",
        lambda: SimpleNamespace(app=app),
    )

    assert main_module.main() == 1


def test_module_entrypoint_invokes_sys_exit(monkeypatch) -> None:
    import dpost.runtime.composition as composition_module

    monkeypatch.setattr(
        composition_module,
        "compose_bootstrap",
        lambda: SimpleNamespace(app=DummyApp()),
    )

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("dpost.__main__", run_name="__main__")
    assert exc_info.value.code == 0
