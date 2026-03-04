"""V2 executable entrypoint with explicit startup bootstrap dispatch."""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Mapping, Sequence

from dpost_v2.application.startup import bootstrap as startup_bootstrap
from dpost_v2.application.startup.bootstrap import BootstrapRequest

_SUPPORTED_MODES = frozenset({"v1", "v2", "shadow"})


class UnsupportedRuntimeModeError(ValueError):
    """Raised when CLI/environment mode token is unsupported."""


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
        return int(exc.code)
    except UnsupportedRuntimeModeError as exc:
        print(f"Unsupported runtime mode: {exc}", file=sys.stderr)
        return 2

    request = _build_bootstrap_request(options)

    try:
        result = startup_bootstrap.run(request=request, emit_event=_emit_startup_event)
    except KeyboardInterrupt:
        print("Startup interrupted by user.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Startup bootstrap failed: {exc}", file=sys.stderr)
        return 1

    if result.is_success:
        print(
            f"dpost_v2 startup succeeded (mode={request.mode}, profile={request.profile or 'default'})."
        )
        return 0

    failure = result.failure
    if failure is None:
        print("dpost_v2 startup failed with unknown error.", file=sys.stderr)
        return 1

    print(
        (
            "dpost_v2 startup failed "
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
    parser = argparse.ArgumentParser(prog="dpost_v2")
    parser.add_argument(
        "--mode",
        choices=tuple(sorted(_SUPPORTED_MODES)),
        default=None,
        help="Runtime architecture mode (v1, v2, shadow).",
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


def _emit_startup_event(event: startup_bootstrap.StartupEvent) -> None:
    if event.name == "startup_failed":
        stage = event.payload.get("stage", "unknown")
        message = event.payload.get("message", "unknown startup failure")
        print(f"startup_event failure stage={stage}: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
