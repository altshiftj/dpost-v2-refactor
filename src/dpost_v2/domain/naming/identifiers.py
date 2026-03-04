"""Identifier parsing/composition rules for V2 naming domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


class IdentifierError(ValueError):
    """Base class for identifier-domain validation errors."""


class IdentifierEmptyError(IdentifierError):
    """Raised when an identifier input is empty after normalization."""


class IdentifierSeparatorError(IdentifierError):
    """Raised when separator configuration is invalid."""


class IdentifierTokenCountError(IdentifierError):
    """Raised when identifier token count is outside configured bounds."""


class IdentifierCharacterError(IdentifierError):
    """Raised when token characters violate configured constraints."""


@dataclass(frozen=True)
class IdentifierRules:
    """Configuration for parsing and composing canonical identifiers."""

    primary_separator: str = "-"
    alternate_separators: tuple[str, ...] = ()
    token_pattern: str = r"[A-Za-z0-9_]+"
    min_tokens: int = 1
    max_tokens: int | None = None
    min_token_length: int = 1
    max_token_length: int | None = None
    casefold: bool = False
    strip_whitespace: bool = True


@dataclass(frozen=True)
class ParsedIdentifier:
    """Normalized identifier with ordered token sequence and canonical form."""

    tokens: tuple[str, ...]
    canonical: str
    separator: str


@dataclass(frozen=True)
class IdentifierValidation:
    """Structured validation output for non-raising validation calls."""

    valid: bool
    reason: str | None = None
    error_type: str | None = None


def _normalized_token(token: str, rules: IdentifierRules) -> str:
    value = token.strip() if rules.strip_whitespace else token
    if rules.casefold:
        value = value.casefold()
    return value


def _normalized_text(value: str, rules: IdentifierRules) -> str:
    text = value.strip() if rules.strip_whitespace else value
    if rules.casefold:
        text = text.casefold()
    return text


def _validate_separator_rules(rules: IdentifierRules) -> None:
    primary = rules.primary_separator
    if not primary or primary.isspace():
        raise IdentifierSeparatorError("Primary separator must be non-empty.")

    alternates = set()
    for separator in rules.alternate_separators:
        if not separator or separator.isspace():
            raise IdentifierSeparatorError("Alternate separators must be non-empty.")
        if separator == primary:
            raise IdentifierSeparatorError(
                "Primary separator cannot also appear in alternate separators.",
            )
        if separator in alternates:
            raise IdentifierSeparatorError(
                "Alternate separators must be unique.",
            )
        alternates.add(separator)

    if rules.min_tokens < 1:
        raise IdentifierTokenCountError("Minimum token count must be >= 1.")
    if rules.max_tokens is not None and rules.max_tokens < rules.min_tokens:
        raise IdentifierTokenCountError(
            "Maximum token count must be >= minimum token count.",
        )


def _split_tokens(raw: str, rules: IdentifierRules) -> tuple[str, ...]:
    separators = (rules.primary_separator, *rules.alternate_separators)
    pattern = "|".join(re.escape(separator) for separator in separators)
    raw_tokens = re.split(pattern, raw) if pattern else [raw]
    if any(token == "" for token in raw_tokens):
        raise IdentifierTokenCountError("Identifier token count contains empty tokens.")
    tokens = tuple(_normalized_token(token, rules) for token in raw_tokens)
    return tokens


def _validate_tokens(tokens: Sequence[str], rules: IdentifierRules) -> tuple[str, ...]:
    token_count = len(tokens)
    if token_count < rules.min_tokens:
        raise IdentifierTokenCountError(
            "Identifier token count is below configured minimum token count.",
        )
    if rules.max_tokens is not None and token_count > rules.max_tokens:
        raise IdentifierTokenCountError(
            "Identifier token count exceeds configured maximum token count.",
        )

    compiled_pattern = re.compile(rules.token_pattern)
    normalized: list[str] = []
    for token in tokens:
        if len(token) < rules.min_token_length:
            raise IdentifierCharacterError("Identifier token is shorter than allowed.")
        if rules.max_token_length is not None and len(token) > rules.max_token_length:
            raise IdentifierCharacterError("Identifier token is longer than allowed.")
        if not compiled_pattern.fullmatch(token):
            raise IdentifierCharacterError(
                f"Identifier token '{token}' contains invalid characters.",
            )
        normalized.append(token)
    return tuple(normalized)


def parse_identifier(raw_identifier: str, *, rules: IdentifierRules) -> ParsedIdentifier:
    """Parse raw identifier string into canonical ordered token representation."""
    _validate_separator_rules(rules)
    normalized = _normalized_text(raw_identifier, rules)
    if not normalized:
        raise IdentifierEmptyError("Identifier input is empty.")

    tokens = _split_tokens(normalized, rules)
    valid_tokens = _validate_tokens(tokens, rules)
    canonical = rules.primary_separator.join(valid_tokens)
    return ParsedIdentifier(
        tokens=valid_tokens,
        canonical=canonical,
        separator=rules.primary_separator,
    )


def compose_identifier(tokens: Sequence[str], *, rules: IdentifierRules) -> str:
    """Compose canonical identifier string from ordered tokens."""
    _validate_separator_rules(rules)
    normalized_tokens = tuple(_normalized_token(token, rules) for token in tokens)
    valid_tokens = _validate_tokens(normalized_tokens, rules)
    return rules.primary_separator.join(valid_tokens)


def validate_identifier(raw_identifier: str, *, rules: IdentifierRules) -> IdentifierValidation:
    """Validate identifier input without raising typed domain errors to callers."""
    try:
        parse_identifier(raw_identifier, rules=rules)
    except IdentifierError as exc:
        return IdentifierValidation(
            valid=False,
            reason=str(exc),
            error_type=type(exc).__name__,
        )
    return IdentifierValidation(valid=True, reason=None, error_type=None)

