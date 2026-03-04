from __future__ import annotations

from typing import Any

import pytest

from dpost_v2.infrastructure.runtime.ui.dialogs import (
    DialogBackendError,
    DialogSpecValidationError,
    DialogTypeError,
    dispatch_dialog,
)


def test_dispatch_dialog_normalizes_cancelled_backend_response() -> None:
    response = dispatch_dialog(
        prompt_type="confirm",
        payload={"question": "Proceed?"},
        backend_prompt=lambda request: None,
        prompt_id_factory=lambda: "prompt-1",
        monotonic_ns=lambda: 10,
    )

    assert response["prompt_id"] == "prompt-1"
    assert response["action"] == "cancelled"
    assert response["cancelled"] is True


def test_dispatch_dialog_rejects_unknown_prompt_type() -> None:
    with pytest.raises(DialogTypeError):
        dispatch_dialog(
            prompt_type="unsupported",
            payload={},
            backend_prompt=lambda request: {},
        )


def test_dispatch_dialog_rejects_non_mapping_payload() -> None:
    with pytest.raises(DialogSpecValidationError):
        dispatch_dialog(
            prompt_type="confirm",
            payload=[] , # type: ignore[arg-type]
            backend_prompt=lambda request: {},
        )


def test_dispatch_dialog_maps_backend_exceptions() -> None:
    def _backend(_: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    with pytest.raises(DialogBackendError):
        dispatch_dialog(
            prompt_type="confirm",
            payload={"question": "Proceed?"},
            backend_prompt=_backend,
        )
