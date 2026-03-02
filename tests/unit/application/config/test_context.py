"""Unit coverage for config context global-service guard helpers."""

from __future__ import annotations

import pytest

import dpost.application.config as config_api
from dpost.application.config import context


def test_get_service_raises_when_not_initialized() -> None:
    """Raise explicit runtime error when global config service is missing."""
    context.reset_service()
    with pytest.raises(RuntimeError, match="has not been initialised"):
        context.get_service()


def test_config_package_namespace_omits_ambient_service_helpers() -> None:
    """Keep ambient context helper APIs out of package-level config namespace."""
    assert not hasattr(config_api, "current")
    assert not hasattr(config_api, "get_service")
    assert not hasattr(config_api, "set_service")


def test_config_package_namespace_omits_context_lifecycle_helpers() -> None:
    """Keep config lifecycle/context helpers scoped to config.context module."""
    assert not hasattr(config_api, "init_config")
    assert not hasattr(config_api, "reset_service")
    assert not hasattr(config_api, "activate_device")
