# Report: Helper Signature Narrowing (Storage/Naming) Slice

## Date
- 2026-03-03

## Context
- This slice targets strategic item 4 from `docs/planning/20260303-legacy-seams-freshness-rpc.md`.
- Goal: remove transitional optionality from high-traffic storage/naming helpers where explicit runtime context is already the dominant path.

## Current State
- Storage helper surface:
  - `src/dpost/infrastructure/storage/filesystem_utils.py`
  - contains several helpers with optional/contextual arguments maintained for compatibility paths.
- Naming helper surface:
  - `src/dpost/application/naming/policy.py`
  - enforces explicit separators/patterns but still includes some context-fallback behavior for device metadata-derived IDs.

## Target State
- High-traffic helper APIs require explicit context inputs by default.
- Compatibility affordances are isolated to clearly named wrappers or transitional seams only.
- Call sites are straightforward and do not rely on implicit fallbacks.

## Findings
- Most hot-path call sites already pass explicit naming/storage context.
- Remaining optional arguments can still obscure intent and increase branch count.
- Full removal of optionality should be incremental to avoid breaking low-frequency plugin/manual paths.

## Proposed Actions
1. Identify true hot-path helpers:
- path generation/move helpers used during routing and persistence.
2. Narrow required arguments first:
- make explicit context required where all production call sites already provide it.
3. Keep compatibility wrappers explicit:
- if needed, retain wrapper functions with clear compatibility naming and deprecation notes.

## Risks
- Signature changes can break downstream plugin tests if call-site inventory is incomplete.
- Aggressive narrowing can reduce pragmatic flexibility for manual troubleshooting flows.

## Validation Plan
- `python -m pytest -q tests/unit/infrastructure/storage/test_filesystem_utils.py`
- `python -m pytest -q tests/unit/application/naming/test_policy.py`
- `python -m pytest -q tests/unit/application/processing/test_record_persistence_context.py tests/unit/application/processing/test_rename_flow.py`
- `python -m pytest -q tests/integration/test_integration.py`

## References
- `docs/planning/20260303-legacy-seams-freshness-rpc.md`
- `src/dpost/infrastructure/storage/filesystem_utils.py`
- `src/dpost/application/naming/policy.py`
- `src/dpost/application/processing/record_persistence_context.py`
