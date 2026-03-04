"""CLI bridge that keeps the `dpost` command bound to V2 startup."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from dpost_v2.__main__ import main as run_v2

_RETIRED_MODES = frozenset({"v1", "shadow"})


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to V2 startup and reject retired runtime mode tokens."""
    args = list(sys.argv[1:] if argv is None else argv)
    if _requests_help(args):
        _build_parser().print_help()
        return 0

    mode, has_mode_flag = _extract_mode(args)

    if mode in _RETIRED_MODES:
        print(
            f"Unsupported runtime mode: {mode}. Supported mode is 'v2'.",
            file=sys.stderr,
        )
        return 2

    if not has_mode_flag:
        args = ["--mode", "v2", *args]

    return run_v2(args)


def _requests_help(args: Sequence[str]) -> bool:
    return any(token in {"-h", "--help"} for token in args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dpost")
    parser.add_argument(
        "--mode",
        choices=("v2",),
        default="v2",
        help="Runtime architecture mode (v2).",
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


def _extract_mode(args: Sequence[str]) -> tuple[str | None, bool]:
    for index, token in enumerate(args):
        if token == "--mode":
            if index + 1 >= len(args):
                return None, True
            return args[index + 1], True
        if token.startswith("--mode="):
            return token.split("=", 1)[1], True
    return None, False


if __name__ == "__main__":
    raise SystemExit(main())
