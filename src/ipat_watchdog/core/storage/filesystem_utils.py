"""
Filesystem and naming utilities used by the processing pipeline.

This module centralizes filename parsing/validation, path computation for
records/exceptions/rename destinations, file moves with fallbacks, and simple
ID generation helpers. It also persists lightweight record state to JSON for
day-level continuity.

Keep functions small and predictable; prefer returning strings/paths and let
callers handle higher-level orchestration.
"""
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Callable, Optional, Union

from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
from ipat_watchdog.core.config.service import ActiveConfig
from ipat_watchdog.core.interactions.messages import ValidationMessages
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.records.local_record import LocalRecord

logger = setup_logger(__name__)


def _active_config() -> ActiveConfig | None:
    try:
        return current()
    except RuntimeError:
        return None


def _directory_list() -> tuple[Path, ...]:
    cfg = _active_config()
    if cfg is not None:
        return cfg.directory_list
    return tuple(_CONST.DIRECTORY_LIST)


def _dest_dir() -> Path:
    cfg = _active_config()
    if cfg is not None:
        return cfg.paths.dest_dir
    return _CONST.DEST_DIR


def _rename_dir() -> Path:
    cfg = _active_config()
    if cfg is not None:
        return cfg.paths.rename_dir
    return _CONST.RENAME_DIR


def _exceptions_dir() -> Path:
    cfg = _active_config()
    if cfg is not None:
        return cfg.paths.exceptions_dir
    return _CONST.EXCEPTIONS_DIR


def _daily_records_path() -> Path:
    cfg = _active_config()
    if cfg is not None:
        return cfg.paths.daily_records_json
    return _CONST.DAILY_RECORDS_JSON


def _id_sep() -> str:
    cfg = _active_config()
    if cfg is not None:
        return cfg.id_separator
    return _CONST.ID_SEP


def _file_sep() -> str:
    cfg = _active_config()
    if cfg is not None:
        return cfg.file_separator
    return _CONST.FILE_SEP


def _filename_pattern():
    cfg = _active_config()
    if cfg is not None:
        return cfg.filename_pattern
    return _CONST.FILENAME_PATTERN


def _current_device():
    cfg = _active_config()
    if cfg is not None:
        return cfg.device
    return None



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
    """Ensure required directory structure exists."""

    if directories is not None:
        target_dirs = [Path(p) for p in directories]
    else:
        target_dirs = [Path(p) for p in _directory_list()]

    for dir_path in target_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_record_path(filename_prefix: str, device_abbr: str | None = None) -> str:
    """Compute (and create) the destination record folder for a prefix."""

    sep = _id_sep()
    parts = filename_prefix.split(sep)
    if len(parts) < 3:
        raise ValueError(f"Filename prefix '{filename_prefix}' does not contain three segments.")
    user_id, institute = parts[0], parts[1]
    sample_id = sep.join(parts[2:])

    if device_abbr is None:
        device = _current_device()
        if device and device.metadata.device_abbr:
            device_abbr = device.metadata.device_abbr
    if device_abbr:
        sample_id = f"{device_abbr}-{sample_id}"

    record_path = _dest_dir() / institute.upper() / user_id.upper() / sample_id
    record_path.mkdir(parents=True, exist_ok=True)
    return str(record_path)


def get_unique_filename(directory: str, filename_prefix: str, extension: str) -> str:
    """Generate a unique filename in the specified directory."""

    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)

    sep = _id_sep()
    counter = 1
    for existing in dir_path.iterdir():
        if existing.is_file() and existing.suffix == extension:
            existing_prefix = existing.stem
            prefix_no_counter = existing_prefix.rsplit(sep, 1)[0]
            if prefix_no_counter == filename_prefix:
                try:
                    suffix_num = int(existing_prefix.rsplit(sep, 1)[1])
                    counter = max(counter, suffix_num + 1)
                except (ValueError, IndexError):
                    continue

    candidate_name = f"{filename_prefix}{sep}{counter:02d}{extension}"
    candidate_path = dir_path / candidate_name
    return str(candidate_path)


