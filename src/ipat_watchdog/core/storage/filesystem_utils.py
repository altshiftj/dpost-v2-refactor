"""
Filesystem and naming utilities used by the processing pipeline.

This module centralizes filename parsing/validation, path computation for
records/exceptions/rename destinations, file moves with fallbacks, and simple
ID generation helpers. It also persists lightweight record state to JSON for
day-level continuity.

Keep functions small and predictable; prefer returning strings/paths and let
callers handle higher-level orchestration.
"""
from pathlib import Path
import shutil
import logging
import json
import re
from typing import Callable, Optional

from ipat_watchdog.core.config.settings_store import SettingsStore
from ipat_watchdog.core.config.constants import (
 DIRECTORY_LIST, 
 ID_SEP, 
 DEST_DIR, 
 FILENAME_PATTERN, 
 EXCEPTIONS_DIR, 
 RENAME_DIR, 
 DAILY_RECORDS_JSON
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.ui.ui_messages import ValidationMessages

logger = setup_logger(__name__)

# -------------------------------
# FILE NAME PARSING
# -------------------------------

def parse_filename(src_path: str) -> tuple[str, str]:
    """Return filename stem and suffix for a path-like string.

    Args:
        src_path: File or directory path (string accepted).

    Returns:
        (stem, suffix) where suffix includes the leading dot (e.g. ".tiff").
    """
    p = Path(src_path)
    return p.stem, p.suffix


# -------------------------------
# PATH MANAGEMENT
# -------------------------------

def init_dirs(directories: Optional[list[str]] = None) -> None:
    """Ensure required directory structure exists.

    Note: The optional `directories` argument is currently ignored; this
    function initializes the standard DIRECTORY_LIST defined in constants.
    """

    for dir_path in DIRECTORY_LIST:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def get_record_path(filename_prefix: str, device_abbr: str = None) -> str:
    """Compute (and create) the destination record folder for a prefix.

    If `device_abbr` is provided, it is prepended to the sample ID segment
    (e.g. "SEM-sample001"). The directory will be created if missing.
    """
    user_ID, institute, sample_ID = filename_prefix.split(ID_SEP)
    if device_abbr:
        sample_ID = f"{device_abbr}-{sample_ID}"
    record_path = Path(DEST_DIR) / institute.upper() / user_ID.upper() / sample_ID
    record_path.mkdir(parents=True, exist_ok=True)
    return str(record_path)


def get_unique_filename(directory: str, filename_prefix: str, extension: str) -> str:
    """
    Generate a unique filename in the specified directory.
    Sequential processing ensures no race conditions.
    
    Args:
        directory: Target directory path
        filename_prefix: Base filename without extension
        extension: File extension including dot
        
    Returns:
        str: Full path to a unique filename
    """
    s = SettingsStore.get()
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # Find the highest existing counter
    counter = 1
    for existing in dir_path.iterdir():
        if existing.is_file() and existing.suffix == extension:
            existing_prefix = existing.stem
            prefix_no_counter = existing_prefix.rsplit(ID_SEP, 1)[0]
            if prefix_no_counter == filename_prefix:
                try:
                    suffix_num = int(existing_prefix.rsplit(ID_SEP, 1)[1])
                    if suffix_num >= counter:
                        counter = suffix_num + 1
                except (ValueError, IndexError):
                    continue
    
    # Generate the next available filename
    candidate_name = f"{filename_prefix}{ID_SEP}{counter:02d}{extension}"
    candidate_path = dir_path / candidate_name
    return str(candidate_path)

def get_rename_path(name: str, base_dir: Optional[str] = None) -> str:
    """Return a unique path under the rename folder for the given name."""
    base_dir = base_dir or RENAME_DIR
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(base_dir, filename_prefix, extension)

def get_exception_path(name: str, base_dir: Optional[str] = None) -> str:
    """Return a unique path under the exceptions folder for the given name."""
    base_dir = base_dir or EXCEPTIONS_DIR
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(base_dir, filename_prefix, extension)

def remove_directory_if_empty(path: Path) -> None:
    """Attempt to remove a directory; log if not empty or removal fails."""
    try:
        path.rmdir()
        logger.debug(f"Removed empty directory: '{path}'.")
    except OSError:
        logger.warning(f"Could not remove directory: '{path}'.")


# -------------------------------
# FILE MOVEMENT / STORAGE ACTIONS
# -------------------------------

def move_item(src: str, dest: str) -> None:
    """Move a file or directory to `dest`, retrying with shutil if needed.

    Handles pre-existing empty placeholder files at destination by removing
    them first. Logs warnings on rename fallback and errors on failure.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    
    # If destination exists as a placeholder file (empty), remove it first
    if dest_path.exists() and dest_path.stat().st_size == 0:
        dest_path.unlink()
    
    try:
        src_path.rename(dest_path)
    except OSError as e:
        logger.warning("Path.rename() failed for '%s' to '%s': %s. Attempting shutil.move.", src, dest, e)
        try:
            # Remove placeholder if it exists
            if dest_path.exists() and dest_path.stat().st_size == 0:
                dest_path.unlink()
            shutil.move(src, dest)
        except Exception as e_move:
            logger.error("Failed to move '%s' to '%s' using shutil.move: %s.", src, dest, e_move)
            raise e_move

def _move_to_folder(
    src: str,
    filename_prefix: str,
    extension: str,
    unique_path_func: Callable[[str], str],
    log_message: str,
    log_level: int = logging.INFO,
) -> None:
    """Generic move helper using a path factory and structured logging."""
    full_name = f"{filename_prefix}{extension}"
    dest = unique_path_func(full_name)
    move_item(src, dest)
    logger.log(log_level, log_message.format(src, dest))

def move_to_exception_folder(src_path: str, filename_prefix: str = None, extension: str = None) -> None:
    """Move an item to the exceptions folder (unique path)."""
    if filename_prefix is None:
        filename_prefix = Path(src_path).stem
    if extension is None:
        extension = Path(src_path).suffix
    _move_to_folder(
        src=src_path,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=get_exception_path,
        log_message="Moved '{}' to exceptions folder at '{}'",
        log_level=logging.WARNING,
    )

def move_to_rename_folder(src: str, filename_prefix: str, extension: str = "") -> None:
    """Move an item to the rename folder (unique path)."""
    _move_to_folder(
        src=src,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=get_rename_path,
        log_message="Moved '{}' to rename folder at '{}'",
        log_level=logging.INFO,
    )

def move_to_record_folder(src: str, filename_prefix: str, extension: str = "") -> None:
    """Move an item to the computed record folder (unique filename)."""
    _move_to_folder(
        src=src,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=get_record_path,
        log_message="Moved '{}' to record folder for '{}'",
        log_level=logging.INFO,
    )

# -------------------------------
# ID GENERATION
# -------------------------------

def generate_record_id(filename_prefix: str, dev_kadi_record_id: Optional[str] = None) -> str:
    """
    Generate a record ID using the device KADI record prefix and the filename prefix.

    If dev_kadi_record_id is not provided, this will attempt to fetch the current
    device from SettingsStore.get_manager().get_current_device() and use its
    DEVICE_RECORD_KADI_ID. This allows callers to omit the device argument when a
    device context is already established for the current thread.
    """
    if dev_kadi_record_id is None:
        try:
            manager = SettingsStore.get_manager()
            device = manager.get_current_device()
        except Exception:
            device = None
        if device is None or not getattr(device, "DEVICE_RECORD_KADI_ID", None):
            raise ValueError(
                "Device context is not set; provide dev_kadi_record_id explicitly or set current device."
            )
        dev_kadi_record_id = device.DEVICE_RECORD_KADI_ID
    return f"{dev_kadi_record_id}{ID_SEP}{filename_prefix}".lower()

def generate_file_id(filename_prefix: str, device_abbr: Optional[str] = None) -> str:
    """
    Generate a file ID combining device abbreviation and sample id from the prefix.

    If device_abbr is not provided, attempts to read it from the current device
    in SettingsStore. Callers are encouraged to pass it explicitly when available.
    """
    if device_abbr is None:
        try:
            manager = SettingsStore.get_manager()
            device = manager.get_current_device()
        except Exception:
            device = None
        if device is None or not getattr(device, "DEVICE_ABBR", None):
            raise ValueError(
                "Device context is not set; provide device_abbr explicitly or set current device."
            )
        device_abbr = device.DEVICE_ABBR
    user_id, institute, sample_id = filename_prefix.split(ID_SEP)
    return f"{device_abbr}{ID_SEP}{sample_id}"

# -------------------------------
# RECORD PERSISTENCE
# -------------------------------

def load_persisted_records() -> dict[str, LocalRecord]:
    """Load persisted daily records from JSON into LocalRecord instances.

    Returns an empty dict on first run or on read/parse failures (logged).
    """
    json_path = Path(DAILY_RECORDS_JSON)
    if not json_path.exists():
        return {}
    try:
        raw_data = json_path.read_text(encoding="utf-8")
        records = json.loads(raw_data)
        logger.debug(f"JSON data loaded from '{json_path}'.")
        return {
            id: LocalRecord.from_dict(record_data)
            for id, record_data in records.items()
        }
    except Exception as e:
        logger.exception(f"Failed to read or convert JSON file '{json_path}': {e}")
        return {}

def save_persisted_records(daily_records_dict: dict[str, LocalRecord]):
    """Serialize LocalRecord mapping to JSON for day-level persistence."""
    json_path = Path(DAILY_RECORDS_JSON)
    try:
        serialized = json.dumps(
            {key: record.to_dict() for key, record in daily_records_dict.items()},
            indent=4,
        )
        json_path.write_text(serialized, encoding="utf-8")
        logger.debug(f"JSON data saved to '{json_path}'.")
    except Exception as e:
        logger.exception(f"Failed to write JSON file '{json_path}': {e}")

# -------------------------------
# FILENAME VALIDATION
# -------------------------------

def is_valid_prefix(raw_prefix: str) -> bool:
    """Quick validation check for a filename prefix against regex and segments."""
    if not FILENAME_PATTERN.match(raw_prefix):
        logger.debug(f"Prefix '{raw_prefix}' failed regex match.")
        return False
    return raw_prefix.count(ID_SEP) >= 2

def sanitize_prefix(raw_prefix: str) -> str:
    """Normalize a raw prefix to lowercase and underscore-separated sample id."""
    s = SettingsStore.get()
    parts = raw_prefix.strip().split(ID_SEP)
    if len(parts) < 3:
        return raw_prefix
    user_id = parts[0].strip()
    institute = parts[1].strip()
    sample_id = ID_SEP.join(part.strip() for part in parts[2:]).replace(" ", "_")
    return f"{user_id.lower()}{ID_SEP}{institute.lower()}{ID_SEP}{sample_id}"

def sanitize_and_validate(raw_prefix: str) -> tuple[str, bool]:
    """Return (sanitized_prefix, is_valid) for a raw filename prefix."""
    if not is_valid_prefix(raw_prefix):
        return raw_prefix, False
    return sanitize_prefix(raw_prefix), True

def explain_filename_violation(filename: str) -> dict:
    """Analyze a filename string and return reasons/highlights when invalid.

    The returned dict contains: { valid: bool, reasons: list[str], highlight_spans: list[tuple[int,int]] }.
    """
    s = SettingsStore.get()
    result = {
        "valid": True,
        "reasons": [],
        "highlight_spans": [],
    }

    if not FILENAME_PATTERN.match(filename):
        result["valid"] = False
        segments = filename.split(ID_SEP)

        if len(segments) != 3:
            result["reasons"].append(ValidationMessages.MISSING_SEPARATOR)
            for i, char in enumerate(filename):
                if char == ID_SEP:
                    result["highlight_spans"].append((i, i + 1))
        else:
            user, institute, sample = segments
            user_start = 0
            user_end = len(user)
            inst_start = user_end + 1
            inst_end = inst_start + len(institute)
            sample_start = inst_end + 1
            sample_end = len(filename)

            if not re.fullmatch(r"[A-Za-z]+", user):
                result["reasons"].append(ValidationMessages.USER_ONLY_LETTERS)
                for i, char in enumerate(user):
                    if not re.match(r"[A-Za-z]", char):
                        result["highlight_spans"].append((user_start + i, user_start + i + 1))

            if not re.fullmatch(r"[A-Za-z]+", institute):
                result["reasons"].append(ValidationMessages.INSTITUTE_ONLY_LETTERS)
                for i, char in enumerate(institute):
                    if not re.match(r"[A-Za-z]", char):
                        result["highlight_spans"].append((inst_start + i, inst_start + i + 1))

            if len(sample) > 30:
                result["reasons"].append(ValidationMessages.SAMPLE_TOO_LONG)

            if not re.fullmatch(r"^[A-Za-z0-9_ ]+", sample):
                result["reasons"].append(ValidationMessages.SAMPLE_INVALID_CHARS)
                for i, char in enumerate(sample):
                    if not re.match(r"[A-Za-z0-9_ ]", char):
                        result["highlight_spans"].append((sample_start + i, sample_start + i + 1))
    return result

def analyze_user_input(dialog_result: dict | None) -> dict:
    """Validate and sanitize rename dialog input structure.

    Returns a dict with keys: valid, sanitized (str|None), reasons, highlight_spans.
    When invalid or cancelled, reasons/highlights are populated for UI display.
    """
    output = {
        "valid": True,
        "sanitized": None,
        "reasons": [],
        "highlight_spans": [],
    }

    if dialog_result is None:
        output["valid"] = False
        output["reasons"].append("User cancelled the dialog.")
        return output

    user_id = dialog_result.get("name", "").strip()
    institute = dialog_result.get("institute", "").strip()
    sample_id = dialog_result.get("sample_ID", "").strip()

    raw_prefix = f"{user_id}{ID_SEP}{institute}{ID_SEP}{sample_id}"
    sanitized, is_valid = sanitize_and_validate(raw_prefix)

    if is_valid:
        output["sanitized"] = sanitized
    else:
        output["valid"] = False
        violation_info = explain_filename_violation(raw_prefix)
        output["reasons"].extend(violation_info["reasons"])
        output["highlight_spans"].extend(violation_info["highlight_spans"])

    return output