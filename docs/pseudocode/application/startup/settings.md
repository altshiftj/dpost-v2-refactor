---
id: application/startup/settings.py
origin_v1_files:
  - src/dpost/runtime/startup_config.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Startup settings model and normalization helpers.

## Origin Gist
- Source mapping: `src/dpost/runtime/startup_config.py`.
- Legacy gist: Centralizes startup settings parsing and validation.

## V2 Improvement Intent
- Transform posture: Split.
- Target responsibility: Startup settings model and normalization helpers.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership.
## Inputs
- Raw config payload assembled from defaults, file config, env, and CLI overrides.
- Schema-level defaults from `settings_schema`.
- Optional profile presets selected by runtime mode/profile.
- Path root hints used to normalize relative filesystem values.

## Outputs
- Typed `StartupSettings` aggregate model.
- Typed nested settings subsets (naming, ingestion, sync, ui/runtime toggles).
- Pure normalization helpers (`normalize_mode`, `normalize_paths`, `normalize_retry_policy`).
- Redacted settings snapshot for logging without secrets.

## Invariants
- Mode/profile tokens are normalized to canonical lowercase identifiers.
- Numeric knobs (timeouts, retry caps, debounce windows) are bounded and non-negative.
- Paths stored in settings are normalized to absolute platform-safe paths.
- Settings model remains side-effect free and does not read environment directly.

## Failure Modes
- Unsupported mode/profile values raise `SettingsNormalizationError`.
- Path normalization failures raise `SettingsPathError`.
- Numeric bound violations raise `SettingsRangeError`.
- Missing required nested blocks after merge raise `SettingsShapeError`.

## Pseudocode
1. Define typed settings dataclasses for runtime, naming, ingestion, sync, and ui concerns.
2. Implement `from_raw(raw_config)` that applies schema defaults and normalizes primitive tokens.
3. Normalize filesystem paths against configured root and convert to canonical string form.
4. Normalize mode/profile aliases and enforce allowed combinations.
5. Validate numeric bounds and cross-field constraints, then return immutable `StartupSettings`.
6. Provide `to_redacted_dict(settings)` for safe diagnostics output.

## Tests To Implement
- unit: normalization canonicalizes mode/profile tokens, rejects invalid ranges, and produces absolute normalized paths.
- integration: settings service merge output becomes a valid `StartupSettings` consumed unchanged by bootstrap and composition.



