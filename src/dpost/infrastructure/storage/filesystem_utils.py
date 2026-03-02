"""
Filesystem and storage utilities used by the processing pipeline.

This module centralizes path computation for records/exceptions/rename
destinations, file moves with fallbacks, and persisted record state JSON
helpers for day-level continuity.

Keep functions small and predictable; prefer returning strings/paths and let
callers handle higher-level orchestration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Union

from dpost.infrastructure.logging import setup_logger

if TYPE_CHECKING:
    from dpost.domain.records.local_record import LocalRecord

logger = setup_logger(__name__)

# -------------------------------
# PATH MANAGEMENT
# -------------------------------


def init_dirs(directories: Optional[list[str]] = None) -> None:
    """Ensure required directory structure exists."""
    if directories is None:
        raise ValueError("directories must be provided explicitly")
    target_dirs = [Path(p) for p in directories]

    for dir_path in target_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_record_path(
    filename_prefix: str,
    device_abbr: str | None = None,
    *,
    id_separator: str | None = None,
    dest_dir: str | Path | None = None,
    current_device=None,
) -> str:
    """Compute (and create) the destination record folder for a prefix."""
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")
    if dest_dir is None:
        raise ValueError("dest_dir must be provided explicitly")
    sep = id_separator
    parts = filename_prefix.split(sep)
    if len(parts) < 3:
        raise ValueError(
            f"Filename prefix '{filename_prefix}' does not contain three segments."
        )
    user_id, institute = parts[0], parts[1]
    sample_id = sep.join(parts[2:])

    if device_abbr is None:
        device = current_device
        if device and device.metadata.device_abbr:
            device_abbr = device.metadata.device_abbr
    if device_abbr:
        sample_id = f"{device_abbr}-{sample_id}"

    root = Path(dest_dir)
    record_path = root / institute.upper() / user_id.upper() / sample_id
    record_path.mkdir(parents=True, exist_ok=True)
    return str(record_path)


def get_unique_filename(
    directory: str,
    filename_prefix: str,
    extension: str,
    *,
    id_separator: str | None = None,
) -> str:
    """Generate a unique filename in the specified directory."""

    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)

    sep = id_separator if id_separator else "-"
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


def get_rename_path(
    name: str,
    base_dir: Optional[str] = None,
    *,
    id_separator: str | None = None,
) -> str:
    """Return a unique path under the rename folder for the given name."""
    if base_dir is None:
        raise ValueError("base_dir must be provided explicitly")
    base = Path(base_dir)
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(
        str(base),
        filename_prefix,
        extension,
        id_separator=id_separator,
    )


def get_exception_path(
    name: str,
    base_dir: Optional[str] = None,
    *,
    id_separator: str | None = None,
) -> str:
    """Return a unique path under the exceptions folder for the given name."""
    if base_dir is None:
        raise ValueError("base_dir must be provided explicitly")
    base = Path(base_dir)
    filename_prefix, extension = Path(name).stem, Path(name).suffix
    return get_unique_filename(
        str(base),
        filename_prefix,
        extension,
        id_separator=id_separator,
    )


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
        logger.warning(
            "Path.rename() failed for '%s' to '%s': %s. Attempting shutil.move.",
            src,
            dest,
            e,
        )
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
            logger.error(
                "Failed to move '%s' to '%s' using shutil.move: %s.", src, dest, e_move
            )
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


def move_to_exception_folder(
    src_path: str,
    filename_prefix: str | None = None,
    extension: str | None = None,
    *,
    base_dir: str | None = None,
    id_separator: str | None = None,
) -> None:
    """Move an item to the exceptions folder (unique path)."""
    if base_dir is None:
        raise ValueError("base_dir must be provided explicitly")
    if filename_prefix is None:
        filename_prefix = Path(src_path).stem
    if extension is None:
        extension = Path(src_path).suffix
    _move_to_folder(
        src=src_path,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=lambda name: get_exception_path(
            name,
            base_dir=base_dir,
            id_separator=id_separator,
        ),
        log_message="Moved '{}' to exceptions folder at '{}'",
        log_level=logging.WARNING,
    )


def move_to_rename_folder(
    src: str,
    filename_prefix: str,
    extension: str = "",
    *,
    base_dir: str | None = None,
    id_separator: str | None = None,
) -> None:
    """Move an item to the rename folder (unique path)."""
    if base_dir is None:
        raise ValueError("base_dir must be provided explicitly")
    _move_to_folder(
        src=src,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=lambda name: get_rename_path(
            name,
            base_dir=base_dir,
            id_separator=id_separator,
        ),
        log_message="Moved '{}' to rename folder at '{}'",
        log_level=logging.INFO,
    )


def move_to_record_folder(
    src: str,
    filename_prefix: str,
    extension: str = "",
    *,
    id_separator: str | None = None,
    dest_dir: str | Path | None = None,
    current_device=None,
) -> None:
    """Move an item to the computed record folder (unique filename)."""
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")
    if dest_dir is None:
        raise ValueError("dest_dir must be provided explicitly")
    _move_to_folder(
        src=src,
        filename_prefix=filename_prefix,
        extension=extension,
        unique_path_func=lambda name: get_record_path(
            name,
            id_separator=id_separator,
            dest_dir=dest_dir,
            current_device=current_device,
        ),
        log_message="Moved '{}' to record folder for '{}'",
        log_level=logging.INFO,
    )


def load_persisted_records(
    *,
    json_path: str | Path | None = None,
    id_separator: str | None = None,
) -> dict[str, LocalRecord]:
    """Load persisted daily records from JSON into LocalRecord instances."""

    from dpost.domain.records.local_record import LocalRecord

    if json_path is None:
        raise ValueError("json_path must be provided explicitly")
    if not id_separator:
        raise ValueError("id_separator must be provided explicitly")
    path = Path(json_path)
    if not path.exists():
        return {}
    try:
        raw_data = path.read_text(encoding="utf-8")
        records = json.loads(raw_data)
        logger.debug(f"JSON data loaded from '{path}'.")
        return {
            record_id: LocalRecord.from_dict(record_data, id_separator=id_separator)
            for record_id, record_data in records.items()
        }
    except Exception as exc:
        logger.exception(f"Failed to read or convert JSON file '{path}': {exc}")
        return {}


def save_persisted_records(
    daily_records_dict: dict[str, LocalRecord],
    *,
    json_path: str | Path | None = None,
):
    """Serialize LocalRecord mapping to JSON for day-level persistence."""
    if json_path is None:
        raise ValueError("json_path must be provided explicitly")
    path = Path(json_path)
    try:
        serialized = json.dumps(
            {key: record.to_dict() for key, record in daily_records_dict.items()},
            indent=4,
        )
        path.write_text(serialized, encoding="utf-8")
        logger.debug(f"JSON data saved to '{path}'.")
    except Exception as exc:
        logger.exception(f"Failed to write JSON file '{path}': {exc}")
