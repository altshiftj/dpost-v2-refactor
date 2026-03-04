"""Naming domain contracts for V2."""

from dpost_v2.domain.naming.identifiers import (
    IdentifierCharacterError,
    IdentifierEmptyError,
    IdentifierRules,
    IdentifierSeparatorError,
    IdentifierTokenCountError,
    IdentifierValidation,
    ParsedIdentifier,
    compose_identifier,
    parse_identifier,
    validate_identifier,
)
from dpost_v2.domain.naming.policy import (
    NamingCompositionResult,
    NamingConstraints,
    NamingLengthError,
    NamingMissingSegmentError,
    NamingSegmentValidationError,
    NamingTemplate,
    NamingTemplateError,
    compose_name,
)
from dpost_v2.domain.naming.prefix_policy import (
    PrefixDecision,
    PrefixDecisionKind,
    PrefixDerivationNotFoundError,
    PrefixRule,
    PrefixRuleAmbiguityError,
    PrefixRuleConfigurationError,
    PrefixTokenFormatError,
    derive_prefix,
)

__all__ = [
    "IdentifierCharacterError",
    "IdentifierEmptyError",
    "IdentifierRules",
    "IdentifierSeparatorError",
    "IdentifierTokenCountError",
    "IdentifierValidation",
    "NamingCompositionResult",
    "NamingConstraints",
    "NamingLengthError",
    "NamingMissingSegmentError",
    "NamingSegmentValidationError",
    "NamingTemplate",
    "NamingTemplateError",
    "ParsedIdentifier",
    "PrefixDecision",
    "PrefixDecisionKind",
    "PrefixDerivationNotFoundError",
    "PrefixRule",
    "PrefixRuleAmbiguityError",
    "PrefixRuleConfigurationError",
    "PrefixTokenFormatError",
    "compose_identifier",
    "compose_name",
    "derive_prefix",
    "parse_identifier",
    "validate_identifier",
]

