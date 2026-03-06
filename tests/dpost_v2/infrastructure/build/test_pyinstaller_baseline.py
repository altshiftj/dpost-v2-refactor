from __future__ import annotations

from pathlib import Path

from dpost_v2.infrastructure.build.pyinstaller_baseline import (
    accepted_plugin_packages,
    canonical_entry_script,
    collect_hiddenimports,
    resolve_build_variant,
    resolve_build_variant_from_env,
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


def test_pyinstaller_baseline_uses_stable_default_build_variant() -> None:
    variant = resolve_build_variant()

    assert variant.executable_name == "dpost-v2-headless"
    assert variant.console is False


def test_pyinstaller_baseline_uses_stable_debug_build_variant() -> None:
    variant = resolve_build_variant(debug_console=True)

    assert variant.executable_name == "dpost-v2-headless-debug"
    assert variant.console is True


def test_pyinstaller_baseline_resolves_debug_variant_from_environment() -> None:
    variant = resolve_build_variant_from_env({"DPOST_PYINSTALLER_DEBUG_CONSOLE": "1"})

    assert variant.executable_name == "dpost-v2-headless-debug"
    assert variant.console is True


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
