# build/specs/horiba_blb.spec (you can keep one spec per profile, or make a generic one)
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
import os, re, sys

SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT      = SPEC_PATH.parents[2]
SRC_PATH  = ROOT / "src"
BUILD_DIR = ROOT / "build"

sys.path.insert(0, str(SRC_PATH))
MAIN_SCRIPT = SRC_PATH / "ipat_watchdog" / "__main__.py"

# ---- read build-time choices from env (set by the PS script) ----
pc_name = os.getenv("PC_NAME", "horiba_blb").strip()
devices_raw = os.getenv("DEVICE_PLUGINS", "").strip()
device_names = [d for d in re.split(r"[,\s;]+", devices_raw) if d] or []

# ---- build plugin lists dynamically ----
pc_plugins = collect_submodules(f"ipat_watchdog.pc_plugins.{pc_name}")

device_plugins = []
for dn in device_names:
    device_plugins += collect_submodules(f"ipat_watchdog.device_plugins.{dn}")

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
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# sanitize exe name (avoid weird chars)
exe_name = f"wd-{pc_name}"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
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
