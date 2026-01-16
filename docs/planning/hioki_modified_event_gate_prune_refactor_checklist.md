# Modified Event Gate pruning refactor checklist

Target: add bounded pruning to the modified-event debounce cache without changing behavior.

- [x] Add time-based pruning to the ModifiedEventGate cache.
  - Justification: avoid unbounded growth in long-running sessions.
  - Resolved: added prune thresholds + interval so stale entries are removed.
- [x] Ensure pruning never short-circuits the cooldown window.
  - Justification: preserve existing debounce behavior.
  - Resolved: clamp prune thresholds to be >= cooldown.
- [x] Run modified-event tests.
  - Justification: refactor safety check.
  - Resolved: ran targeted modified-event/unit tests.
