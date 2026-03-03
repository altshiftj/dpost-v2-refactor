# Folder Documentation: docs/pseudocode/application/ingestion/stages

## Purpose
- Stage-by-stage flow specs defining deterministic processing transitions.

## Contents
- Subfolders:
  - `(none)`
- Spec Files:
  - `persist.md`
  - `pipeline.md`
  - `post_persist.md`
  - `resolve.md`
  - `route.md`
  - `stabilize.md`

## Justification for Delineation
- Stage docs are isolated to support independent parallel implementation and deterministic stitching.

