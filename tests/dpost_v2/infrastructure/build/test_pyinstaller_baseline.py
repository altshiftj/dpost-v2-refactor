from __future__ import annotations

from pathlib import Path

from dpost_v2.infrastructure.build.pyinstaller_baseline import (
    EXECUTABLE_NAME,
    accepted_plugin_packages,
    canonical_entry_script,
    collect_hiddenimports,
)


def test_pyinstaller_baseline_targets_canonical_dpost_entrypoint() -> None:
    repo_root = Path(__file__).resolve().parents[4]

    entry_script = canonical_entry_script(repo_root)

    assert entry_script == repo_root / "src" / "dpost" / "__main__.py"
    assert entry_script.exists()


def test_pyinstaller_baseline_collects_hiddenimports_for_accepted_plugin_set() -> None:
    hiddenimports = collect_hiddenimports()

    assert "dpost_v2.plugins.devices" in hiddenimports
    assert "dpost_v2.plugins.pcs" in hiddenimports
    assert "dpost_v2.plugins.devices.sem_phenomxl2.plugin" in hiddenimports
    assert "dpost_v2.plugins.devices.psa_horiba.plugin" in hiddenimports
    assert "dpost_v2.plugins.devices.utm_zwick.plugin" in hiddenimports
    assert "dpost_v2.plugins.pcs.tischrem_blb.plugin" in hiddenimports
    assert "dpost_v2.plugins.pcs.horiba_blb.plugin" in hiddenimports
    assert "dpost_v2.plugins.pcs.zwick_blb.plugin" in hiddenimports


def test_pyinstaller_baseline_uses_stable_executable_name() -> None:
    assert EXECUTABLE_NAME == "dpost-v2-headless"


def test_pyinstaller_baseline_lists_accepted_plugin_packages_deterministically() -> (
    None
):
    assert accepted_plugin_packages() == (
        "dpost_v2.plugins.devices.psa_horiba",
        "dpost_v2.plugins.devices.sem_phenomxl2",
        "dpost_v2.plugins.devices.utm_zwick",
        "dpost_v2.plugins.pcs.horiba_blb",
        "dpost_v2.plugins.pcs.tischrem_blb",
        "dpost_v2.plugins.pcs.zwick_blb",
    )
