---
id: __main__.py
origin_v1_files:
  - src/dpost/__main__.py
lane: Startup-Core
status: draft
depends_on: []
owned_side_effects: []
reads: []
writes: []
---

## Intent
- Parse mode/profile args and dispatch runtime entrypoint (`v1`,`v2`,`shadow`).

## Origin Gist
- Source mapping: `src/dpost/__main__.py`.
- Legacy gist: Defines V2 entrypoint and architecture mode dispatch.

## V2 Improvement Intent
- Transform posture: Rewrite.
- Target responsibility: Parse mode/profile args and dispatch runtime entrypoint (`v1`,`v2`,`shadow`).
- Improvement goal: Rebuild the module around cleanroom contracts while preserving intended outcomes.
## Inputs
- CLI argv (`--mode`, `--profile`, `--config`, `--headless`, `--dry-run`).
- Environment fallback values (`DPOST_MODE`, `DPOST_PROFILE`, `DPOST_CONFIG`).
- Bootstrap entrypoint callable from `application.startup.bootstrap`.
- Process-level stdout/stderr for human-readable startup diagnostics.

## Outputs
- `int` process exit code (`0` success, non-zero startup or argument failures).
- `BootstrapRequest` value passed to startup bootstrap orchestration.
- Structured startup failure event written through bootstrap event channel.
- Optional version/help output for CLI introspection paths.

## Invariants
- Argument parsing is deterministic and side-effect free.
- Runtime mode defaults to `v2` when not explicitly provided.
- Mode/profile validation occurs before any adapter initialization.
- `__main__` never constructs infrastructure adapters directly.

## Failure Modes
- Invalid CLI shape raises parser error and exits with usage code.
- Unsupported mode token raises `UnsupportedRuntimeModeError`.
- Bootstrap exception returns non-zero exit and emits structured startup failure.
- Keyboard interrupt returns graceful non-zero termination without trace spam.

## Pseudocode
1. Parse argv into a typed command object; merge missing fields from environment defaults.
2. Validate requested mode/profile/config path, then construct `BootstrapRequest`.
3. Call `bootstrap.run(request)` and capture returned `BootstrapResult`.
4. Emit user-facing summary line for success or normalized error details for failure.
5. Map result category to process exit code and return from `main()`.
6. Keep module dependency-free except parser definitions and bootstrap entrypoint import.

## Tests To Implement
- unit: parser accepts valid arg combinations, defaults mode/profile correctly, and rejects invalid modes before bootstrap.
- integration: invoking entrypoint with a real bootstrap stub returns expected exit codes and emits startup failure events on exceptions.



