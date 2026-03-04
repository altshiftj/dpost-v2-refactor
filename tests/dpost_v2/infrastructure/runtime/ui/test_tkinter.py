from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import pytest

from dpost_v2.infrastructure.runtime.ui.tkinter import (
    TkinterUiAdapter,
    TkinterUiRenderError,
    TkinterUiThreadError,
    TkinterUiUnavailableError,
)


@dataclass
class _Backend:
    initialized: bool = False

    def initialize(self) -> None:
        self.initialized = True

    def notify(self, *, severity: str, title: str, message: str) -> None:
        return None

    def prompt(
        self, *, prompt_type: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        return {"accepted": True}

    def show_status(self, *, message: str) -> None:
        return None

    def shutdown(self) -> None:
        self.initialized = False


def test_tkinter_adapter_requires_backend_when_gui_is_requested() -> None:
    adapter = TkinterUiAdapter(backend=None)

    with pytest.raises(TkinterUiUnavailableError):
        adapter.initialize()


def test_tkinter_adapter_normalizes_cancelled_prompt_result() -> None:
    class _CancelBackend(_Backend):
        def prompt(
            self, *, prompt_type: str, payload: dict[str, Any]
        ) -> dict[str, Any] | None:
            return None

    backend = _CancelBackend()
    adapter = TkinterUiAdapter(backend=backend, ui_thread_id=threading.get_ident())
    adapter.initialize()

    response = adapter.prompt(prompt_type="confirm", payload={})

    assert response["cancelled"] is True
    assert response["action"] == "cancelled"


def test_tkinter_adapter_enforces_ui_thread_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _Backend()
    adapter = TkinterUiAdapter(backend=backend, ui_thread_id=999)
    adapter.initialize()

    monkeypatch.setattr(threading, "get_ident", lambda: 123)

    with pytest.raises(TkinterUiThreadError):
        adapter.notify(severity="info", title="x", message="y")


def test_tkinter_adapter_maps_backend_exceptions() -> None:
    class _FailingBackend(_Backend):
        def show_status(self, *, message: str) -> None:
            raise RuntimeError("render fail")

    backend = _FailingBackend()
    adapter = TkinterUiAdapter(backend=backend, ui_thread_id=threading.get_ident())
    adapter.initialize()

    with pytest.raises(TkinterUiRenderError):
        adapter.show_status(message="hello")
