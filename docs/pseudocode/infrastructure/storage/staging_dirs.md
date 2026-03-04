---
id: infrastructure/storage/staging_dirs.py
origin_v1_files:
  - src/dpost/infrastructure/storage/staging_dirs.py
lane: Infra-Storage
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Staging directory derivation and filesystem path policies.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/storage/staging_dirs.py`.
- Legacy gist: Retains storage adapter module staging_dirs.py.

## V2 Improvement Intent
- Transform posture: Migrate.
- Target responsibility: Staging directory derivation and filesystem path policies.
- Improvement goal: Carry forward stable behavior while enforcing V2 contracts and explicit context.
## Inputs
- Root directory settings for intake, staging, processed, rejected, and archive areas.
- Runtime profile/mode tokens affecting directory partitioning.
- Candidate route facts (date/profile/device tokens) used for derived subpaths.
- Directory policy settings (create-on-demand, cleanup retention, naming constraints).

## Outputs
- Derived absolute directory path set for each lifecycle bucket.
- Directory creation/validation result when create-on-demand is enabled.
- Cleanup candidate list based on retention policy inputs.
- Typed directory policy errors for invalid derivation.

## Invariants
- Directory derivation is deterministic for identical settings and route facts.
- Derived directories stay within configured root scope.
- Path normalization is applied before returning paths.
- Cleanup candidate derivation never includes active intake/staging directories.

## Failure Modes
- Missing/invalid root settings raise `StagingDirsConfigError`.
- Derived path escaping root scope raises `StagingDirsSafetyError`.
- Directory create/validation failure raises `StagingDirsProvisionError`.
- Unsupported token values in derivation input raise `StagingDirsTokenError`.

## Pseudocode
1. Normalize configured roots and validate required directory policy fields.
2. Derive bucket paths (intake/staging/processed/rejected/archive) from route/profile/date tokens.
3. Validate derived paths remain within allowed roots.
4. Optionally create missing directories according to policy.
5. Build cleanup candidate set from retention configuration and path metadata.
6. Return directory set plus optional provision/cleanup diagnostics.

## Tests To Implement
- unit: deterministic derivation, root-scope safety checks, token validation, and cleanup candidate filtering.
- integration: ingest persist/post-persist flows consume derived directories and handle provisioning failures through typed outcomes.



