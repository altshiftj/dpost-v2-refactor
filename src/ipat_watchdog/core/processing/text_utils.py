"""Text decoding helpers for preprocessing."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def read_text_prefix(
    path: Path,
    bytes_limit: int = 4096,
    *,
    encodings: Iterable[str],
    errors: str | None = "ignore",
    fallback_encoding: str | None = None,
    fallback_errors: str | None = None,
    logger=None,
    log_label: str | None = None,
) -> str:
    """Read and decode a file prefix with configurable encoding fallbacks."""
    raw = path.read_bytes()[:bytes_limit]
    for enc in encodings:
        try:
            if errors is None:
                text = raw.decode(enc)
            else:
                text = raw.decode(enc, errors=errors)
            if logger is not None and log_label:
                logger.debug(
                    "%s: read_text_prefix used encoding=%s for %s", log_label, enc, path
                )
            return text
        except UnicodeDecodeError:
            continue
        except Exception:
            continue

    if fallback_encoding is None:
        return raw.decode(errors=fallback_errors or errors or "ignore")

    resolved_errors = fallback_errors or errors or "ignore"
    text = raw.decode(fallback_encoding, errors=resolved_errors)
    if logger is not None and log_label:
        logger.debug(
            "%s: read_text_prefix fallback encoding=%s(%s) for %s",
            log_label,
            fallback_encoding,
            resolved_errors,
            path,
        )
    return text
