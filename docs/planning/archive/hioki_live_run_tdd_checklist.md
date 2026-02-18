# Hioki live run TDD checklist

Target: fix the live run issues described in `docs/planning/hioki_live_run_report_20260114.md`

- [x] Add a failing test: measurement should create `{file_id}-02.csv` even when the aggregate file already exists.
  - Justification: guard against regressions where prefix normalization could redirect measurement processing to the aggregate path.
  - Resolved: `test_measurement_creates_second_file_when_aggregate_exists`.
- [x] Add a failing test: aggregate updates (same filename) are reprocessed and force-synced.
  - Justification: watcher only queues `on_created`, so in-place updates never trigger processing.
  - Resolved: `test_aggregate_update_marks_force_after_upload`.
- [x] Add a failing test: CC updates (same filename) are reprocessed and force-synced.
  - Justification: CC updates appear as "Changed" events in the lab logs, and are not processed today.
  - Resolved: `test_cc_update_marks_force_after_upload`.
- [x] Implement: ensure timestamped measurement files stay the effective path for processing.
  - Justification: ensure the effective path remains the timestamped measurement even when the aggregate exists.
  - Resolved: Preprocessing now returns `PreprocessingResult` with `prefix_override` instead of aliasing paths.
- [x] Implement: decide and apply a strategy for modified events (global `on_modified` handling or Hioki-only opt-in).
  - Justification: aggregate/CC updates are in-place modifications, not new files.
  - Resolved: scoped on_modified via `should_queue_modified` + `ModifiedEventGate`.
- [x] Verify naming conventions stay enforced: `{file_id}-##.csv`, `{file_id}-cc.csv`, `{file_id}-results.csv`.
  - Justification: record consistency for Kadi sync and traceability.
  - Resolved: covered by `test_processing_moves_measurement_and_forces_cc_aggregate` and measurement sequence tests.
- [x] Add a higher-level regression test that mirrors the lab sequence (CC -> measurement -> aggregate -> measurement -> aggregate/CC change).
  - Justification: ensures ordering and sync behavior match real-world behavior.
  - Resolved: `test_full_lab_sequence_marks_measurements_and_force_updates`.
