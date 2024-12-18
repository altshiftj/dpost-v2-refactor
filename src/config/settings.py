import os
import re
import logging
from kadi_apy import KadiManager

DEVICE_ID = "REM_01"

WATCH_DIR = os.path.abspath("monitored_folder")
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
RECORD_DIR = os.path.join(WATCH_DIR, 'Records')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(RECORD_DIR, 'archive_db.json')
DAILY_RECORDS_JSON = os.path.join(RECORD_DIR, 'daily_records.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9-]+$')

TESTING = False
TESTING_PATH = ""

LOG_FILE = 'watchdog.log'

SESSION_TIMEOUT = 300 # 5 minutes

DEBOUNCE_TIME = 1.0
