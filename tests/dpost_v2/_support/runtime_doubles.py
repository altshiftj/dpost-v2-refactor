"""Runtime doubles used by V2 harness and smoke tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable


def build_recording_factories(
    port_names: Iterable[str],
    *,
    call_log: list[str],
    adapter_builder: Callable[[str], object] | None = None,
) -> dict[str, Callable[[], object]]:
    """Return adapter factories that append each initialized port to ``call_log``."""
    build_adapter = adapter_builder or (lambda port: {"port": port})
    factories: dict[str, Callable[[], object]] = {}
    for port_name in port_names:

        def _factory(current_port: str = port_name) -> object:
            call_log.append(current_port)
            return build_adapter(current_port)

        factories[port_name] = _factory
    return factories


def make_lifecycle_adapter(
    name: str,
    *,
    call_log: list[str],
    hook_name: str = "shutdown",
) -> object:
    """Create an adapter exposing one lifecycle hook supported by composition."""
    if hook_name not in {"shutdown", "close", "stop"}:
        raise ValueError(f"unsupported lifecycle hook: {hook_name}")

    class _Adapter:
        pass

    adapter = _Adapter()

    def _hook() -> None:
        call_log.append(name)

    setattr(adapter, hook_name, _hook)
    return adapter
