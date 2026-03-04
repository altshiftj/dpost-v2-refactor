---
id: domain/processing/text.py
origin_v1_files:
  - src/dpost/domain/processing/text.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Text parsing/normalization helpers used by processors.

## Origin Gist
- Source mapping: `src/dpost/domain/processing/text.py`.
- Legacy gist: Retains processing domain model or policy text.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Text parsing/normalization helpers used by processors.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Raw text payload and optional line iterator.
- Parse options (delimiter, quote character, decimal separator, encoding hints).
- Normalization policy (trim rules, case rules, whitespace collapsing).
- Field-shape expectations (column counts, required header tokens).

## Outputs
- Normalized text record model (header + row tokens).
- Parsing/normalization result with warnings for recoverable anomalies.
- Helper functions for token cleanup and numeric-safe normalization.
- Typed domain parsing errors for malformed inputs.

## Invariants
- Normalization is idempotent: applying normalization twice yields identical output.
- Output rows preserve original order.
- Required header fields must exist before row parsing succeeds.
- Example: trimming surrounding spaces around tokens yields stable output on repeated calls.
- Counterexample: row with unclosed quote delimiter is invalid.

## Failure Modes
- Unsupported/unknown encoding hint raises `TextEncodingError`.
- Malformed delimiter/quote structure raises `TextParseStructureError`.
- Missing required header token raises `TextHeaderValidationError`.
- Inconsistent row column count under strict mode raises `TextRowShapeError`.

## Pseudocode
1. Decode or accept raw text input according to parse options.
2. Parse header and rows using configured delimiter/quote semantics.
3. Validate required headers and row shape constraints.
4. Normalize each token according to normalization policy.
5. Build immutable normalized text record model preserving row order.
6. Return warnings/errors using typed parsing result model.

## Tests To Implement
- unit: idempotent normalization, header validation, malformed quote detection, and strict row-shape checks.
- integration: plugin processor logic reuses text domain helpers and receives deterministic tokenized outputs for equivalent raw inputs.



