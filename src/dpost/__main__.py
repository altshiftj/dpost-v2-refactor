"""Executable entry point for the dpost application."""

from __future__ import annotations

import sys

from dpost.infrastructure.logging import setup_logger
from dpost.runtime.bootstrap import MissingConfiguration, StartupError
from dpost.runtime.composition import compose_bootstrap

logger = setup_logger(__name__)


def main() -> int:
    """Start dpost and return a process exit code."""
    try:
        context = compose_bootstrap()
    except MissingConfiguration as exc:
        logger.error("Configuration error: %s", exc)
        return 1
    except StartupError as exc:
        logger.exception("Failed to bootstrap application: %s", exc)
        return 1

    try:
        context.app.run()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Application terminated unexpectedly: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
