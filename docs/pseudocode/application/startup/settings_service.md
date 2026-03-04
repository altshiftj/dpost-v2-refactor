---
id: application/startup/settings_service.py
origin_v1_files:
  - src/dpost/application/config/service.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Load/merge settings sources and expose validated settings object.

## Origin Gist
- Source mapping: `src/dpost/application/config/service.py`.
- Legacy gist: Owns validated settings loading and lifecycle API.

## V2 Improvement Intent
- Transform posture: Rename.
- Target responsibility: Load/merge settings sources and expose validated settings object.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Ordered settings sources: defaults, config file, environment, CLI overrides.
- Schema validator from `settings_schema`.
- Normalization helpers from `settings`.
- Optional in-memory cache handle for repeated bootstrap calls in one process.

## Outputs
- Validated `StartupSettings` object.
- Source provenance metadata showing which layer set each final key.
- Redacted diagnostics payload for startup logs.
- Stable error result for parse/merge/validation failures.

## Invariants
- Source precedence is deterministic: defaults < file < environment < CLI.
- Merge operation is pure for provided inputs; no hidden global state.
- Cached settings may be reused only if source fingerprint is unchanged.
- Service never silently drops unknown keys; it reports them via schema errors.

## Failure Modes
- Config file read/parse failures raise `SettingsSourceReadError`.
- Schema validation failures raise `SettingsValidationError` with field-level details.
- Merge conflicts in incompatible types raise `SettingsMergeTypeError`.
- Cache desynchronization detection raises `SettingsCacheIntegrityError` and forces reload.

## Pseudocode
1. Resolve active source list from bootstrap request and read each source into raw dictionaries.
2. Merge dictionaries by precedence while capturing provenance per key.
3. Pass merged payload through schema validation and normalization helpers.
4. Build immutable `StartupSettings` and optional redacted diagnostics snapshot.
5. Store/reuse cache entry keyed by source fingerprint when cache is enabled.
6. Return typed success/failure result consumed by bootstrap orchestration.

## Tests To Implement
- unit: precedence ordering, provenance tracking, validation failures, and cache fingerprint behavior.
- integration: bootstrap consumes service output and aborts launch on typed settings errors with deterministic messages.



