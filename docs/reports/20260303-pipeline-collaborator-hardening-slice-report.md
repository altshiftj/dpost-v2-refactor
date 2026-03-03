# Report: Pipeline Collaborator Hardening Slice

## Date
- 2026-03-03

## Context
- This slice targets strategic item 2 from `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`.
- Goal: reduce migration-style coupling where `ProcessingPipelineRuntime` proxies manager-private methods.

## Current State
- Stage machine:
  - `src/dpost/application/processing/processing_pipeline.py`
- Runtime adapter boundary:
  - `src/dpost/application/processing/processing_pipeline_runtime.py`
- Orchestration owner:
  - `src/dpost/application/processing/file_process_manager.py`
- Runtime adapter currently forwards several operations to manager private methods (`_...`).

## Target State
- `_ProcessingPipeline` depends on explicit runtime-port operations that read like stable collaborator capabilities.
- `ProcessingPipelineRuntime` no longer feels like a thin wrapper over manager-private internals.
- `FileProcessManager` remains lifecycle owner, but contract surfaces are clearer and less leak-prone.

## Findings
- Current split is functionally good and testable; this is not a broken architecture.
- Main smell is naming/coupling readability:
  - private-manager method names leak into runtime adapter behavior.
- Risk is long-term contributor confusion rather than runtime instability.

## Proposed Actions
1. Harden runtime port naming:
- rename runtime-port methods to capability names (for example, `move_candidate_to_exception`, `emit_failure_outcome`) instead of manager-private stage aliases.
2. Pull micro-collaborators where repeated:
- if the same side-effect pattern appears across several runtime methods, extract explicit collaborator classes (emission/move/record update).
3. Keep stage machine stable:
- avoid moving decision logic into runtime adapter; keep flow decisions in `processing_pipeline.py`.

## Risks
- Over-refactoring can create more indirection than it removes.
- Renaming runtime-port methods can create broad test churn; needs disciplined slicing.

## Validation Plan
- `python -m pytest -q tests/unit/application/processing/test_file_process_manager.py`
- `python -m pytest -q tests/unit/application/processing/test_file_process_manager_branches.py`
- `python -m pytest -q tests/unit/application/processing/test_record_flow.py`
- `python -m pytest -q tests/integration/test_integration.py`

## References
- `docs/planning/archive/20260303-legacy-seams-freshness-rpc.md`
- `src/dpost/application/processing/processing_pipeline.py`
- `src/dpost/application/processing/processing_pipeline_runtime.py`
- `src/dpost/application/processing/file_process_manager.py`

