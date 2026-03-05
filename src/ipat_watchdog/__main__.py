"""Executable entry point for the Watchdog application."""

from __future__ import annotations

import sys

from ipat_watchdog.core.app.bootstrap import (
    MissingConfiguration,
    StartupError,
    bootstrap,
)
from ipat_watchdog.core.logging.logger import setup_logger

logger = setup_logger(__name__)


def main() -> int:
    try:
        context = bootstrap()
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
