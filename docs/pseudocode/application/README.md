# Folder Documentation: docs/pseudocode/application

## Purpose
- Application-layer orchestration specs: contracts, startup flow, runtime control, ingestion pipeline, and record services.

## Contents
- Subfolders:
  - `contracts/`
  - `ingestion/`
  - `records/`
  - `runtime/`
  - `session/`
  - `startup/`
- Spec Files:
  - `(none)`

## Justification for Delineation
- Application concerns are separated from domain and infrastructure so orchestration changes do not leak into business rules or adapters.

