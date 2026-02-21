"""Pure domain helpers for filename parsing and record/file identifier policy."""

from __future__ import annotations

from pathlib import Path


def parse_filename(src_path: str) -> tuple[str, str]:
    """Return filename stem and suffix for a path-like string."""
    path = Path(src_path)
    return path.stem, path.suffix


def generate_record_id(
    filename_prefix: str, *, dev_kadi_record_id: str, id_separator: str
) -> str:
    """Compose canonical record identifier from record prefix and naming settings."""
    return f"{dev_kadi_record_id}{id_separator}{filename_prefix}".lower()


def generate_file_id(
    filename_prefix: str, *, device_abbr: str, id_separator: str
) -> str:
    """Compose canonical file identifier from record prefix and naming settings."""
    parts = filename_prefix.split(id_separator)
    if len(parts) < 3:
        raise ValueError(
            f"Filename prefix '{filename_prefix}' does not contain three segments."
        )
    sample_id = id_separator.join(parts[2:])
    return f"{device_abbr}{id_separator}{sample_id}"
