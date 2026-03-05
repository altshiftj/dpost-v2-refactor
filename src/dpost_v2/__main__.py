"""V2 executable entrypoint with explicit startup bootstrap dispatch."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from dpost_v2.application.startup import bootstrap as startup_bootstrap
from dpost_v2.application.startup.bootstrap import BootstrapRequest

# Backward-compatible symbols for legacy test expectations and external patch points.
BootstrapResult = startup_bootstrap.BootstrapResult


def run(*, request: BootstrapRequest, emit_event, **kwargs) -> BootstrapResult:
    """Delegate to the configured bootstrap run implementation."""
    return startup_bootstrap.run(request=request, emit_event=emit_event, **kwargs)


_SUPPORTED_MODES = frozenset({"v2"})
_RUNTIME_FAILURE_TERMINALS = frozenset({"failed_terminal", "hard_timeout"})
_RUNTIME_SUCCESS_TERMINALS = frozenset({"end_of_stream", "cancelled", "soft_timeout"})


class UnsupportedRuntimeModeError(ValueError):
    """Raised when CLI/environment mode token is unsupported."""


class RuntimeContractError(RuntimeError):
    """Raised when runtime handle/result violates required execution contract."""


@dataclass(frozen=True, slots=True)
class CliOptions:
    """Normalized startup options derived from CLI arguments and environment."""

    mode: str
    profile: str | None
    config_path: str | None
    headless: bool
    dry_run: bool


def main(argv: Sequence[str] | None = None) -> int:
    """Parse startup arguments, run bootstrap orchestration, and map exit codes."""
    try:
        options = _parse_cli(argv)
    except SystemExit as exc:
        return _coerce_system_exit_code(exc.code)
    except UnsupportedRuntimeModeError as exc:
        print(f"Unsupported runtime mode: {exc}", file=sys.stderr)
        return 2

    request = _build_bootstrap_request(options)

    try:
        result = run(request=request, emit_event=_emit_startup_event)
    except KeyboardInterrupt:
        print("Startup interrupted by user.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Startup bootstrap failed: {exc}", file=sys.stderr)
        return 1

    if result.is_success and options.dry_run:
        print(
            f"dpost startup succeeded (mode={request.mode}, profile={request.profile or 'default'})."
        )
        return 0
    if result.is_success:
        runtime_exit_code = _execute_runtime(result.runtime_handle)
        if runtime_exit_code != 0:
            return runtime_exit_code
        print(
            f"dpost startup succeeded (mode={request.mode}, profile={request.profile or 'default'})."
        )
        return 0

    failure = result.failure
    if failure is None:
        print("dpost startup failed with unknown error.", file=sys.stderr)
        return 1

    print(
        (
            "dpost startup failed "
            f"(stage={failure.stage}, error={failure.error_type}): {failure.message}"
        ),
        file=sys.stderr,
    )
    return 1


def _parse_cli(argv: Sequence[str] | None) -> CliOptions:
    parser = _build_parser()
    parsed = parser.parse_args(list(argv) if argv is not None else None)

    mode = parsed.mode or os.getenv("DPOST_MODE", "v2")
    if mode not in _SUPPORTED_MODES:
        raise UnsupportedRuntimeModeError(mode)

    profile = parsed.profile or _normalized_env("DPOST_PROFILE")
    config_path = parsed.config or _normalized_env("DPOST_CONFIG")

    return CliOptions(
        mode=mode,
        profile=profile,
        config_path=config_path,
        headless=bool(parsed.headless),
        dry_run=bool(parsed.dry_run),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dpost")
    parser.add_argument(
        "--mode",
        choices=tuple(sorted(_SUPPORTED_MODES)),
        default=None,
        help="Runtime architecture mode (v2 only).",
    )
    parser.add_argument("--profile", default=None, help="Startup settings profile.")
    parser.add_argument(
        "--config",
        default=None,
        help="Optional config file path passed as metadata to startup services.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Request headless startup behavior.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Request dry-run startup behavior.",
    )
    return parser


def _normalized_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _build_bootstrap_request(options: CliOptions) -> BootstrapRequest:
    metadata: Mapping[str, object] = {
        "config_path": options.config_path,
        "headless": options.headless,
        "dry_run": options.dry_run,
    }
    return BootstrapRequest(
        mode=options.mode,
        profile=options.profile,
        trace_id=uuid.uuid4().hex,
        metadata=metadata,
    )


def _coerce_system_exit_code(code: object) -> int:
    if code is None:
        return 0
    try:
        return int(code)
    except (TypeError, ValueError):
        return 1


def _execute_runtime(runtime_handle: object) -> int:
    try:
        run_callable = _resolve_runtime_run_callable(runtime_handle)
    except RuntimeContractError as exc:
        print(f"dpost runtime contract violation: {exc}", file=sys.stderr)
        return 1

    try:
        run_result = run_callable()
    except KeyboardInterrupt:
        print("Runtime interrupted by user.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"dpost runtime failed: {exc}", file=sys.stderr)
        return 1

    try:
        terminal_reason = _resolve_terminal_reason(run_result)
    except RuntimeContractError as exc:
        print(f"dpost runtime contract violation: {exc}", file=sys.stderr)
        return 1

    if terminal_reason in _RUNTIME_FAILURE_TERMINALS:
        print(f"dpost runtime failed (reason={terminal_reason}).", file=sys.stderr)
        return 1
    if terminal_reason in _RUNTIME_SUCCESS_TERMINALS:
        return 0

    print(
        f"dpost runtime contract violation: unsupported terminal_reason {terminal_reason!r}",
        file=sys.stderr,
    )
    return 1


def _resolve_runtime_run_callable(runtime_handle: object) -> Callable[[], Any]:
    run_callable = getattr(runtime_handle, "run", None)
    if not callable(run_callable):
        raise RuntimeContractError("runtime handle must provide callable run()")
    return run_callable


def _resolve_terminal_reason(run_result: object) -> str:
    terminal_reason = getattr(run_result, "terminal_reason", None)
    if not isinstance(terminal_reason, str) or not terminal_reason.strip():
        raise RuntimeContractError("runtime result missing terminal_reason")
    return terminal_reason.strip().lower()


def _emit_startup_event(event: startup_bootstrap.StartupEvent) -> None:
    if event.name == "startup_failed":
        stage = event.payload.get("stage", "unknown")
        message = event.payload.get("message", "unknown startup failure")
        print(f"startup_event failure stage={stage}: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
