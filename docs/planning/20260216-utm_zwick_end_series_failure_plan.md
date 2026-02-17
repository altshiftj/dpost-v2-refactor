# UTM Zwick end-series failure fix plan (2026-02-16)

## Goal
- Make end-of-series processing robust for mixed-case prefixes so staged `.ZS2` and sentinel `.xlsx` resolve to the same series and land in the record folder.
- Preserve raw artefact traceability in failure paths by preventing extension drift when moving to exceptions.

## Non-Goals
- Redesign the full Zwick workflow or device routing architecture.
- Change directory layout or Kadi sync semantics.
- Introduce new UI behavior.

## Constraints
- Python 3.12+, strict type checking, Black/Ruff rules.
- Keep diffs small and limited to affected processing paths.
- Follow human-in-the-loop TDD cycle:
  - write failing tests,
  - report and wait for approval,
  - implement fix,
  - rerun tests for human verification.

## Approach
- Normalize the series key consistently in both preprocessing and processing inside `FileProcessorUTMZwick`.
- Add a compatibility fallback during key lookup to tolerate in-memory legacy keys during rolling updates.
- In `FileProcessManager`, when `effective_path` falls back to the original source path, recompute prefix/extension from the fallback path to avoid extension drift on exception moves.
- Keep failure logging explicit about effective path, prefix, extension, and key used.

## Milestones
- Add failing regression tests for casing mismatch and extension drift.
- Get human approval to proceed after failing-test proof.
- Implement key normalization and fallback metadata correction.
- Run focused and full test suites; verify no regression in existing Zwick sentinel flow.

## Dependencies
- Confirmation that case-insensitive behavior is expected for `user` and `institute` segments.
- Availability of current UTM Zwick unit/integration test harness.
- Human approval gate between failing tests and implementation.

## Risks and Mitigations
- Risk: Over-normalization could change behavior for unusual legacy names.
  - Mitigation: normalize only key lookup/storage path, keep record/file IDs unchanged unless explicitly intended.
- Risk: Exception routing fix could alter existing failure filenames.
  - Mitigation: assert expected extension behavior in tests and preserve unique naming utility usage.
- Risk: New tests may be brittle on filesystem event timing.
  - Mitigation: prefer deterministic unit tests around processor and manager internals.

## Test Plan
- Add a failing test where `.ZS2` and `.xlsx` differ only by case in user/institute and confirm series resolution succeeds.
- Add a failing test where preprocessing path is missing and `effective_path` fallback occurs; assert exception move keeps true source suffix.
- Run targeted tests first:
  - `python -m pytest tests/unit/device_plugins/utm_zwick -k "series or casing or exception"`
- Run full suite after implementation:
  - `python -m pytest`

## Rollout / Validation
- Replay the same trace scenario locally and confirm:
  - no `No staged series` error for mixed-case prefixes,
  - one record folder contains expected artefacts,
  - exceptions folder does not receive mislabeled raw payloads.
- Validate logs contain clear key/extension diagnostics for any remaining rejection.
