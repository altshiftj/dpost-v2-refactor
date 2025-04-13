from pathlib import Path
import re

WATCH_DIR = Path("Upload_Ordner").resolve()

DEST_DIR = Path("Data").resolve()
RENAME_DIR = DEST_DIR / "00_To_Rename"
EXCEPTIONS_DIR = DEST_DIR / "01_Exceptions"
DAILY_RECORDS_JSON = DEST_DIR / "record_persistence.json"

r"""
   ^(?!.*\.\.):   No consecutive dots ".." anywhere in the string
   (?!\.):        The first character must not be a dot
   [A-Za-z]+:     First segment = letters only
   -:             Literal underscore
   [A-Za-z]+:     Second segment = letters only
   -:             Another underscore
   [a-z0-9_ ]+:   Third segment = lower case letters, digits, underscores, and spaces
   (?<!\.):       Must not end with a dot
   $:             End of string

   Exemplary format: 'UserID-Institute-Sample_ID'
"""
FILENAME_PATTERN = re.compile(
    r"^(?!.*\.\.)(?!\.)([A-Za-z]+)-[A-Za-z]+-[A-Za-z0-9_ ]{1,30}(?<!\.)$"
)

ID_SEP = "-"
FILE_SEP = "_"

LOG_FILE = DEST_DIR / "watchdog.log"

SESSION_TIMEOUT = 600  # 10 minutes

SYNC_LOGS = True
LOG_SYNC_INTERVAL = 60  # 1 minute
