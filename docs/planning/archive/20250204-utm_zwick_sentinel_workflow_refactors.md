# Refactor opportunities: UTM Zwick sentinel workflow

## Summary
Targeted refactors that can simplify the sentinel `.xlsx` workflow and improve maintainability without changing behavior.

## Candidates
1. **Unify prefix validation + sanitization**
   - **Observation**: `device_specific_preprocessing()` only validates with `is_valid_prefix()` and does not sanitize. Other processors use `sanitize_prefix()` or `sanitize_and_validate()` for consistency.
   - **Potential refactor**: Replace `is_valid_prefix()` with `sanitize_and_validate()` and store the sanitized prefix in `_SeriesState.sample` so record IDs are consistent.
   - **Benefit**: Avoids mixed casing/spacing and keeps naming consistent across devices.

2. **Consolidate TTL handling into preprocessing lock**
   - **Observation**: `_find_ttl_ready()` is called before the main lock in `device_specific_preprocessing()`. It grabs its own lock internally, which results in two lock acquisitions per event.
   - **Potential refactor**: Move TTL scanning into the main lock block and/or merge with state updates.
   - **Benefit**: Simplifies concurrency reasoning and reduces lock churn.

3. **Make TTL flush explicit in `flush_incomplete()`**
   - **Observation**: TTL behavior is hidden in preprocessing. `flush_incomplete()` currently processes all remaining series regardless of staleness.
   - **Potential refactor**: Add a TTL check in `flush_incomplete()` (or a dedicated `_purge_or_flush_stale()` method) to align behavior across entry points.
   - **Benefit**: Consistent TTL enforcement for manual/session-end flushes.

4. **Remove no-op `flush_series()`**
   - **Observation**: `flush_series()` now returns immediately after the flag check, with no behavior.
   - **Potential refactor**: Remove the method or delegate to `flush_incomplete()` when `flush_on_session_end` is enabled.
   - **Benefit**: Reduces dead code and clarifies session-end behavior.

5. **Simplify naming constants**
   - **Observation**: `results_prefix = f"{file_id}_results"` mirrors other processors but is now the only derived name in this processor.
   - **Potential refactor**: Extract to a helper or inline consistent naming constants.
   - **Benefit**: Smaller surface for future edits; clearer intent.

## Notes
- No changes proposed in this document; these are optional refactors after tests are green.
- Any refactor touching prefixes should be coordinated with naming rules in core validation.
