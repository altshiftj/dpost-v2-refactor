# Report: V2 Three-Plugin Closeout

## Scope
- Worktree:
  - `.worktrees/laneD-closeout`
- Goal:
  - integrate lane0, laneA, laneB, and laneC outputs
  - run the planned closeout gates
  - determine whether the three-plugin functional parity phase is complete

## Intake
- Integrated committed lane outputs from:
  - `lane0-spec-lock` at `b33d33e`
  - `laneA-sem-phenomxl2` at `a4f289a`
  - `laneB-utm-zwick` at `cc4ce02`
  - `laneC-psa-horiba` at `3dd0457`
- Lane reports consumed:
  - `docs/reports/20260305-v2-lane0-spec-lock-report.md`
  - `docs/reports/20260305-v2-laneA-sem-phenomxl2-report.md`
  - `docs/reports/20260305-v2-laneB-utm-zwick-report.md`
  - `docs/reports/20260305-v2-laneC-psa-horiba-report.md`

## Validation Run
- `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - passed
- `python -m pytest -q tests/dpost_v2/plugins/devices/sem_phenomxl2/test_parity_spec.py tests/dpost_v2/plugins/devices/utm_zwick tests/dpost_v2/plugins/devices/psa_horiba tests/dpost_v2/runtime/test_composition.py`
  - failed in runtime composition
- `python -m pytest -q tests/dpost_v2/plugins/test_migration_coverage.py`
  - passed after updating stale template-era expectations for the migrated plugins
- `python -m pytest -q tests/dpost_v2`
  - `415 passed`
  - `9 failed`

## Runtime Proof
- SEM probe succeeded end-to-end under `tischrem_blb`:
  - probe root:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-tischrem_blb-pn2c1qlt`
  - result:
    - `processed_count=1`
    - `failed_count=0`
    - `terminal_reason=end_of_stream`
  - persisted record:
    - `plugin_id="sem_phenomxl2"`
    - `datatype="img"`
- Zwick probe failed on the first staged pre-event under `zwick_blb`:
  - probe root:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-zwick_blb-usf7mbgl`
  - result:
    - `processed_count=1`
    - `failed_count=1`
    - `terminal_reason=failed_terminal`
  - no records persisted
- PSA probe failed on the first staged pre-event under `horiba_blb`:
  - probe root:
    - `C:\\Users\\fitz\\AppData\\Local\\Temp\\closeout-horiba_blb-q71hmi_l`
  - result:
    - `processed_count=1`
    - `failed_count=1`
    - `terminal_reason=failed_terminal`
  - no records persisted

## Failure Analysis
- Remaining failing tests:
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_default_runtime_resolves_real_plugin_id_instead_of_default_device`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_default_runtime_moves_file_and_persists_record`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_uses_real_file_facts_for_stabilize_and_candidate`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_stock_prod_headless_processes_fresh_files_in_one_pass`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_persists_processor_result_payload`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_processes_pc_scoped_device_pairs_end_to_end[horiba_blb-sample.ngb-psa_horiba]`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_processes_pc_scoped_device_pairs_end_to_end[zwick_blb-sample.zs2-utm_zwick]`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_shapes_sync_payload_via_selected_pc_plugin`
  - `tests/dpost_v2/runtime/test_composition.py::test_composition_runtime_emits_sync_error_and_marks_record_unsynced_on_sync_failure`
- Root cause:
  - the shared runtime still assumes a candidate is either immediately processable or rejected
  - `psa_horiba` and `utm_zwick` now require staged/deferred pre-events before a finalizing event can be processed
- Concrete evidence:
  - raw PSA `.ngb` under `horiba_blb` resolves `psa_horiba` but is rejected in `transform` with `reason_code="cannot_process"`
  - raw Zwick `.zs2` under `zwick_blb` is rejected in `resolve` with `reason_code="processor_not_found"` because current selection still depends on immediate processability
- Result:
  - plugin-local parity is green
  - SEM end-to-end runtime is green
  - PSA and Zwick still need a shared deferred/staged runtime seam before the three-plugin phase can be declared complete

## Conclusion
- The three-plugin functional parity phase is not closed yet.
- Completed:
  - lane0 spec lock
  - SEM parity slice
  - Zwick plugin-local parity slice
  - PSA plugin-local parity slice
  - integrated closeout gate execution
- Not yet completed:
  - shared runtime support for deferred/staged pre-events so PSA and Zwick can run headless end-to-end without failing the watch loop

## Next Required Slice
- Introduce a first-class deferred/staged outcome in the ingestion/runtime seam and update composition/runtime tests to prove:
  - staged PSA pre-events do not fail the watch loop
  - staged Zwick pre-events do not fail the watch loop
  - finalizing PSA and Zwick events persist records and sync correctly after staging
