# Report: V2 Standalone Manual Closeout

## Summary
- Manual source-mode continuous closeout passed.
- Manual frozen debug-console continuous closeout passed.
- Both probes processed files that arrived after startup and persisted the
  expected plugin selection.
- The current silent runtime posture is accepted for this phase; richer
  operator-visible runtime progress remains deferred.

## Source Continuous Probe
- Probe root:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-source-closeout-146c3f2f87114ca4ac5735cbce5c1c50`
- Config posture:
  - `loop_mode = continuous`
  - `poll_interval_seconds = 0.5`
  - `idle_timeout_seconds = 300.0`
  - `max_runtime_seconds = 600.0`
  - `pc_name = tischrem_blb`
- Late file injected after startup:
  - `config\incoming\late-sem.tif`
- Observed results:
  - `config\incoming` drained
  - `config\processed\late-sem.tif` exists
  - sqlite record persisted
  - persisted `candidate.plugin_id = sem_phenomxl2`
  - operator confirmed the app returned to the prompt on its own

## Frozen Continuous Probe
- Probe root:
  - `C:\Users\fitz\AppData\Local\Temp\dpost-v2-frozen-closeout-920ff25c1c6b4686b92637502b0bfa01`
- Executable:
  - `dist\pyinstaller-v2\dpost-v2-headless-debug\dpost-v2-headless-debug.exe`
- Config posture:
  - `loop_mode = continuous`
  - `poll_interval_seconds = 0.5`
  - `idle_timeout_seconds = 300.0`
  - `max_runtime_seconds = 600.0`
  - `pc_name = tischrem_blb`
- Late file injected after startup:
  - `config\incoming\late-sem-frozen.tif`
- Observed results:
  - `config\incoming` drained
  - `config\processed\late-sem-frozen.tif` exists
  - sqlite record persisted
  - persisted `candidate.plugin_id = sem_phenomxl2`

## Accepted Interpretation
- Source continuous mode processes files arriving after startup.
- Frozen continuous mode processes files arriving after startup.
- The runtime/service posture is acceptable for this phase.

## Deferred Improvement
- Debug-console mode currently provides a console surface, but not rich live
  runtime progress output.
- The CLI prints startup success and failure paths, but not explicit terminal
  completion reasons for successful idle completion.
- This is accepted as an observability/UX improvement for a later slice, not a
  blocker for current standalone closeout.

## Supporting Validation
- Existing automated lifecycle/build gates remain green from the current
  standalone slice:
  - `python -m ruff check src/dpost_v2 tests/dpost_v2`
  - `python -m pytest -q tests/dpost_v2`
  - `python -m pre_commit run --all-files`
