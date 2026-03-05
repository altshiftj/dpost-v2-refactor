# 20260305 V2 Handshake Slice 02: Stabilize Facts and Stock Prod Headless

## Scope
- Close the documented standalone gap where stock prod headless startup succeeded but fresh files deferred before route/persist.
- Keep the slice focused on runtime facts and stabilize behavior, not plugin policy or processor-contract expansion.

## TDD Record
- Red tests added first in `tests/dpost_v2/runtime/test_composition.py`:
  - `test_composition_runtime_uses_real_file_facts_for_stabilize_and_candidate`
  - `test_composition_stock_prod_headless_processes_fresh_files_in_one_pass`
- Initial failure mode before implementation:
  - aged files still deferred because runtime fed `modified_at = now`
  - stock-prod-like settings (`retry_delay_seconds = 1.0`) left fresh files in `incoming`
  - sqlite persisted no `records` rows in the stock config manual probe

## Implementation
- `src/dpost_v2/runtime/composition.py`
  - `fs_facts_provider()` now reads real file facts from filesystem stat data:
    - `size`
    - `modified_at`
    - stable fingerprint derived from path, size, and mtime
  - `_resolve_settle_delay_seconds()` no longer reuses `ingestion.retry_delay_seconds` as stabilize settle delay.
  - Runtime settle delay now defaults to `0.0` unless an explicit `settle_delay_seconds` field is introduced later.

## Validation
- `python -m pytest -q tests/dpost_v2/runtime tests/dpost_v2/application/startup`
  - `57 passed`
- `python -m pytest -q tests/dpost_v2`
  - `397 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed

## Result
- Stock prod headless one-pass runtime now processes fresh files without a temporary no-settle config override.
- Stabilize uses real file mtimes instead of synthetic `now` timestamps.
- Candidate payloads now carry real file size and modification-time facts into downstream persistence.

## Manual Interpretation
- The standalone ceiling has moved again:
  - startup succeeds
  - headless runtime finds files
  - fresh files pass stabilize in stock prod config
  - files move into `processed`
  - sqlite records persist with concrete plugin ids
- Remaining gaps are now downstream architecture seams:
  - PC-scoped device policy
  - explicit processor `prepare/process` handoff
  - PC-owned sync payload shaping