def get_rename_path(name: str, base_dir: Optional[str] = None) -> str:
    """Return a unique path under the rename folder for the given name."""

    base = Path(base_dir) if base_dir is not None else _rename_dir()
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(str(base), filename_prefix, extension)


def get_exception_path(name: str, base_dir: Optional[str] = None) -> str:
    """Return a unique path under the exceptions folder for the given name."""

    base = Path(base_dir) if base_dir is not None else _exceptions_dir()
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(str(base), filename_prefix, extension)


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

def move_item(src: Union[str, Path], dest: Union[str, Path]) -> None:
    """Move a file or directory to `dest`, retrying with shutil if needed.

    Handles pre-existing empty placeholder files at destination by removing
    them first. Logs warnings on rename fallback and errors on failure.
    """
    src_path = Path(src)
    dest_path = Path(dest)
    
    # If destination exists as a placeholder file (empty), remove it first
    if dest_path.exists():
        if dest_path.is_file():
            if dest_path.stat().st_size == 0:
                dest_path.unlink()
        elif dest_path.is_dir():
            try:
                dest_path.rmdir()
            except OSError:
                # Directory not empty, remove recursively
                import shutil
                shutil.rmtree(dest_path)
    
    try:
        src_path.rename(dest_path)
    except OSError as e:
        logger.warning("Path.rename() failed for '%s' to '%s': %s. Attempting shutil.move.", src, dest, e)
        try:
            # Remove placeholder if it exists
            if dest_path.exists():
                if dest_path.is_file():
                    if dest_path.stat().st_size == 0:
                        dest_path.unlink()
                elif dest_path.is_dir():
                    try:
                        dest_path.rmdir()
                    except OSError:
                        import shutil
                        shutil.rmtree(dest_path)
            import shutil
            shutil.move(str(src_path), str(dest_path))
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


def move_to_exception_folder(src_path: str, filename_prefix: str | None = None, extension: str | None = None) -> None:
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
    """Generate a record ID using the device KADI record prefix and filename prefix."""

    if dev_kadi_record_id is None:
        device = _current_device()
        if device is None or not device.metadata.record_kadi_id:
            raise ValueError("Device context is not set; provide dev_kadi_record_id explicitly or activate a device.")
        dev_kadi_record_id = device.metadata.record_kadi_id

    sep = _id_sep()
    return f"{dev_kadi_record_id}{sep}{filename_prefix}".lower()


def generate_file_id(filename_prefix: str, device_abbr: Optional[str] = None) -> str:
    """Generate a file ID combining device abbreviation and sample id from the prefix."""

    if device_abbr is None:
        device = _current_device()
        if device is None or not device.metadata.device_abbr:
            raise ValueError("Device context is not set; provide device_abbr explicitly or activate a device.")
        device_abbr = device.metadata.device_abbr

    sep = _id_sep()
    parts = filename_prefix.split(sep)
    if len(parts) < 3:
        raise ValueError(f"Filename prefix '{filename_prefix}' does not contain three segments.")
    sample_id = sep.join(parts[2:])
    return f"{device_abbr}{sep}{sample_id}"


def load_persisted_records() -> dict[str, LocalRecord]:
    """Load persisted daily records from JSON into LocalRecord instances."""

    json_path = _daily_records_path()
    if not json_path.exists():
        return {}
    try:
        raw_data = json_path.read_text(encoding='utf-8')
        records = json.loads(raw_data)
        logger.debug(f"JSON data loaded from '{json_path}'.")
        return {id: LocalRecord.from_dict(record_data) for id, record_data in records.items()}
    except Exception as exc:
        logger.exception(f"Failed to read or convert JSON file '{json_path}': {exc}")
        return {}
    

def save_persisted_records(daily_records_dict: dict[str, LocalRecord]):
    """Serialize LocalRecord mapping to JSON for day-level persistence."""

    json_path = _daily_records_path()
    try:
        serialized = json.dumps(
            {key: record.to_dict() for key, record in daily_records_dict.items()},
            indent=4,
        )
        json_path.write_text(serialized, encoding='utf-8')
        logger.debug(f"JSON data saved to '{json_path}'.")
    except Exception as exc:
        logger.exception(f"Failed to write JSON file '{json_path}': {exc}")


