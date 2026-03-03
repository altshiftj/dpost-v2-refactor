# Folder Documentation: docs/pseudocode/application/startup

## Purpose
- Startup lifecycle specs for settings loading, validation, context build, and bootstrap orchestration.

## Contents
- Subfolders:
  - `(none)`
- Spec Files:
  - `bootstrap.md`
  - `context.md`
  - `settings_schema.md`
  - `settings_service.md`
  - `settings.md`

## Justification for Delineation
- Application concerns are separated from domain and infrastructure so orchestration changes do not leak into business rules or adapters.

