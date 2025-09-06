# ipat_watchdog/device_plugins/dsv_horiba/settings.py
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
import re

class SettingsDSVHoriba(DeviceSettings):
    """
    Configuration for the Horiba Dissolver.
    Handles raw data files (.wdb, .wdk, .wdp) and exported text files (.txt).
    """

    # Device identity
    DEVICE_ID = "dsv_horiba"

    # ─── Runtime / Watchdog ----------------------------------------------------
    SESSION_TIMEOUT       = 600 # seconds

    # ─── File handling ---------------------------------------------------------
    ALLOWED_EXTENSIONS        = {".wdb", ".wdk", ".wdp", ".txt"}

    # ─── Device identity -------------------------------------------------------
    DEVICE_USER_KADI_ID       = "dsv-01-usr"
    DEVICE_USER_PERSISTENT_ID = 31
    DEVICE_RECORD_KADI_ID     = "dsv_01"
    DEVICE_RECORD_PERSISTENT_ID = 562
    DEVICE_TYPE               = "DSV"

    # ─── Metadata defaults -----------------------------------------------------
    RECORD_TAGS = [
        "Dissolution Test",
        "Particle Analysis",
    ]

    DEFAULT_RECORD_DESCRIPTION = r"""
## Horiba Dissolver Analysis

This record contains both the **raw binary data** (`*.wdb`, `*.wdk`, `*.wdp`, compressed into ZIP)
and the **exported text files** (`*.txt`) from dissolution tests. Raw files preserve the full
measurement data and can be re-analyzed with Horiba software. The text files contain the
processed results and dissolution curves.

**File types:**
- `.wdb` - Raw database file
- `.wdk` - Raw data configuration
- `.wdp` - Raw data parameters  
- `.txt` - Exported dissolution results and curves

**Analysis parameters:** Sample size, dissolution medium, temperature, stirring rate.
"""

