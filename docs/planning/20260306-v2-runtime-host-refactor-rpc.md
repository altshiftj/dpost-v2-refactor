# Plan: V2 RuntimeHost Refactor

## Intent
- Replace the current app-owned shutdown seam with a first-class runtime host.
- Keep the already-green shutdown behavior while improving the lifecycle
  architecture before frozen/bootstrap and PyInstaller work.

## Why This Refactor Is Needed Now
- The current `DPostApp.shutdown()` hook is behaviorally correct, but it is not
  the cleanest long-term ownership model.
- Packaging and service-like execution will amplify lifecycle concerns:
  - startup
  - shutdown
  - signal/interrupt handling
  - adapter ownership
- If the current seam survives into frozen/bootstrap work, it is more likely to
  become permanent by inertia.

## Architectural Decision
- Introduce a `RuntimeHost` as the first-class lifecycle owner.
- Keep `DPostApp` responsible for:
  - session lifecycle within a run
  - event polling/processing orchestration
  - emitting runtime/ingestion events
- Move ownership of:
  - adapter shutdown ordering
  - host lifecycle semantics
  - top-level runtime `run()` / `shutdown()`
  into the host.

## Exact Target Contract
### `RuntimeHost`
- Required public API:
  - `run() -> RunResult`
  - `shutdown() -> None`
- Required properties:
  - idempotent `shutdown()`
  - `run()` delegates to the runtime app
  - host owns adapter cleanup ordering
  - host may expose diagnostics if useful, but lifecycle is the required
    contract

### `DPostApp`
- Remains a runtime application object, not the deployment/lifecycle owner.
- Should not own concrete adapter cleanup semantics after this refactor.
- May keep pure runtime-loop helpers and session behavior.

### Composition
- Must construct:
  - the `DPostApp`
  - the `RuntimeHost`
- Must stop exposing the app-owned shutdown seam as the canonical contract.
- `CompositionBundle.app` may remain as a diagnostic/testing convenience only if
  needed, but the runtime handle reaching bootstrap/CLI should be the host.

### CLI / Bootstrap
- Must talk to the host contract only:
  - `run()`
  - `shutdown()`
- CLI should not know adapter details or composition internals.

## Explicit Non-Goals
- No compatibility shim that is intended to live indefinitely.
- No second lifecycle owner beside the host.
- No new legacy fallback path.

## Preferred Refactor Style
- Clean cut, one behavior-preserving slice.
- Accept targeted test churn now to avoid carrying a bridge later.
- Keep the already-green lifecycle behavior as the invariant:
  - success still shuts down
  - runtime exception still shuts down
  - interrupt still shuts down
  - shutdown failure still returns exit code `1`

## TDD Order
1. Add failing tests for a first-class `RuntimeHost`.
2. Add failing composition tests that require the host as the runtime handle.
3. Add failing CLI/bootstrap tests that consume the host contract.
4. Refactor composition/bootstrap/CLI together.
5. Remove or de-canonicalize the app-owned shutdown seam.

## Exit Criteria
- `RuntimeHost` is the canonical lifecycle owner.
- `DPostApp` no longer carries the final shutdown responsibility.
- CLI/bootstrap operate through the host contract.
- `tests/dpost_v2` remain green.
- Active standalone docs point packaging work at the host-based lifecycle shape.
