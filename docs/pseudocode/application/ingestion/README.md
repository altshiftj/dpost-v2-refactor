# Folder Documentation: docs/pseudocode/application/ingestion

## Purpose
- Ingestion engine orchestration specs and runtime facade boundaries.

## Contents
- Subfolders:
  - `models/`
  - `policies/`
  - `stages/`
- Spec Files:
  - `engine.md`
  - `processor_factory.md`
  - `runtime_services.md`

## Justification for Delineation
- Application concerns are separated from domain and infrastructure so orchestration changes do not leak into business rules or adapters.

