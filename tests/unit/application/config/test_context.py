"""Unit coverage for config context global-service guard helpers."""

from __future__ import annotations

import pytest

from dpost.application.config import context


def test_get_service_raises_when_not_initialized() -> None:
    """Raise explicit runtime error when global config service is missing."""
    context.reset_service()
    with pytest.raises(RuntimeError, match="has not been initialised"):
        context.get_service()
