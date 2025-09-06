# ipat_watchdog/core/config/zwick_utm_settings.py
from ipat_watchdog.core.config.device_settings_base import DeviceSettings
import re

class SettingsZwickUTM(DeviceSettings):
    """
    Configuration for the Zwick/Roell universal testing machine.
    Overrides device-specific settings from DeviceSettings.
    """

    # Device identity
    DEVICE_ID = "utm_zwick"

    # ─── Runtime / Watchdog ----------------------------------------------------
    SESSION_TIMEOUT       = 4 * 3600             # close session after 4 h idle
    POLL_SECONDS          = 1.0
    MAX_WAIT_SECONDS      = 30.0
    STABLE_CYCLES         = 3
    TEMP_FOLDER_REGEX     = re.compile(r"\.~tmp$")   # rarely used by testXpert

    # ─── File handling ---------------------------------------------------------
    ALLOWED_EXTENSIONS        = {".zs2", ".xlsx"}
    ALLOWED_FOLDER_CONTENTS   = set()             # device writes plain files
    SENTINEL_NAME             = None              # rely on stable-cycles logic

    # ─── Device identity -------------------------------------------------------
    DEVICE_USER_KADI_ID       = "utm-01-usr"
    DEVICE_USER_PERSISTENT_ID = 30
    DEVICE_RECORD_KADI_ID     = "utm_01"
    DEVICE_RECORD_PERSISTENT_ID = 561
    DEVICE_TYPE               = "UTM"

    # ─── Metadata defaults -----------------------------------------------------
    RECORD_TAGS = [
        "Mechanical Test",
    ]

    DEFAULT_RECORD_DESCRIPTION = r"""
## Zwick/Roell Universal Testing Machine

This record contains both the **raw binary output** (`*.zs2`, compressed into ZIP)
and the **post-processed Excel workbook** (`*.xlsx`) for each tensile/compression
test.  Raw files preserve the full resolution of force–displacement channels and
can be re-analysed in Zwick testXpert.  The Excel file includes the calculated
stress–strain curve and summary statistics.

**Typical columns in the workbook**

| Column            | Meaning                       |
|-------------------|-------------------------------|
| Time [s]          | Time stamp since test start   |
| Force [N]         | Load cell reading             |
| Extension [mm]    | Crosshead displacement        |
| Stress [MPa]      | Calculated                    |
| Strain [%]        | Calculated                    |

Please add sample geometry, material batch, gauge length and other context
information below.
"""
