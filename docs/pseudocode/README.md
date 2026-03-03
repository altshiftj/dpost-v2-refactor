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

## Justification for Delineation
- Keeping a single root index prevents ambiguity about where model lanes start and which conventions are binding.

