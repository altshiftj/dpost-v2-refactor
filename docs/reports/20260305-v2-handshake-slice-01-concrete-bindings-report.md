# 20260305 V2 Handshake Slice 01: Concrete Bindings and Composed Runtime

## Scope
- Checklist sections completed in this slice:
  - `Concrete dependency binding handshake (TDD)`
  - `Composition-to-runtime handshake (TDD)`
- Supporting startup coverage was revalidated because dependency resolution changed from placeholder factories to concrete adapter construction.

## TDD Record
- Red tests added first in `tests/dpost_v2/runtime/test_startup_dependencies.py`:
  - `test_dependency_resolution_builds_concrete_runtime_bindings_for_headless_prod`
- Red tests added first in `tests/dpost_v2/runtime/test_composition.py`:
  - `test_composition_default_runtime_uses_concrete_dependency_bindings`
  - `test_composition_default_runtime_resolves_real_plugin_id_instead_of_default_device`
  - `test_composition_default_runtime_moves_file_and_persists_record`
- Initial failure mode before implementation:
  - `ui`, `storage`, `filesystem`, `sync`, and `plugins` were still dict placeholders.
  - Runtime resolved `default_device` instead of a concrete plugin id.
  - Headless run completed without moving source files.

## Implementation
- `src/dpost_v2/application/startup/settings.py`
  - Extended `to_dependency_payload()` to include `paths`, `sync`, and `ui` blocks so dependency resolution can build live adapters from normalized startup settings.
- `src/dpost_v2/infrastructure/storage/file_ops.py`
  - Added `normalize_path()` so `LocalFileOpsAdapter` satisfies both file-ops and filesystem port contracts.
- `src/dpost_v2/runtime/startup_dependencies.py`
  - Replaced placeholder runtime factories with concrete builders for:
    - `HeadlessUiAdapter` / UI factory selection
    - `SqliteRecordStoreAdapter`
    - `LocalFileOpsAdapter`
    - initialized `NoopSyncAdapter` and `KadiSyncAdapter`
    - activated builtin `PluginHost`
    - concrete clock and event sink objects
  - Added deterministic plugin-profile fallback so runtime profiles like `ci` do not break builtin plugin host activation during startup wiring.
- `src/dpost_v2/runtime/composition.py`
  - Updated persist bookkeeping to speak the real sqlite record-store contract:
    - explicit `record_id`
    - monotonic `revision`
    - mapped `payload`
  - Updated bookkeeping mutation to use optimistic concurrency input expected by the sqlite adapter.
  - Treated sync statuses `synced`, `queued`, and `skipped_noop` as successful post-persist outcomes for standalone/headless wiring.

## Validation
- `python -m pytest -q tests/dpost_v2/runtime/test_startup_dependencies.py tests/dpost_v2/runtime/test_composition.py`
  - `21 passed`
- `python -m pytest -q tests/dpost_v2/runtime tests/dpost_v2/application/startup`
  - `55 passed`
- `python -m pytest -q tests/dpost_v2/infrastructure/storage tests/dpost_v2/infrastructure/sync`
  - `33 passed`
- `python -m pytest -q tests/dpost_v2`
  - `395 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed

## Result
- Default headless V2 composition now binds real adapters instead of dict placeholders.
- Composed runtime can resolve a concrete device plugin id (`psa_horiba` in the `.ngb` runtime smoke) and perform real file movement plus sqlite record persistence.
- The runtime still does not implement PC-scoped device policy, processor `prepare/process` handoff, or PC-owned sync payload shaping. Those remain the next handshake sections.

## Manual Probe Addendum
- Manual probe workspace:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-probe-20260305-194406`
- Probe with stock [dpost-v2-prod.config.json](D:/Repos/dpost-v2-refactor/configs/dpost-v2-prod.config.json):
  - startup succeeded
  - files remained in `incoming`
  - `processed` stayed empty
  - sqlite file was created but contained no `records` rows
- Reproduced runtime result for that stock config:
  - `processed_count = 3`
  - `failed_count = 0`
  - `terminal_reason = end_of_stream`
  - each event emitted `ingestion_deferred`
- Root cause isolated to the stabilize/facts handshake:
  - stock prod config sets `ingestion.retry_delay_seconds = 1.0`
  - runtime currently feeds `candidate.modified_at` from `now_seconds` instead of file mtime in [composition.py](D:/Repos/dpost-v2-refactor/src/dpost_v2/runtime/composition.py:565)
  - stabilize retries whenever `age < settle_delay_seconds` in [stabilize.py](D:/Repos/dpost-v2-refactor/src/dpost_v2/application/ingestion/stages/stabilize.py:69)
- Probe with a temp config override setting `ingestion.retry_delay_seconds = 0.0`:
  - `incoming` drained
  - `processed` contained `sample.ngb`, `sample.tif`, `sample.zs2`
  - sqlite `records` rows persisted with:
    - `psa_horiba`
    - `sem_phenomxl2`
    - `utm_zwick`
- Practical interpretation:
  - concrete runtime wiring is working
  - real headless side effects are working
  - the remaining blocker for stock prod standalone behavior is the stabilize/facts seam, not startup/composition/persist wiring

## Deferred
- `Plugin policy handshake (PC scope first)`
- `Ingestion handshake (processor contract path)`
- `Sync boundary handshake (TDD)`
