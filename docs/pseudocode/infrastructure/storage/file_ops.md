---
id: infrastructure/storage/file_ops.py
origin_v1_files:
  - src/dpost/infrastructure/storage/filesystem_utils.py
lane: Infra-Storage
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Concrete file operations with explicit context input only.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/storage/filesystem_utils.py`.
- Legacy gist: Narrows broad helper surface into explicit context-driven file ops.

## V2 Improvement Intent
- Transform posture: Split.
- Target responsibility: Concrete file operations with explicit context input only.
- Improvement goal: Decompose orchestration into focused modules/stages with tighter ownership.
## Inputs
- File operation requests (`read`, `move`, `copy`, `delete`, `exists`, `mkdir`) with normalized paths.
- Operation context containing correlation ids, retry flags, and safety policy.
- Root-scope constraints and overwrite/collision strategy.
- Filesystem adapter primitives from host OS runtime.

## Outputs
- Typed `FileOpResult` envelope with status, source/target paths, and optional bytes count.
- Typed file operation errors mapped to infrastructure error taxonomy.
- Operation diagnostics (duration, syscall type, retryable hint).
- Idempotent no-op responses for allowed safe no-op operations.

## Invariants
- Every operation requires explicit context; no ambient global path/config lookup.
- Path safety checks run before any mutating filesystem call.
- File operations return typed outcomes instead of raw exceptions.
- Delete and mkdir operations are idempotent under configured safe-no-op policy.

## Failure Modes
- Path outside allowed root scope raises `FileOpsPathSafetyError`.
- Missing source path on required read/move raises `FileOpsNotFoundError`.
- Permission/lock failures raise `FileOpsPermissionError` or `FileOpsLockedError`.
- Cross-device move fallback failure raises `FileOpsCrossDeviceError`.

## Pseudocode
1. Validate operation request shape and enforce root/path safety constraints.
2. Dispatch to operation-specific handler (`read`, `move`, `copy`, `delete`, `mkdir`, `exists`).
3. Wrap host filesystem call and capture duration/diagnostics.
4. Map host exceptions to typed file operation errors.
5. Apply idempotent-safe semantics for configured no-op cases.
6. Return normalized `FileOpResult` to runtime services facade.

## Tests To Implement
- unit: path safety guard behavior, exception-to-error mapping, and idempotent no-op semantics.
- integration: ingestion persist stage file operations succeed/fail with deterministic typed outcomes under real filesystem conditions.