def is_valid_prefix(raw_prefix: str) -> bool:
    """Quick validation check for a filename prefix against regex and segments."""

    pattern = _filename_pattern()
    if not pattern.match(raw_prefix):
        logger.debug(f"Prefix '{raw_prefix}' failed regex match.")
        return False
    sep = _id_sep()
    return raw_prefix.count(sep) >= 2
def sanitize_prefix(raw_prefix: str) -> str:
    """Normalize a raw prefix to lowercase and underscore-separated sample id."""

    sep = _id_sep()
    parts = raw_prefix.strip().split(sep)
    if len(parts) < 3:
        return raw_prefix
    user_id = parts[0].strip()
    institute = parts[1].strip()
    sample_id = sep.join(part.strip() for part in parts[2:]).replace(' ', '_')
    return f"{user_id.lower()}{sep}{institute.lower()}{sep}{sample_id}"


def sanitize_and_validate(raw_prefix: str) -> tuple[str, bool]:
    """Return (sanitized_prefix, is_valid) for a raw filename prefix."""
    if not is_valid_prefix(raw_prefix):
        return raw_prefix, False
    return sanitize_prefix(raw_prefix), True


def explain_filename_violation(filename: str) -> dict:
    """Analyze a filename string and return reasons/highlights when invalid."""

    result = {
        'valid': True,
        'reasons': [],
        'highlight_spans': [],
    }

    pattern = _filename_pattern()
    sep = _id_sep()
    if not pattern.match(filename):
        result['valid'] = False
        segments = filename.split(sep)

        if len(segments) != 3:
            result['reasons'].append(ValidationMessages.MISSING_SEPARATOR)
            for i, char in enumerate(filename):
                if char == sep:
                    result['highlight_spans'].append((i, i + 1))
        else:
            user, institute, sample = segments
            user_start = 0
            user_end = len(user)
            inst_start = user_end + 1
            inst_end = inst_start + len(institute)
            sample_start = inst_end + 1

            if not re.fullmatch(r'[A-Za-z]+', user):
                result['reasons'].append(ValidationMessages.USER_ONLY_LETTERS)
                for i, char in enumerate(user):
                    if not re.match(r'[A-Za-z]', char):
                        result['highlight_spans'].append((user_start + i, user_start + i + 1))

            if not re.fullmatch(r'[A-Za-z]+', institute):
                result['reasons'].append(ValidationMessages.INSTITUTE_ONLY_LETTERS)
                for i, char in enumerate(institute):
                    if not re.match(r'[A-Za-z]', char):
                        result['highlight_spans'].append((inst_start + i, inst_start + i + 1))

            if len(sample) > 30:
                result['reasons'].append(ValidationMessages.SAMPLE_TOO_LONG)

            if not re.fullmatch(r'^[A-Za-z0-9_ ]+', sample):
                result['reasons'].append(ValidationMessages.SAMPLE_INVALID_CHARS)
                for i, char in enumerate(sample):
                    if not re.match(r'[A-Za-z0-9_ ]', char):
                        result['highlight_spans'].append((sample_start + i, sample_start + i + 1))
    return result


def analyze_user_input(dialog_result: dict | None) -> dict:
    """Validate and sanitize rename dialog input structure."""

    output = {
        'valid': True,
        'sanitized': None,
        'reasons': [],
        'highlight_spans': [],
    }

    if dialog_result is None:
        output['valid'] = False
        output['reasons'].append('User cancelled the dialog.')
        return output

    user_id = dialog_result.get('name', '').strip()
    institute = dialog_result.get('institute', '').strip()
    sample_id = dialog_result.get('sample_ID', '').strip()
    sep = _id_sep()
    raw_prefix = f"{user_id}{sep}{institute}{sep}{sample_id}"
    sanitized, is_valid = sanitize_and_validate(raw_prefix)

    if is_valid:
        output['sanitized'] = sanitized
    else:
        output['valid'] = False
        violation_info = explain_filename_violation(raw_prefix)
        output['reasons'].extend(violation_info['reasons'])
        output['highlight_spans'].extend(violation_info['highlight_spans'])

    return output
