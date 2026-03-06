from pathlib import Path
import sys

SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT = SPEC_PATH.parents[2]
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from dpost_v2.infrastructure.build.pyinstaller_baseline import (
    EXECUTABLE_NAME,
    canonical_entry_script,
    collect_hiddenimports,
)

ENTRY_SCRIPT = canonical_entry_script(ROOT)

a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=[],
    hiddenimports=list(collect_hiddenimports()),
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXECUTABLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=EXECUTABLE_NAME,
)
