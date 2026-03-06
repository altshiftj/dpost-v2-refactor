"""Runtime host lifecycle surface for V2 execution."""

from __future__ import annotations

from typing import Any, Callable


class RuntimeHost:
    """Canonical lifecycle owner for a runnable V2 runtime app."""

    def __init__(
        self,
        *,
        app: object,
        shutdown_hook: Callable[[], None] | None = None,
    ) -> None:
        self.app = app
        self._shutdown_hook = shutdown_hook
        self._shutdown_completed = False

    def run(self) -> Any:
        """Delegate execution to the hosted runtime app."""
        run_callable = getattr(self.app, "run", None)
        if not callable(run_callable):
            raise RuntimeError("runtime app must provide callable run()")
        return run_callable()

    def shutdown(self) -> None:
        """Release runtime-owned adapters exactly once."""
        if self._shutdown_completed:
            return
        self._shutdown_completed = True
        if self._shutdown_hook is not None:
            self._shutdown_hook()
