---
id: domain/naming/identifiers.py
origin_v1_files:
  - src/dpost/domain/naming/identifiers.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Parse/format artifact identifiers and separator-aware tokenization.

## Origin Gist
- Source mapping: `src/dpost/domain/naming/identifiers.py`.
- Legacy gist: Retains pure naming rule module identifiers.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Parse/format artifact identifiers and separator-aware tokenization.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Raw identifier strings from naming/routing domain contexts.
- Separator configuration (primary separator, alternate accepted separators).
- Token rules (allowed characters, min/max token length, required token count).
- Optional normalization policy (case-folding, whitespace trimming).

## Outputs
- `ParsedIdentifier` domain model (ordered tokens + canonical normalized string).
- Composition helper that builds canonical identifier strings from token lists.
- Validation result object with reason codes for invalid identifiers.
- Round-trip helpers used by naming policy logic.

## Invariants
- Parsing then composing preserves canonical representation (`compose(parse(x)) == canonical(x)`).
- Tokens are non-empty and satisfy configured character constraints.
- Token ordering is preserved through parse/compose operations.
- Example: `MAT-DEVICE-20260304` parses into three tokens and composes back identically.
- Counterexample: `MAT--20260304` contains an empty token and is rejected.

## Failure Modes
- Empty input identifier raises `IdentifierEmptyError`.
- Illegal character in any token raises `IdentifierCharacterError`.
- Token count outside allowed bounds raises `IdentifierTokenCountError`.
- Unknown separator configuration raises `IdentifierSeparatorError`.

## Pseudocode
1. Normalize raw identifier string according to case/whitespace policy.
2. Split string using accepted separators and filter/validate token list shape.
3. Validate each token against character and length constraints.
4. Build `ParsedIdentifier` with ordered tokens and canonical separator form.
5. Implement `compose_identifier(tokens)` that validates then joins tokens deterministically.
6. Return typed validation errors for any failed step.

## Tests To Implement
- unit: separator-aware parsing, round-trip composition invariant, and token validation errors.
- integration: naming policy consumes parsed identifiers and composes canonical names without depending on infrastructure behavior.



