# Hioki refactor opportunities

These are optional refactors surfaced after the scoped on_modified + Hioki fixes.
No behavior changes proposed here unless explicitly called out.

## Completed
- Extracted a `ModifiedEventGate` helper from `FileProcessManager`.
- Replaced the `.__staged__` alias hack with an explicit preprocessing result.
- Split `FileProcessorHioki.device_specific_processing` into intent-specific helpers.
- Tightened `should_queue_modified` to only CC/aggregate names (with prefix validation).
- Added a bounded debounce cache for modified events.

## Opportunities
None currently queued.

## Non-goals (for now)
- Changing record naming conventions or sync behavior.
- Reworking the watcher/observer threading model.
