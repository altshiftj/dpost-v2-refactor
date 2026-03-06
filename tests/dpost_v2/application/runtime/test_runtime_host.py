from __future__ import annotations

from dataclasses import dataclass

from dpost_v2.application.runtime.runtime_host import RuntimeHost


@dataclass
class FakeApp:
    result: object

    def __post_init__(self) -> None:
        self.run_calls = 0

    def run(self) -> object:
        self.run_calls += 1
        return self.result


def test_runtime_host_delegates_run_to_app() -> None:
    app = FakeApp(result={"terminal_reason": "end_of_stream"})
    host = RuntimeHost(app=app)

    result = host.run()

    assert result == {"terminal_reason": "end_of_stream"}
    assert app.run_calls == 1
    assert host.app is app


def test_runtime_host_shutdown_is_idempotent() -> None:
    shutdown_calls: list[str] = []
    host = RuntimeHost(
        app=FakeApp(result=None),
        shutdown_hook=lambda: shutdown_calls.append("shutdown"),
    )

    host.shutdown()
    host.shutdown()

    assert shutdown_calls == ["shutdown"]
