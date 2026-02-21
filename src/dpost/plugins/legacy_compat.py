"""Legacy plugin namespace compatibility helpers for phased retirement."""

from __future__ import annotations

LEGACY_DEVICE_ENTRYPOINT_GROUP = "ipat_watchdog.device_plugins"
LEGACY_PC_ENTRYPOINT_GROUP = "ipat_watchdog.pc_plugins"


def legacy_entrypoint_groups(group: str) -> tuple[str, ...]:
    """Return legacy entry point groups that map to the canonical dpost group."""
    if group == "dpost.device_plugins":
        return (LEGACY_DEVICE_ENTRYPOINT_GROUP,)
    if group == "dpost.pc_plugins":
        return (LEGACY_PC_ENTRYPOINT_GROUP,)
    return ()


def legacy_builtin_packages() -> tuple[tuple[str, str], ...]:
    """Return legacy built-in package roots used for transition compatibility."""
    return (
        ("ipat_watchdog.device_plugins", LEGACY_DEVICE_ENTRYPOINT_GROUP),
        ("ipat_watchdog.pc_plugins", LEGACY_PC_ENTRYPOINT_GROUP),
    )


def legacy_builtin_module_name(group: str, name: str) -> str | None:
    """Return legacy module path that maps to canonical dpost group/name."""
    if group == "dpost.device_plugins":
        return f"ipat_watchdog.device_plugins.{name}.plugin"
    if group == "dpost.pc_plugins":
        return f"ipat_watchdog.pc_plugins.{name}.plugin"
    return None
