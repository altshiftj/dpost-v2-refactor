# Scoped on_modified handling for Hioki

## Decision summary
We will NOT queue every on_modified event. Instead, we will make modified-event handling opt-in per processor and enable it only for the Hioki processor (CC and aggregate files). This avoids global watcher noise while still capturing the lab behavior (CC/aggregate are updated in place).

## Why this decision
- Global on_modified queuing is noisy and can trigger repeated processing for unrelated devices.
- Hioki CC and aggregate files update in place, so we need a way to reprocess them.
- An opt-in hook keeps the blast radius small and testable.

## Chain of events (runtime sequence)
1. Watchdog observer receives a filesystem on_modified event.
2. QueueingEventHandler checks the event (ignores directories).
3. Handler calls `should_queue_modified(path)` (new callback) to decide if it should enqueue.
4. `should_queue_modified` resolves candidate devices for the path using ConfigService.
5. For each candidate, it loads the processor and asks `processor.should_queue_modified(path)`.
6. If any processor returns True, the gate applies a per-path cooldown to avoid enqueue storms.
7. If allowed, the handler enqueues the path; otherwise it drops the event.
8. FileProcessManager processes the path normally.
9. Hioki processor recognizes CC/aggregate and overwrites `{file_id}-cc.csv` or `{file_id}-results.csv`, marking force sync.
10. Immediate sync uploads the updated file to Kadi.

## Implementation checklist
- [ ] Add `should_queue_modified(self, path: str) -> bool` to `FileProcessorABS` with a default of False.
  - Justification: makes modified-event handling explicit and opt-in.
  - Resolved: TODO.
- [ ] Implement `FileProcessorHioki.should_queue_modified`.
  - Return True for `CC_*.csv` and `{prefix}.csv` (aggregate) when the name is NOT timestamped.
  - Justification: only these files update in place and should trigger reprocessing.
  - Resolved: TODO.
- [ ] Add a modified-event gate in FileProcessManager, e.g. `should_queue_modified(path)`.
  - Uses ConfigService + FileProcessorFactory to check processors.
  - Applies a small per-path cooldown (e.g., 1.0s) to avoid enqueue storms.
  - Justification: keeps event policy centralized and debounced.
  - Resolved: TODO.
- [ ] Extend QueueingEventHandler to accept a `should_queue_modified` callback.
  - on_modified uses the callback; on_created behavior stays unchanged.
  - Justification: app layer stays thin, policy stays in processing layer.
  - Resolved: TODO.
- [ ] Wire DeviceWatchdogApp to pass the new callback into QueueingEventHandler.
  - Justification: enables the scoped behavior without changing other devices.
  - Resolved: TODO.

## Test checklist
- [ ] Update the modified-event test to expect enqueuing only when the callback returns True.
  - Justification: no global modified queuing.
  - Resolved: TODO.
- [ ] Add a Hioki-specific unit test that `should_queue_modified` returns True for CC/aggregate and False for timestamped measurements.
  - Justification: locks the intended behavior to Hioki only.
  - Resolved: TODO.
