"""Unit tests for PC-to-device mapping expectations."""

from __future__ import annotations

import pytest

from dpost.plugins.loading import get_devices_for_pc


_EXPECTED_MAPPINGS = [
    ("test_pc", ["test_device"]),
    ("tischrem_blb", ["sem_phenomxl2"]),
    ("zwick_blb", ["utm_zwick"]),
    ("horiba_blb", ["psa_horiba", "dsv_horiba"]),
    ("kinexus_blb", ["rhe_kinexus"]),
    ("haake_blb", ["extr_haake"]),
    ("hioki_blb", ["erm_hioki"]),
    ("eirich_blb", ["rmx_eirich_el1", "rmx_eirich_r01"]),
]


@pytest.mark.parametrize("pc_name, expected", _EXPECTED_MAPPINGS)
def test_pc_device_mapping(pc_name: str, expected: list[str]) -> None:
    """Return the configured device list for each canonical PC plugin mapping."""
    assert get_devices_for_pc(pc_name) == expected


@pytest.mark.parametrize("pc_name", [name for name, _ in _EXPECTED_MAPPINGS])
def test_mapping_completeness(pc_name: str) -> None:
    """Ensure mapping results are non-empty string identifiers."""
    devices = get_devices_for_pc(pc_name)
    assert isinstance(devices, list)
    assert devices
    assert all(isinstance(device, str) for device in devices)


def test_pc_plugin_not_found() -> None:
    """Raise runtime error for unknown PC plugin identifiers."""
    with pytest.raises(RuntimeError, match="No PC plugin named 'unknown_pc'"):
        get_devices_for_pc("unknown_pc")
