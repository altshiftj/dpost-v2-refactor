# 20260305 V2 Handshake Slice 04: Ingestion Transform and Processor Result Handoff

## Scope
- Complete the `Ingestion handshake (processor contract path)` section from the handshake-first checklist.
- Keep the slice focused on explicit processor execution and typed handoff, not device-specific parity logic.

## TDD Record
- Red tests added first in `tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py`:
  - `test_transform_stage_continues_to_route_with_validated_processor_result`
  - `test_transform_stage_rejects_candidate_when_processor_cannot_process`
  - route-stage expectation updated to use processor `final_path`
- Red tests added first in `tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py`:
  - `test_persist_stage_continues_to_post_persist_on_success`
    - extended to require persisted `processor_result`
- Red tests added first in `tests/dpost_v2/application/ingestion/stages/test_pipeline.py`
  - transition table updated to require `stabilize -> transform -> route`
- Red tests added first in `tests/dpost_v2/application/ingestion/test_engine.py`
  - required stage-order expectations updated to include `transform`
- Red tests added first in `tests/dpost_v2/application/ingestion/test_pipeline_integration.py`
  - full happy-path pipeline updated to execute `transform`
- Red tests added first in `tests/dpost_v2/runtime/test_composition.py`
  - `test_composition_runtime_persists_processor_result_payload`
- Initial failure mode before implementation:
  - runtime selected processors only for `can_process`
  - runtime-built `ProcessingContext` never reached ingestion state
  - route used source filename only
  - persist saved candidate/target only, with no processor output

## Implementation
- `src/dpost_v2/application/ingestion/state.py`
  - added state fields for:
    - `processing_context`
    - `prepared_input`
    - `processor_result`
  - extended `IngestionState.from_event(...)` to accept runtime processing context
- `src/dpost_v2/application/ingestion/stages/transform.py`
  - new explicit stage executing:
    - optional `prepare(...)`
    - `can_process(...)`
    - `process(...)`
    - `validate_processor_result(...)`
  - rejects when processor cannot process under current scope
- `src/dpost_v2/application/ingestion/stages/stabilize.py`
  - now continues to `transform`
- `src/dpost_v2/application/ingestion/stages/route.py`
  - filename builder now receives `IngestionState`
  - route can use processor-derived output filename
- `src/dpost_v2/application/ingestion/stages/persist.py`
  - persisted record payload now includes normalized `processor_result`
- `src/dpost_v2/application/ingestion/stages/pipeline.py`
  - default transition table now includes the `transform` stage
- `src/dpost_v2/application/ingestion/engine.py`
  - required stage order now includes `transform`
- `src/dpost_v2/runtime/composition.py`
  - runtime ingestion engine now registers the `transform` stage
  - runtime adapter no longer discards `ProcessingContext`
  - direct engine calls without explicit runtime context synthesize a fallback `ProcessingContext`
  - route filename defaults to processor `final_path` basename when present
  - sqlite payloads now persist `processor_result`
  - default fallback device processor shim now emits a contract-valid `datatype`

## Validation
- `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py tests/dpost_v2/application/ingestion/stages/test_pipeline.py tests/dpost_v2/runtime/test_composition.py`
  - `41 passed`
- `python -m pytest -q tests/dpost_v2/application/ingestion tests/dpost_v2/application/runtime tests/dpost_v2/runtime`
  - `86 passed`
- `python -m pytest -q tests/dpost_v2`
  - `406 passed`
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed

## Result
- V2 ingestion now has an explicit processor-contract seam instead of selection-only behavior.
- Runtime-built `ProcessingContext` now reaches processor execution.
- Route and persistence consume typed processor output:
  - route uses processor `final_path` basename
  - persist saves normalized `processor_result`
- Runtime sqlite payloads now prove processor execution occurred without relying on plugin-specific parity features.

## Deferred
- Device-specific `prepare/process` parity behavior for the three target plugins
- PC-owned sync payload shaping in post-persist
- Decision on whether `prepared_input` should also become part of persisted record payloads
