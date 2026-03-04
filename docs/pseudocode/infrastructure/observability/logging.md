---
id: infrastructure/observability/logging.py
origin_v1_files:
  - src/dpost/infrastructure/logging.py
lane: Infra-Observability
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Logger config, structured log formatter, sink setup.

## Origin Gist
- Source mapping: `src/dpost/infrastructure/logging.py`.
- Legacy gist: Moves logging config to observability package.

## V2 Improvement Intent
- Transform posture: Move.
- Target responsibility: Logger config, structured log formatter, sink setup.
- Improvement goal: Clarify layer boundaries and naming without changing behavior intent.
## Inputs
- Logging configuration (level, sink targets, format style, redaction rules).
- Runtime metadata defaults (service name, mode, profile, host id).
- Event payloads from application/infrastructure layers.
- Optional test sink and in-memory capture hooks.

## Outputs
- Configured logger factory/instance bound to structured formatter.
- Structured log records with canonical fields and correlation ids.
- Sink initialization status and diagnostics.
- Typed logging setup/runtime errors.

## Invariants
- Structured log field schema is stable across runtime modes.
- Sensitive fields are redacted before serialization.
- Logger initialization is idempotent for identical config.
- Logging adapter never raises uncaught exceptions to application callers.

## Failure Modes
- Invalid logging configuration yields `LoggingConfigError`.
- Sink initialization failure yields `LoggingSinkInitError`.
- Serialization failure for payload fields yields `LoggingSerializationError`.
- Sink write timeout/failure yields `LoggingSinkWriteError`.

## Pseudocode
1. Validate logging config and build redaction/filter policy objects.
2. Initialize configured sinks and structured formatter with canonical field schema.
3. Create logger factory that enriches records with runtime metadata/correlation ids.
4. Apply redaction and safe-serialization before sink writes.
5. Map sink/serialization failures to typed logging errors while avoiding app-level crashes.
6. Expose no-op/testing logger variants for deterministic tests.

## Tests To Implement
- unit: config validation, redaction behavior, structured field stability, and sink failure mapping.
- integration: runtime and ingestion modules emit structured logs with correlation ids and survive sink failures without uncontrolled exceptions.



