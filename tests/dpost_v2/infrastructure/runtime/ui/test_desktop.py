from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import pytest

from dpost_v2.infrastructure.runtime.ui.desktop import (
    DesktopUiAdapter,
    DesktopUiAdapterError,
    DesktopUiCallbackError,
)
from dpost_v2.infrastructure.runtime.ui.dialogs import dispatch_dialog
from dpost_v2.infrastructure.runtime.ui.tkinter import TkinterUiAdapter


@dataclass
class _Backend:
    notified: int = 0
    statuses: list[str] | None = None

    def initialize(self) -> None:
        return None

    def notify(self, *, severity: str, title: str, message: str) -> None:
        self.notified += 1

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "prompt_type": prompt_type, "payload": payload}

    def show_status(self, *, message: str) -> None:
        if self.statuses is None:
            self.statuses = []
        self.statuses.append(message)

    def shutdown(self) -> None:
        return None


def test_desktop_adapter_updates_view_model_and_delegates_backend_calls() -> None:
    backend = _Backend(statuses=[])
    adapter = DesktopUiAdapter(
        backend=backend,
        dialog_dispatch=lambda **kwargs: {"action": "accepted", "cancelled": False},
    )
    adapter.initialize()

    adapter.notify(severity="info", title="hello", message="world")
    adapter.show_status(message="running")

    assert backend.notified == 1
    assert backend.statuses == ["running"]
    assert adapter.view_model.last_status == "running"
    assert adapter.view_model.notification_count == 1


def test_desktop_adapter_uses_dialog_dispatch_for_prompt() -> None:
    backend = _Backend(statuses=[])

    def _dispatch(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["prompt_type"] == "confirm"
        assert kwargs["payload"] == {"question": "Proceed?"}
        return {"action": "accepted", "cancelled": False}

    adapter = DesktopUiAdapter(backend=backend, dialog_dispatch=_dispatch)
    adapter.initialize()

    response = adapter.prompt(prompt_type="confirm", payload={"question": "Proceed?"})

    assert response["action"] == "accepted"
    assert adapter.view_model.prompt_count == 1


def test_desktop_adapter_maps_dialog_failures() -> None:
    backend = _Backend(statuses=[])

    def _dispatch(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("dialog boom")

    adapter = DesktopUiAdapter(backend=backend, dialog_dispatch=_dispatch)
    adapter.initialize()

    with pytest.raises(DesktopUiAdapterError):
        adapter.prompt(prompt_type="confirm", payload={})


def test_desktop_adapter_maps_callback_failures() -> None:
    backend = _Backend(statuses=[])

    adapter = DesktopUiAdapter(
        backend=backend,
        dialog_dispatch=lambda **kwargs: {"action": "accepted", "cancelled": False},
        on_user_action=lambda result: (_ for _ in ()).throw(RuntimeError("callback boom")),
    )
    adapter.initialize()

    with pytest.raises(DesktopUiCallbackError):
        adapter.prompt(prompt_type="confirm", payload={})


def test_desktop_adapter_integrates_dialog_dispatch_with_tkinter_backend() -> None:
    backend = _Backend(statuses=[])
    tkinter = TkinterUiAdapter(backend=backend, ui_thread_id=threading.get_ident())
    adapter = DesktopUiAdapter(backend=tkinter, dialog_dispatch=dispatch_dialog)
    adapter.initialize()

    result = adapter.prompt(prompt_type="confirm", payload={"question": "Proceed?"})

    assert result["action"] == "accepted"
    assert result["cancelled"] is False
    assert result["values"]["accepted"] is True
    assert result["values"]["prompt_type"] == "confirm"
