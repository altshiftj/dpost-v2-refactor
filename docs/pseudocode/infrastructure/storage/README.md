# Folder Documentation: docs/pseudocode/infrastructure/storage

## Purpose
- Persistence and file-system adapter specs, including transactional record store boundary.

## Contents
- Subfolders:
  - `(none)`
- Spec Files:
  - `file_ops.md`
  - `record_store.md`
  - `staging_dirs.md`

## Justification for Delineation
- Infrastructure adapters are isolated to keep external integrations replaceable behind ports.

