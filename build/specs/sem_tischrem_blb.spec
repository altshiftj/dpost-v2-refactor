# build/specs/tischrem_blb.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata
import sys

SPEC_PATH = Path(sys.argv[0]).resolve()
ROOT      = SPEC_PATH.parents[2]
SRC_PATH  = ROOT / "src"
ENV_FILE  = ROOT / ".env"

# ---------------------------------------------------------------------------------
# 1.  **Point Analysis at the real script, not '-m'**
# ---------------------------------------------------------------------------------
MAIN_SCRIPT = SRC_PATH / "ipat_watchdog" / "__main__.py"

device_plugins = collect_submodules("ipat_watchdog.plugins.sem_tischrem_blb")

metadata_datas = copy_metadata("ipat-watchdog")

a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(SRC_PATH)],
    binaries=[],
    datas=metadata_datas + [(str(ENV_FILE), ".")],
    hiddenimports=device_plugins,
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="wd-sem_tischrem_blb",
    console=False,
    upx=True,
)
