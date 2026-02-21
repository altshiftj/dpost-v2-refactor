"""Pure domain policy for filename-prefix validation and normalization."""

from __future__ import annotations

import re
from typing import Pattern, TypedDict


class ValidationMessages:
    """Validation feedback when filenames or fields break naming conventions."""

    MISSING_SEPARATOR = "Filename must have exactly 3 parts separated by '-'."
    USER_ONLY_LETTERS = "User ID must contain only letters."
    INSTITUTE_ONLY_LETTERS = "Institute must contain only letters."
    SAMPLE_TOO_LONG = "Sample name must be 30 characters or fewer."
    SAMPLE_INVALID_CHARS = (
        "Sample may only contain letters, digits, underscores/spaces."
    )


class FilenameViolation(TypedDict):
    """Structured validation response for invalid filename analysis."""

    valid: bool
    reasons: list[str]
    highlight_spans: list[tuple[int, int]]


class UserInputAnalysis(TypedDict):
    """Structured validation response for rename dialog analysis."""

    valid: bool
    sanitized: str | None
    reasons: list[str]
    highlight_spans: list[tuple[int, int]]


def is_valid_prefix(
    raw_prefix: str, *, filename_pattern: Pattern[str], id_separator: str
) -> bool:
    """Return True when prefix matches policy pattern and segment shape."""
    if not filename_pattern.match(raw_prefix):
        return False
    return raw_prefix.count(id_separator) >= 2


def sanitize_prefix(raw_prefix: str, *, id_separator: str) -> str:
    """Normalize prefix fields with lowercase IDs and underscore sample spacing."""
    parts = raw_prefix.strip().split(id_separator)
    if len(parts) < 3:
        return raw_prefix
    user_id = parts[0].strip()
    institute = parts[1].strip()
    sample_id = id_separator.join(part.strip() for part in parts[2:]).replace(
        " ",
        "_",
    )
    return (
        f"{user_id.lower()}{id_separator}{institute.lower()}{id_separator}{sample_id}"
    )


def sanitize_and_validate(
    raw_prefix: str, *, filename_pattern: Pattern[str], id_separator: str
) -> tuple[str, bool]:
    """Return `(sanitized_prefix, is_valid)` for a raw prefix string."""
    if not is_valid_prefix(
        raw_prefix,
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    ):
        return raw_prefix, False
    return sanitize_prefix(raw_prefix, id_separator=id_separator), True


def explain_filename_violation(
    filename: str, *, filename_pattern: Pattern[str], id_separator: str
) -> FilenameViolation:
    """Analyze invalid filename input and provide reasons plus highlight spans."""
    result: FilenameViolation = {
        "valid": True,
        "reasons": [],
        "highlight_spans": [],
    }

    if filename_pattern.match(filename):
        return result

    result["valid"] = False
    segments = filename.split(id_separator)

    if len(segments) != 3:
        result["reasons"].append(ValidationMessages.MISSING_SEPARATOR)
        for index, char in enumerate(filename):
            if char == id_separator:
                result["highlight_spans"].append((index, index + 1))
        return result

    user, institute, sample = segments
    user_start = 0
    user_end = len(user)
    inst_start = user_end + 1
    inst_end = inst_start + len(institute)
    sample_start = inst_end + 1

    if not re.fullmatch(r"[A-Za-z]+", user):
        result["reasons"].append(ValidationMessages.USER_ONLY_LETTERS)
        for index, char in enumerate(user):
            if not re.match(r"[A-Za-z]", char):
                result["highlight_spans"].append(
                    (user_start + index, user_start + index + 1)
                )

    if not re.fullmatch(r"[A-Za-z]+", institute):
        result["reasons"].append(ValidationMessages.INSTITUTE_ONLY_LETTERS)
        for index, char in enumerate(institute):
            if not re.match(r"[A-Za-z]", char):
                result["highlight_spans"].append(
                    (inst_start + index, inst_start + index + 1)
                )

    if len(sample) > 30:
        result["reasons"].append(ValidationMessages.SAMPLE_TOO_LONG)

    if not re.fullmatch(r"^[A-Za-z0-9_ ]+", sample):
        result["reasons"].append(ValidationMessages.SAMPLE_INVALID_CHARS)
        for index, char in enumerate(sample):
            if not re.match(r"[A-Za-z0-9_ ]", char):
                result["highlight_spans"].append(
                    (sample_start + index, sample_start + index + 1)
                )

    return result


def analyze_user_input(
    dialog_result: dict | None, *, filename_pattern: Pattern[str], id_separator: str
) -> UserInputAnalysis:
    """Validate and sanitize rename dialog values using naming policy rules."""
    output: UserInputAnalysis = {
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
    raw_prefix = f"{user_id}{id_separator}{institute}{id_separator}{sample_id}"

    sanitized, is_valid = sanitize_and_validate(
        raw_prefix,
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )

    if is_valid:
        output["sanitized"] = sanitized
        return output

    output["valid"] = False
    violation_info = explain_filename_violation(
        raw_prefix,
        filename_pattern=filename_pattern,
        id_separator=id_separator,
    )
    output["reasons"].extend(violation_info["reasons"])
    output["highlight_spans"].extend(violation_info["highlight_spans"])
    return output
