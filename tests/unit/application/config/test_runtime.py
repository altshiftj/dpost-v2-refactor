"""Unit coverage for config runtime global-service guard helpers."""

from __future__ import annotations

import pytest

from dpost.application.config import runtime


def test_get_service_raises_when_not_initialized() -> None:
    """Raise explicit runtime error when global config service is missing."""
    runtime.reset_service()
    with pytest.raises(RuntimeError, match="has not been initialised"):
        runtime.get_service()
