# Modified Event Gate refactor checklist

Target: refactor the modified-event gating logic introduced for Hioki without changing behavior.

- [x] Create a small helper (e.g., `ModifiedEventGate`) that owns debounce + opt-in logic.
  - Justification: isolates state (`_modified_event_tracker`) and keeps `FileProcessManager` smaller.
  - Resolved: added `ModifiedEventGate` in `src/ipat_watchdog/core/processing/modified_event_gate.py`.
- [x] Move `should_queue_modified` logic from `FileProcessManager` into the helper.
  - Justification: keep the manager focused on orchestration, not event policy.
  - Resolved: `FileProcessManager.should_queue_modified` delegates to the gate.
- [x] Wire the helper back into `FileProcessManager` and keep the public API the same.
  - Justification: no behavior change for `DeviceWatchdogApp` or tests.
  - Resolved: gate constructed in `FileProcessManager` with the existing processor resolver.
- [x] Run existing tests that cover modified-event behavior.
  - Justification: refactor safety check with no new behavior.
  - Resolved: `python -m pytest tests/unit/core/app/test_device_watchdog_app.py::test_modified_events_queue_only_when_callback_allows tests/unit/device_plugins/erm_hioki/test_file_processor.py::test_should_queue_modified_only_for_cc_and_aggregate tests/unit/device_plugins/erm_hioki/test_live_run_sequence.py::test_measurement_processed_even_when_aggregate_exists`.
