---
id: application/startup/settings_schema.py
origin_v1_files:
  - src/dpost/application/config/schema.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Typed schema declarations including NamingSettings and validation rules.

## Origin Gist
- Source mapping: `src/dpost/application/config/schema.py`.
- Legacy gist: Holds typed startup and naming schema definitions.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Typed schema declarations including NamingSettings and validation rules.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Canonical field definitions for startup/runtime configuration keys.
- Allowed value sets and constraints for mode, profile, naming policy, and retry knobs.
- Default values and deprecation aliases for legacy config keys.
- Optional schema version tag for forward compatibility checks.

## Outputs
- Schema model declarations for all startup setting groups.
- Field-level validators and cross-field validators.
- Typed validation error objects including path, code, and remediation hint.
- Schema-to-documentation map used by startup diagnostics/help output.

## Invariants
- Every public startup field is defined in exactly one schema owner.
- Required/optional/default semantics are explicit and deterministic.
- Cross-field validation rules are pure and side-effect free.
- Schema validation does not depend on infrastructure adapter availability.

## Failure Modes
- Unknown required field omission yields `SettingsSchemaMissingFieldError`.
- Invalid enum literal yields `SettingsSchemaValueError`.
- Cross-field contradiction yields `SettingsSchemaConstraintError`.
- Deprecated key collision with canonical key yields `SettingsSchemaAliasError`.

## Pseudocode
1. Declare typed schema structures for runtime, naming, ingestion, sync, and UI settings groups.
2. Register per-field validators for enum values, ranges, and path token shape.
3. Register cross-field validators (for example mode-to-ui compatibility, retry cap consistency).
4. Implement `validate_raw_settings(raw)` returning either typed schema object or aggregated validation errors.
5. Implement alias normalization so legacy keys map to canonical names before final validation.
6. Expose machine-readable error codes consumed by settings service and bootstrap failure reporting.

## Tests To Implement
- unit: schema catches missing required fields, invalid enums, and cross-field contradictions with stable error codes.
- integration: settings service uses schema validation output to reject invalid startup config before dependency resolution begins.



