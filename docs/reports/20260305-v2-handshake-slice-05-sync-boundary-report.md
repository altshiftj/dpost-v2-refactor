# 20260305 V2 Handshake Slice 05: Sync Boundary and PC Payload Shaping

## Scope
- Complete the `Sync boundary handshake (TDD)` section from the handshake-first checklist.
- Keep payload ownership with the selected PC plugin and transport ownership with the sync backend.

## TDD Record
- Red tests added first in `tests/dpost_v2/plugins/test_host.py`
  - `test_host_prepares_sync_payload_for_active_pc_plugin`
- Red tests added first in `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`
  - `test_persist_stage_continues_to_post_persist_on_success`
    - extended to require persisted `record_snapshot`
  - `test_post_persist_stage_completes_with_sync_warning_on_sync_failure`
    - updated so sync receives the full `IngestionState`
  - `test_post_persist_stage_uses_fallback_sync_reason_for_malformed_diagnostics`
    - updated to assert `record_snapshot` reaches sync
- Red tests added first in `tests/dpost_v2/runtime/test_composition.py`
  - `test_composition_runtime_shapes_sync_payload_via_selected_pc_plugin`
  - `test_composition_runtime_emits_sync_error_and_marks_record_unsynced_on_sync_failure`
- Initial failure mode before implementation:
  - `PluginHost` had no PC payload-shaping runtime entrypoint
  - persist dropped the saved record snapshot before post-persist
  - post-persist only passed `record_id` into sync
  - runtime always built sync payloads as `{record_id: ...}`
  - sync failure left persisted records in `pending` state

## Implementation
- `src/dpost_v2/plugins/host.py`
  - added `prepare_sync_payload(...)` for active PC plugins
- `src/dpost_v2/application/ingestion/state.py`
  - added `record_snapshot`
- `src/dpost_v2/application/ingestion/stages/persist.py`
  - carries `record_snapshot` forward into post-persist state
- `src/dpost_v2/application/ingestion/stages/post_persist.py`
  - sync trigger now receives full `IngestionState`
- `src/dpost_v2/runtime/composition.py`
  - persists normalized record snapshots from the record store
  - builds sync payloads through the selected PC plugin when available
  - falls back to `{record_id}` only when no explicit PC plugin is selected
  - marks records `unsynced` on immediate sync failure
  - preserves sync backend responsibility as transport only via `SyncRequest`

## Validation
- `python -m pytest -q tests/dpost_v2/plugins/test_host.py tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py tests/dpost_v2/runtime/test_composition.py`
  - `35 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pre_commit run --all-files`
  - passed
- `python -m pytest -q tests/dpost_v2`
  - `409 passed`

## Result
- PC plugin payload shaping is now a live runtime seam rather than a dormant contract.
- Post-persist sync uses persisted record state plus runtime context.
- Sync transport receives shaped `SyncRequest` payloads without owning payload policy.
- Immediate sync failures now leave persisted records `unsynced` and emit `immediate_sync_error`.

## Deferred
- Remove or formally deprecate `create_sync_adapter(...)` from the PC contract if the architecture stays transport-centralized.
- Decide whether successful sync should also write normalized sync metadata back into the record payload.
