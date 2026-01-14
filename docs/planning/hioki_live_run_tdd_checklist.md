# Hioki live run TDD checklist

Target: fix the live run issues described in `docs/planning/hioki_live_run_report_20260114.md`

- [ ] Add a failing test: measurement should create `{file_id}-02.csv` even when the aggregate file already exists.
  - Justification: current preprocessing normalizes the timestamped name to the base name, so the aggregate path wins and the measurement file is skipped.
  - Resolved: TODO.
- [ ] Add a failing test: aggregate updates (same filename) are reprocessed and force-synced.
  - Justification: watcher only queues `on_created`, so in-place updates never trigger processing.
  - Resolved: TODO.
- [ ] Add a failing test: CC updates (same filename) are reprocessed and force-synced.
  - Justification: CC updates appear as "Changed" events in the lab logs, and are not processed today.
  - Resolved: TODO.
- [ ] Implement: ensure timestamped measurement files stay the effective path for processing.
  - Justification: the current fallback picks an existing aggregate path, which reroutes measurement events to results.
  - Resolved: TODO.
- [ ] Implement: decide and apply a strategy for modified events (global `on_modified` handling or Hioki-only opt-in).
  - Justification: aggregate/CC updates are in-place modifications, not new files.
  - Resolved: TODO.
- [ ] Verify naming conventions stay enforced: `{file_id}-##.csv`, `{file_id}-cc.csv`, `{file_id}-results.csv`.
  - Justification: record consistency for Kadi sync and traceability.
  - Resolved: TODO.
- [ ] Add a higher-level regression test that mirrors the lab sequence (CC -> measurement -> aggregate -> measurement -> aggregate/CC change).
  - Justification: ensures ordering and sync behavior match real-world behavior.
  - Resolved: TODO.
