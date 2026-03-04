---
id: plugins/pcs/_pc_template/settings.py
origin_v1_files:
  - src/dpost/pc_plugins/kinexus_blb/settings.py
  - src/dpost/pc_plugins/haake_blb/settings.py
  - src/dpost/pc_plugins/zwick_blb/settings.py
  - src/dpost/pc_plugins/tischrem_blb/settings.py
  - src/dpost/pc_plugins/eirich_blb/settings.py
  - src/dpost/pc_plugins/horiba_blb/settings.py
  - src/dpost/pc_plugins/test_pc/settings.py
  - src/dpost/pc_plugins/hioki_blb/settings.py
lane: Plugin-PC
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- PC plugin typed settings and upload/sync config defaults.

## Origin Gist
- Source mapping: template derived from 8 PC-plugin origin files.
- Legacy gist: Keeps PC plugin module settings.py for kinexus_blb. Keeps PC plugin module settings.py for haake_blb. (plus similar related variants).

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: PC plugin typed settings and upload/sync config defaults.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Raw PC plugin configuration payload.
- Template defaults for endpoint, workspace, upload behavior, and retry knobs.
- Validation schema constraints for sync credentials/targets/options.
- Optional profile-based overrides.

## Outputs
- Typed `PcPluginSettings` model.
- Normalized sync/upload configuration for PC plugin runtime hooks.
- Redacted diagnostics view that excludes secret fields.
- Field-level validation errors for host activation gating.

## Invariants
- Required sync target fields are present before activation.
- Secrets/credentials are never emitted in plain diagnostics payloads.
- Defaults and overrides apply in deterministic precedence order.
- Settings object is immutable after successful validation.

## Failure Modes
- Missing required endpoint/target keys raises `PcPluginSettingsMissingKeyError`.
- Invalid endpoint/credential format raises `PcPluginSettingsValidationError`.
- Unsupported upload mode token raises `PcPluginSettingsModeError`.
- Override conflict or strict unknown key raises `PcPluginSettingsOverrideError`.

## Pseudocode
1. Define typed schema for PC plugin sync/upload settings and defaults.
2. Merge defaults, raw config, and profile overrides according to precedence.
3. Validate endpoints, identifiers, credentials placeholders, and mode tokens.
4. Normalize resulting values into canonical settings model for plugin hooks.
5. Build redacted diagnostics representation that strips secret material.
6. Return immutable `PcPluginSettings` or typed validation/override errors.

## Tests To Implement
- unit: default/override precedence, endpoint/mode validation, secret redaction, and strict unknown-key handling.
- integration: PC plugin activation validates settings and supplies normalized sync configuration to immediate/deferred sync hooks.



