import os
import re
import logging

DEVICE_NAME = "REM_01"

WATCH_DIR = os.path.abspath("monitored_folder")
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9-]+$')

LOG_FILE = 'watchdog.log'
