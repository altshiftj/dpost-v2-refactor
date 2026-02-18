# Refactor Proposal

## Title
- UTM Zwick post-green refactor backlog

## Date
- 2026-02-16

## Context
- The end-series stability fix is implemented and tests are green.
- This document captures behavior-preserving cleanup opportunities identified after the bug fix.
- Status update: all listed refactors in this proposal are now implemented.

## Motivation
- Current logic works but has duplicated paths for series lookup, artifact moves, and candidate metadata parsing.
- Reducing duplication here lowers regression risk for future Zwick workflow changes.

## Proposed Change
- Extract a shared series-state lookup helper in `FileProcessorUTMZwick` that encapsulates:
  - normalized key resolution.
- Extract a shared artifact move helper in `FileProcessorUTMZwick` to unify:
  - unique filename creation,
  - move + warning logging behavior.
- Extract candidate metadata derivation in `_ProcessingPipeline` to one helper so parse/fallback logic is not split across branches.
- Parametrize near-duplicate Zwick processing tests to reduce repeated setup and assertions.
- Remove legacy raw-key fallback to keep key handling strict and shim-free.

## Impacted Areas
- `src/ipat_watchdog/device_plugins/utm_zwick/file_processor.py`
- `src/ipat_watchdog/core/processing/file_process_manager.py`
- `tests/unit/device_plugins/utm_zwick/test_file_processor.py`
- `tests/unit/core/processing/test_file_process_manager.py` (only if helper extraction requires assertion updates)

## Alternative Options
- Keep current code as-is and rely on tests only.
- Apply only test parametrization and skip production refactors for now.

## Risks / Trade-offs
- Refactor-only changes can still introduce behavioral drift if helper boundaries are chosen poorly.
- Short-term readability gains can be offset by over-abstraction if helper names are not precise.

## Implementation Notes
- Suggested order:
  - 1. Extract series lookup helper and keep existing behavior byte-for-byte.
  - 2. Extract artifact move helper and preserve existing logging text.
  - 3. Extract candidate metadata helper and preserve prefix/extension override precedence.
  - 4. Parametrize tests after production refactors to lock behavior.
  - 5. Remove raw-key fallback shim.
- Guardrails:
  - no functional changes,
  - keep diffs small,
  - run targeted tests after each step.

### Completion Notes
- Added `_pop_series_state()` and `_move_staged_artifact()` in `FileProcessorUTMZwick`.
- Added `_derive_candidate_metadata()` in `_ProcessingPipeline`.
- Replaced duplicate Zwick processing tests with parameterized `test_device_specific_processing_moves_staged_series`.
- Removed raw-key fallback shim from staged series lookup.

## Validation
- `python -m pytest tests/unit/device_plugins/utm_zwick/test_file_processor.py`
- `python -m pytest tests/unit/core/processing/test_file_process_manager.py`
- `python -m pytest tests/integration/test_utm_zwick_integration.py`
- `python -m pytest`
