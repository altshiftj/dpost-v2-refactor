# Folder Documentation: docs/pseudocode/application/ingestion/policies

## Purpose
- Cross-stage policy specs (retry, failure mapping, gating, force-path behavior).

## Contents
- Subfolders:
  - `(none)`
- Spec Files:
  - `error_handling.md`
  - `failure_emitter.md`
  - `failure_outcome.md`
  - `force_path.md`
  - `immediate_sync_error_emitter.md`
  - `modified_event_gate.md`
  - `retry_planner.md`

## Justification for Delineation
- Policy logic is separated from stage flow so behavior tuning can occur without rewriting core orchestration.

