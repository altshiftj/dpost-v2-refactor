"""Unit coverage for domain text decoding fallback policy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from dpost.domain.processing.text import read_text_prefix


def test_read_text_prefix_respects_bytes_limit(local_tmp_path: Path) -> None:
    """Decode only the requested leading bytes from the input file."""
    path = local_tmp_path / "prefix.txt"
    path.write_text("abcdef", encoding="utf-8")

    result = read_text_prefix(path, bytes_limit=3, encodings=("utf-8",))

    assert result == "abc"


def test_read_text_prefix_uses_next_encoding_when_primary_fails(
    local_tmp_path: Path,
) -> None:
    """Try later encodings when strict decode fails on the first option."""
    path = local_tmp_path / "sample.bin"
    path.write_bytes(b"\xffABC")
    logger = Mock()

    result = read_text_prefix(
        path,
        encodings=("utf-8", "latin-1"),
        errors="strict",
        logger=logger,
        log_label="decoder",
    )

    assert result == "ÿABC"
    logger.debug.assert_called_once()
    debug_args = logger.debug.call_args[0]
    assert debug_args[1] == "decoder"
    assert debug_args[2] == "latin-1"


def test_read_text_prefix_uses_fallback_encoding_when_all_candidates_fail(
    local_tmp_path: Path,
) -> None:
    """Decode with explicit fallback when configured encodings all fail."""
    path = local_tmp_path / "fallback.bin"
    path.write_bytes(b"\xff")
    logger = Mock()

    result = read_text_prefix(
        path,
        encodings=("invalid-encoding",),
        fallback_encoding="latin-1",
        fallback_errors="strict",
        logger=logger,
        log_label="decoder",
    )

    assert result == "ÿ"
    logger.debug.assert_called_once()
    debug_args = logger.debug.call_args[0]
    assert "fallback encoding" in debug_args[0]
    assert debug_args[1] == "decoder"
    assert debug_args[2] == "latin-1"


def test_read_text_prefix_defaults_to_utf8_with_resolved_errors(
    local_tmp_path: Path,
) -> None:
    """Use default decode path when no explicit fallback encoding is provided."""
    path = local_tmp_path / "default.bin"
    path.write_bytes(b"\xffabc")

    result = read_text_prefix(
        path,
        encodings=("invalid-encoding",),
        errors="ignore",
        fallback_encoding=None,
    )

    assert result == "abc"


def test_read_text_prefix_omits_errors_kwarg_when_errors_is_none(
    local_tmp_path: Path,
) -> None:
    """Decode with codec defaults when explicit errors handling is disabled."""
    path = local_tmp_path / "codec-defaults.bin"
    path.write_bytes(b"\xffABC")

    result = read_text_prefix(
        path,
        encodings=("latin-1",),
        errors=None,
    )

    assert result == "ÿABC"
