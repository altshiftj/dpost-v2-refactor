# -*- mode: python ; coding: utf-8 -*-
# build/specs/pc_tischrem_blb.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
import sys

SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT      = SPEC_PATH.parents[2]
SRC_PATH  = ROOT / "src"
BUILD_DIR = ROOT / "build"

# ---------------------------------------------------------------------------------
# PC-centric build for tischrem_blb PC (devices: sem_phenomxl2)
# ---------------------------------------------------------------------------------
MAIN_SCRIPT = SRC_PATH / "ipat_watchdog" / "__main__.py"

# Collect all required plugins for tischrem_blb PC
pc_plugins = collect_submodules("ipat_watchdog.pc_plugins.tischrem_blb")
device_plugins = collect_submodules("ipat_watchdog.device_plugins.sem_phenomxl2")

metadata_datas = copy_metadata("ipat-watchdog")

a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=metadata_datas + [
        (str(BUILD_DIR / ".env"), "."),
        (str(BUILD_DIR / "version.txt"), "."),
    ],
    hiddenimports=[
        'ipat_watchdog.pc_plugins.tischrem_blb.plugin',
        'ipat_watchdog.device_plugins.sem_phenomxl2.plugin',
    ] + pc_plugins + device_plugins,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='wd-tischrem_blb',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
