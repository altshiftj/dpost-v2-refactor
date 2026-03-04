---
id: domain/naming/policy.py
origin_v1_files:
  - src/dpost/application/naming/policy.py
lane: Domain-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Canonical naming composition (pattern + separator + explicit shape).

## Origin Gist
- Source mapping: `src/dpost/application/naming/policy.py`.
- Legacy gist: Consolidates naming policy logic in pure domain naming package.

## V2 Improvement Intent
- Transform posture: Merge.
- Target responsibility: Canonical naming composition (pattern + separator + explicit shape).
- Improvement goal: Consolidate duplicated logic into a single canonical owner.
## Inputs
- Naming pattern template (ordered segments and separators).
- Parsed identifier tokens and derived prefix token.
- Domain context tokens (timestamp token, batch token, route token).
- Naming constraints (max length, allowed characters, required segments).

## Outputs
- Canonical name composition result with filename stem and segment breakdown.
- Validation diagnostics for rejected naming attempts.
- Optional normalized alternate representation used in collision handling logic.
- Deterministic hashing helper for name identity checks.

## Invariants
- Segment order and separator use always follow template definition.
- Composed name contains only allowed characters and required segments.
- Composition is deterministic for identical inputs.
- Example: template `prefix+id+date` always yields the same segment order for same tokens.
- Counterexample: missing required `id` segment causes composition rejection.

## Failure Modes
- Missing required segment token raises `NamingMissingSegmentError`.
- Segment value violating character/length constraints raises `NamingSegmentValidationError`.
- Template with unknown segment placeholder raises `NamingTemplateError`.
- Result exceeding max length without legal truncation strategy raises `NamingLengthError`.

## Pseudocode
1. Validate naming template structure and required segment definitions.
2. Assemble segment map from prefix policy output, identifier tokens, and contextual tokens.
3. Ensure required segments are present and each segment value passes constraints.
4. Compose canonical name by joining template-ordered segments with configured separators.
5. Validate final composed name length/character constraints.
6. Return composition result with segment diagnostics and stable identity hash.

## Tests To Implement
- unit: template ordering, required segment enforcement, deterministic composition, and length/character rejection.
- integration: route stage naming integration composes stable names for identical domain inputs and rejects invalid segment sets.



