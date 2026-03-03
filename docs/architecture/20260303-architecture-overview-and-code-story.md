# Architecture Overview and Code Story

## Date
- 2026-03-03

## What This System Is
- `dpost` is a plugin-driven watchdog runtime for scientific data ingestion.
- It watches filesystem drop zones, resolves device-specific processors, transforms/routes outputs, persists local record state, and optionally syncs to an external backend.

## Structural Shape
1. Domain layer (`src/dpost/domain/`)
- Pure models and policy logic.
- No infrastructure/runtime wiring.

2. Application layer (`src/dpost/application/`)
- Orchestration and use-case flow.
- Ports and contracts consumed by runtime/infrastructure.

3. Infrastructure layer (`src/dpost/infrastructure/`)
- Concrete adapters: UI runtime, storage/fs, logging, observability, sync.

4. Plugin layer (`src/dpost/plugins/`, `src/dpost/device_plugins/`, `src/dpost/pc_plugins/`)
- Extension points for PC/device behavior and discovery.

## Runtime Story (Startup to Running Loop)
1. Composition root resolves runtime mode, sync adapter, profile/settings:
- `src/dpost/runtime/composition.py`

2. Bootstrap constructs concrete runtime dependencies:
- `src/dpost/runtime/bootstrap.py`
- `src/dpost/infrastructure/runtime_adapters/startup_dependencies.py`

3. UI runtime selection is adapter-based:
- `headless`: `src/dpost/infrastructure/runtime_adapters/headless_ui.py`
- `desktop`: `src/dpost/infrastructure/runtime_adapters/tkinter_ui.py`
- selector: `src/dpost/infrastructure/runtime_adapters/ui_factory.py`

4. Main app loop owns observer/event-queue lifecycle:
- `src/dpost/application/runtime/device_watchdog_app.py`

## Processing Story (Per Artifact)
1. `FileProcessManager` is the orchestration shell:
- `src/dpost/application/processing/file_process_manager.py`

2. `_ProcessingPipeline` is the stage machine:
- resolve device
- stability guard
- device preprocessing
- route decision
- persist or rename/reject flow
- file: `src/dpost/application/processing/processing_pipeline.py`

3. `ProcessingPipelineRuntime` is the runtime adapter used by the stage machine:
- exposes manager-owned collaborators behind a runtime port
- file: `src/dpost/application/processing/processing_pipeline_runtime.py`

## Why Pipeline and Pipeline Runtime Both Exist
- `_ProcessingPipeline` keeps stage logic explicit and testable as a flow machine.
- `ProcessingPipelineRuntime` isolates side-effect collaborators and manager internals behind a contract.
- This split reduces orchestration sprawl without changing runtime behavior.

## Configuration and Naming Story
1. Config schema owns canonical runtime policy surface:
- `src/dpost/application/config/schema.py`
- `NamingSettings` is the naming source of truth (separator/pattern policy).

2. Config service provides active PC/device context:
- `src/dpost/application/config/service.py`
- includes explicit `ConfigDeviceProtocol` for device matching/activation contract shape.

3. Application naming facade applies runtime naming context to pure domain policy:
- `src/dpost/application/naming/policy.py`
- pure domain helpers: `src/dpost/domain/naming/identifiers.py`, `src/dpost/domain/naming/prefix_policy.py`

## Plugin Story
- Pluggy host and hooks live in `src/dpost/plugins/system.py`.
- Loader boundary lives in `src/dpost/plugins/loading.py`.
- Device and PC plugins provide config + processor capabilities via contract-conformant factories.

## Records and Sync Story
- Local record lifecycle/persistence is owned by:
- `src/dpost/application/records/record_manager.py`
- Storage/path/move helpers are owned by:
- `src/dpost/infrastructure/storage/filesystem_utils.py`
- Sync is port-driven with adapter selection at composition:
- port: `src/dpost/application/ports/sync.py`
- adapters: `src/dpost/infrastructure/sync/noop.py`, `src/dpost/infrastructure/sync/kadi.py`

## Governance Story
- Architecture baseline, contract, and responsibility catalog are explicit and maintained:
- `docs/architecture/architecture-baseline.md`
- `docs/architecture/architecture-contract.md`
- `docs/architecture/responsibility-catalog.md`

## Delivery Story (As Written Today)
- The code reflects a migration from mixed legacy seams toward explicit ownership in `src/dpost/**`.
- Current posture emphasizes:
- explicit runtime boundaries at composition/startup
- explicit naming/config context in hot paths
- isolated manual test lane (`tests/manual`) outside default CI/test runs
- CI lanes split by intent (`quality`, `unit-tests`, `integration-tests`, smoke, hygiene)
