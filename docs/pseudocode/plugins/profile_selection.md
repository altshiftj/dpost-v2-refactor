---
id: plugins/profile_selection.py
origin_v1_files:
  - src/dpost/plugins/profile_selection.py
lane: Plugin-Host
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Profile-to-enabled-plugin resolution policy.

## Origin Gist
- Source mapping: `src/dpost/plugins/profile_selection.py`.
- Legacy gist: Retains profile-based plugin selection logic.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Profile-to-enabled-plugin resolution policy.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Active runtime profile token and optional mode token.
- Plugin catalog metadata (capabilities, profile tags, enabled-by-default flags).
- Profile selection policy rules (include/exclude overrides).
- Optional operator overrides for temporary enable/disable lists.

## Outputs
- Selected plugin id sets by family (`device`, `pc`) for active profile.
- Selection diagnostics (included, excluded, reason codes).
- Typed policy errors for unknown profiles or conflicting overrides.
- Stable selection fingerprint for caching.

## Invariants
- Selection is deterministic for identical profile + catalog + policy inputs.
- Disabled/blocked plugins are never selected even if profile-tagged.
- Override precedence is explicit and stable (`deny` before `allow`).
- Selected plugin ids must exist in catalog snapshot.

## Failure Modes
- Unknown profile token raises `PluginProfileUnknownError`.
- Conflicting allow/deny overrides raise `PluginProfileOverrideConflictError`.
- Selection references missing plugin id raises `PluginProfileCatalogMismatchError`.
- Invalid policy rule shape raises `PluginProfilePolicyError`.

## Pseudocode
1. Load active profile policy and validate profile token against known profiles.
2. Filter catalog plugins by family/capability/profile-tag compatibility.
3. Apply override precedence rules (deny list, then allow list, then defaults).
4. Validate resulting plugin ids all exist and satisfy required capabilities.
5. Produce deterministic sorted plugin id sets and diagnostics.
6. Return selection result plus fingerprint used by host activation cache.

## Tests To Implement
- unit: deterministic filtering, override precedence behavior, and unknown-profile/conflict handling.
- integration: host activation uses profile selection output to enable correct plugin subsets in multiple runtime profiles.



