from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from dpost_v2.infrastructure.runtime.ui.adapters import (
    UiAdapterCapabilityError,
    UiAdapterContractError,
    UiAdapterRuntimeError,
    UiAdapterShim,
)


@dataclass
class _Backend:
    calls: list[tuple[str, object]]

    def initialize(self) -> None:
        self.calls.append(("initialize", None))

    def notify(self, *, severity: str, title: str, message: str) -> None:
        self.calls.append(
            ("notify", {"severity": severity, "title": title, "message": message})
        )

    def prompt(self, *, prompt_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("prompt", {"prompt_type": prompt_type, "payload": payload}))
        return {"accepted": True}

    def show_status(self, *, message: str) -> None:
        self.calls.append(("status", message))

    def shutdown(self) -> None:
        self.calls.append(("shutdown", None))


def test_shim_requires_all_ui_contract_methods() -> None:
    class _Broken:
        def initialize(self) -> None:
            return None

    with pytest.raises(UiAdapterContractError):
        UiAdapterShim(_Broken())


def test_shim_reports_capabilities_and_blocks_unsupported_prompt_types() -> None:
    backend = _Backend(calls=[])
    shim = UiAdapterShim(backend, supported_prompt_types={"confirm"})

    assert shim.supports("confirm") is True
    assert shim.supports("rename") is False
    with pytest.raises(UiAdapterCapabilityError):
        shim.prompt(prompt_type="rename", payload={})


def test_shim_maps_backend_failures_to_runtime_error() -> None:
    class _FailingBackend(_Backend):
        def prompt(
            self, *, prompt_type: str, payload: dict[str, Any]
        ) -> dict[str, Any]:
            raise RuntimeError("backend failed")

    shim = UiAdapterShim(_FailingBackend(calls=[]))

    with pytest.raises(UiAdapterRuntimeError):
        shim.prompt(prompt_type="confirm", payload={})


def test_shim_delegates_successful_calls() -> None:
    backend = _Backend(calls=[])
    shim = UiAdapterShim(backend)

    shim.initialize()
    shim.notify(severity="info", title="t", message="m")
    response = shim.prompt(prompt_type="confirm", payload={"q": "ok?"})
    shim.show_status(message="done")
    shim.shutdown()

    assert response == {"accepted": True}
    assert [call[0] for call in backend.calls] == [
        "initialize",
        "notify",
        "prompt",
        "status",
        "shutdown",
    ]
