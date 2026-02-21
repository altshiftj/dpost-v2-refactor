"""Plugin profile selection boundary helpers for dpost startup."""

from __future__ import annotations

import os
from typing import Callable

from dpost.plugins.reference import REFERENCE_PLUGIN_PROFILE, PluginProfile


def resolve_plugin_profile_selection(
    *,
    profile_name: str | None = None,
    env_profile_name: str | None = None,
    startup_error_factory: Callable[[str], Exception],
) -> PluginProfile | None:
    """Resolve optional plugin profile selection with actionable errors."""
    selected_name = (
        (
            profile_name
            if profile_name is not None
            else (
                env_profile_name
                if env_profile_name is not None
                else os.getenv("DPOST_PLUGIN_PROFILE") or ""
            )
        )
        .strip()
        .lower()
    )
    if not selected_name:
        return None

    if selected_name == "reference":
        return REFERENCE_PLUGIN_PROFILE

    raise startup_error_factory(
        "Unknown plugin profile " f"'{selected_name}'. Available profiles: reference."
    )
