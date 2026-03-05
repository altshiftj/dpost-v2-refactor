# Report: V2 Three-Plugin Closeout

## Scope
- Worktree:
  - `.worktrees/laneD-closeout`
- Goal:
  - integrate lane0, laneA, laneB, and laneC outputs
  - run the closeout gates for the accepted three-plugin parity scope
  - determine whether the phase is closed on the real V2 headless path

## Intake
- Integrated committed lane outputs from:
  - `lane0-spec-lock` at `b33d33e`
  - `laneA-sem-phenomxl2` at `a4f289a`
  - `laneB-utm-zwick` at `cc4ce02`
  - `laneC-psa-horiba` at `3dd0457`
- Follow-on shared seam slice:
  - `docs/reports/20260305-v2-staged-runtime-seam-report.md`

## Validation Run
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2/application/ingestion/stages/test_resolve_stabilize_route.py tests/dpost_v2/application/ingestion/stages/test_persist_post_persist.py tests/dpost_v2/application/ingestion/test_pipeline_integration.py tests/dpost_v2/runtime/test_composition.py`
  - `43 passed`
- `python -m pytest -q tests/dpost_v2/plugins/test_migration_coverage.py`
  - passed
- `python -m pytest -q tests/dpost_v2`
  - `426 passed`

## Runtime Proof
- `tischrem_blb -> sem_phenomxl2`
  - succeeds end-to-end
  - persists `plugin_id="sem_phenomxl2"` and `datatype="img"`
- `zwick_blb -> utm_zwick`
  - raw `.zs2` pre-event now defers without failing the watch loop
  - matching `.xlsx` finalizer completes and persists one record
  - finalized artifacts land in `processed/` as `.xlsx` plus paired `.zs2`
- `horiba_blb -> psa_horiba`
  - staged `.ngb/.csv/.csv/.ngb` pre-events now defer without failing the watch loop
  - sentinel finalizer completes and persists one record
  - finalized artifacts land in `processed/` as numbered `.csv` and `.zip` outputs
- Restricted no-PC target-device run:
  - `plugins.device_plugins=("psa_horiba", "sem_phenomxl2", "utm_zwick")`
  - one-pass result:
    - `processed_count=7`
    - `failed_count=0`
    - `terminal_reason=end_of_stream`
    - `3` persisted records

## Shared seam outcome
- The closeout blocker is resolved.
- Implemented in the shared runtime:
  - transform-stage deferred retry for not-ready staged inputs
  - transform retry transition support
  - per-plugin runtime processor reuse across events
  - headless event ordering by file mtime
  - persist move-plan support for finalized artifacts and normalized `force_paths`
  - standalone `plugins.device_plugins` restriction without requiring a selected PC

## Residual deferred items
- `utm_zwick`
  - TTL/session-end flush
  - overwrite/unique-move hardening beyond the accepted slice
- `psa_horiba`
  - rename-cancel whole-folder handling
  - exception-bucket behavior
- runtime
  - richer successful-sync metadata persistence remains thin

## Conclusion
- The accepted three-plugin functional parity phase is closed.
- Completed:
  - lane0 spec lock
  - SEM parity slice
  - Zwick parity slice
  - PSA parity slice
  - shared staged/deferred runtime seam
  - closeout gates on the real V2 headless path
- Remaining deferred items are documented and out of scope for this closeout gate.
