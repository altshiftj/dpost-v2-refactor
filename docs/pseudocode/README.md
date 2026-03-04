# Folder Documentation: docs/pseudocode

## Purpose
- Top-level index for all V2 pseudocode specifications and lane-oriented authoring conventions.

## Contents
- Subfolders:
  - `application/`
  - `domain/`
  - `infrastructure/`
  - `plugins/`
  - `runtime/`
- Spec Files:
  - `__main__.md`

## Front Matter Standard
- Every pseudocode spec file (non-README) must include:
  - `id` (the planned V2 Python module path)
  - `lane`
  - `origin_v1_files` (explicit V1 source file(s) mapped into this V2 spec)
- If there is no direct V1 source, set:
  - `origin_v1_files: []`
  - `origin_note: new_in_v2_or_no_direct_v1_source`
- Source mapping authority:
  - `docs/planning/20260303-v1-to-v2-exhaustive-file-mapping-rpc.md`

## Required Narrative Sections
- Every pseudocode spec file (non-README) must include:
  - `## Origin Gist`
  - `## V2 Improvement Intent`
- `Origin Gist` explains what the legacy source responsibility looked like.
- `V2 Improvement Intent` explains how the rewrite improves ownership, structure, or contracts while preserving functional intent.

## Active Execution Baseline (2026-03-04)
- Active checklist:
  - `docs/checklists/20260304-v2-pseudocode-population-checklist.md`
- Active traceability checklist:
  - `docs/checklists/20260304-v2-pseudocode-traceability-lane-completion-checklist.md`
- Active traceability refresh checklist:
  - `docs/checklists/20260304-v2-pseudocode-traceability-refresh-checklist.md`
- Active traceability gap-closure checklist:
  - `docs/checklists/20260304-v2-pseudocode-gap-closure-checklist.md`
- Active traceability report:
  - `docs/reports/20260304-v2-pseudocode-implementation-traceability-report.md`
- Active traceability matrix:
  - `docs/reports/20260304-v2-pseudocode-implementation-traceability-matrix.csv`
- Frozen execution order:
  - `contracts -> domain -> startup -> runtime -> ingestion -> records/session -> infrastructure -> plugins -> review`
- Completion snapshot:
  - non-README pseudocode specs: `65/65` done
  - placeholder-token audit: zero matches
  - origin mapping audit: `origin_v1_files` present in every non-README pseudocode spec

## Justification for Delineation
- Keeping a single root index prevents ambiguity about where model lanes start and which conventions are binding.

