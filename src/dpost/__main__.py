"""Canonical CLI entrypoint that delegates to the V2 implementation."""

from __future__ import annotations

from typing import Sequence

from dpost_v2.__main__ import main as _run_v2


def main(argv: Sequence[str] | None = None) -> int:
    return _run_v2(argv)


if __name__ == "__main__":
    raise SystemExit(main())
