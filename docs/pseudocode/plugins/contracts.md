---
id: plugins/contracts.py
origin_v1_files:
  - src/dpost/plugins/contracts.py
lane: Plugin-Host
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Plugin-facing contract aliases/re-exports for adapter packages.

## Origin Gist
- Source mapping: `src/dpost/plugins/contracts.py`.
- Legacy gist: Promotes plugin contract model to contract-first application boundary.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Plugin-facing contract aliases/re-exports for adapter packages.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Canonical application contract symbols (`plugin_contracts`, `context`, `events`).
- Plugin compatibility/version policy.
- Optional deprecated alias map for transition period.
- Type-only metadata for plugin authoring ergonomics.

## Outputs
- Stable plugin-facing alias exports for required contract types.
- Contract version constant used by plugin compatibility checks.
- Compatibility helpers for validating plugin-declared contract version.
- Typed contract compatibility errors.

## Invariants
- This module contains aliases/re-exports only (no runtime side effects).
- Exported names remain stable across compatible minor versions.
- Deprecated aliases map to canonical names until explicitly retired.
- Plugin template docs rely on these exports as authoritative contract surface.

## Failure Modes
- Missing upstream contract symbol raises `PluginContractsImportError`.
- Version mismatch between plugin and host raises `PluginContractVersionError`.
- Deprecated alias conflict raises `PluginContractAliasConflictError`.
- Invalid compatibility declaration shape raises `PluginContractMetadataError`.

## Pseudocode
1. Import canonical contract symbols from `application.contracts` modules.
2. Re-export plugin-author-facing aliases with stable naming.
3. Define contract version constant and compatibility checker helper.
4. Optionally expose deprecated aliases with explicit deprecation metadata.
5. Validate alias table consistency at module load.
6. Surface typed errors for compatibility/version failures used by host/discovery.

## Tests To Implement
- unit: alias export completeness, version compatibility checks, and deprecated alias conflict detection.
- integration: plugin host validates template plugins against re-exported contract version and rejects incompatible plugin declarations.



