"""Text parsing and normalization helpers for V2 processing domain."""

from __future__ import annotations

import codecs
import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Sequence


class TextModelError(ValueError):
    """Base class for text parsing/normalization domain errors."""


class TextEncodingError(TextModelError):
    """Raised when payload cannot be decoded using configured encoding hints."""


class TextParseStructureError(TextModelError):
    """Raised when delimiter/quote structure is malformed."""


class TextHeaderValidationError(TextModelError):
    """Raised when required header tokens are missing."""


class TextRowShapeError(TextModelError):
    """Raised when strict row shape constraints are violated."""


@dataclass(frozen=True)
class TextNormalizationPolicy:
    """Normalization policy for header and cell token cleanup."""

    trim_tokens: bool = True
    collapse_internal_whitespace: bool = True
    casefold_tokens: bool = False


@dataclass(frozen=True)
class TextParseOptions:
    """Parsing options for delimiter/encoding/header/shape behavior."""

    delimiter: str = ","
    quote_character: str = '"'
    encoding_hints: tuple[str, ...] = ("utf-8",)
    strict_row_shape: bool = True
    required_headers: tuple[str, ...] = ()
    normalization: TextNormalizationPolicy = field(default_factory=TextNormalizationPolicy)


@dataclass(frozen=True)
class NormalizedTextRecord:
    """Normalized text representation with optional non-fatal warnings."""

    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    warnings: tuple[str, ...] = ()


def normalize_token(token: str, *, policy: TextNormalizationPolicy) -> str:
    """Normalize token according to trim/case/whitespace policy."""
    value = token.strip() if policy.trim_tokens else token
    if policy.collapse_internal_whitespace:
        value = " ".join(value.split())
    if policy.casefold_tokens:
        value = value.casefold()
    return value


def _decode_payload(
    payload: str | bytes,
    *,
    encoding_hints: Sequence[str],
) -> str:
    if isinstance(payload, str):
        return payload

    for encoding in encoding_hints:
        try:
            codecs.lookup(encoding)
        except LookupError as exc:
            raise TextEncodingError(f"Unknown encoding hint '{encoding}'.") from exc

    for encoding in encoding_hints:
        try:
            return payload.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
    raise TextEncodingError("Unable to decode payload using configured encoding hints.")


def _parse_rows(
    text: str,
    *,
    delimiter: str,
    quote_character: str,
) -> list[list[str]]:
    reader = csv.reader(
        StringIO(text),
        delimiter=delimiter,
        quotechar=quote_character,
        strict=True,
    )
    try:
        return [list(row) for row in reader]
    except csv.Error as exc:
        raise TextParseStructureError("Malformed delimiter/quote structure.") from exc


def parse_text_records(
    payload: str | bytes,
    *,
    options: TextParseOptions,
) -> NormalizedTextRecord:
    """Parse and normalize delimited text into immutable domain structure."""
    decoded = _decode_payload(payload, encoding_hints=options.encoding_hints)
    parsed_rows = _parse_rows(
        decoded,
        delimiter=options.delimiter,
        quote_character=options.quote_character,
    )
    if not parsed_rows:
        header: tuple[str, ...] = ()
        data_rows: list[list[str]] = []
    else:
        header = tuple(
            normalize_token(token, policy=options.normalization) for token in parsed_rows[0]
        )
        data_rows = parsed_rows[1:]

    required_headers = {
        normalize_token(token, policy=options.normalization)
        for token in options.required_headers
    }
    missing = sorted(required_headers.difference(set(header)))
    if missing:
        raise TextHeaderValidationError(
            f"Missing required header token(s): {', '.join(missing)}.",
        )

    normalized_rows: list[tuple[str, ...]] = []
    warnings: list[str] = []
    expected_columns = len(header)
    for row_index, row in enumerate(data_rows, start=2):
        normalized_row = tuple(
            normalize_token(token, policy=options.normalization) for token in row
        )
        if options.strict_row_shape and expected_columns and len(normalized_row) != expected_columns:
            raise TextRowShapeError(
                f"Row {row_index} has {len(normalized_row)} column(s), expected {expected_columns}.",
            )
        if not options.strict_row_shape and expected_columns and len(normalized_row) != expected_columns:
            warnings.append(
                f"Row {row_index} column count {len(normalized_row)} differs from expected {expected_columns}.",
            )
        normalized_rows.append(normalized_row)

    return NormalizedTextRecord(
        header=header,
        rows=tuple(normalized_rows),
        warnings=tuple(warnings),
    )

