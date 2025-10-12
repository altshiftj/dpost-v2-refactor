# build/specs/zwick_blb.spec
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
import sys

SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT      = SPEC_PATH.parents[2]
SRC_PATH  = ROOT / "src"
BUILD_DIR = ROOT / "build"

# ensure src/ importable during analysis
sys.path.insert(0, str(SRC_PATH))

MAIN_SCRIPT = SRC_PATH / "ipat_watchdog" / "__main__.py"

pc_plugins     = collect_submodules("ipat_watchdog.pc_plugins.zwick_blb")
device_plugins = collect_submodules("ipat_watchdog.device_plugins.utm_zwick")
metadata_datas = list(copy_metadata("ipat-watchdog"))

datas_extra = []
env_file = BUILD_DIR / ".env"
ver_file = BUILD_DIR / "version.txt"
if env_file.exists(): datas_extra.append((str(env_file), "."))
if ver_file.exists(): datas_extra.append((str(ver_file), "."))

a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=metadata_datas + datas_extra,
    hiddenimports=pc_plugins + device_plugins,
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
    name="wd-zwick_blb",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
