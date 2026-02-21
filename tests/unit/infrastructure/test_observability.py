from __future__ import annotations

import builtins
import threading

from dpost.infrastructure import observability


def test_health_endpoint_ok():
    client = observability.app.test_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_logs_returns_404_when_missing(monkeypatch, tmp_path):
    missing = tmp_path / "missing.log"
    monkeypatch.setattr(observability, "LOG_PATH", str(missing))

    client = observability.app.test_client()
    response = client.get("/logs")

    assert response.status_code == 404


def test_logs_invalid_tail(monkeypatch, tmp_path):
    log_path = tmp_path / "watchdog.log"
    log_path.write_text("{}\n")
    monkeypatch.setattr(observability, "LOG_PATH", str(log_path))

    client = observability.app.test_client()
    response = client.get("/logs?tail=abc")

    assert response.status_code == 400


def test_logs_renders_json_and_raw_lines(monkeypatch, tmp_path):
    log_path = tmp_path / "watchdog.log"
    log_path.write_text('{"msg": "one"}\nraw line\n')
    monkeypatch.setattr(observability, "LOG_PATH", str(log_path))

    client = observability.app.test_client()
    response = client.get("/logs")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "&#34;msg&#34;" in body
    assert "raw line" in body


def test_logs_tail_truncates(monkeypatch, tmp_path):
    log_path = tmp_path / "watchdog.log"
    log_path.write_text('{"msg": "one"}\nraw line\n')
    monkeypatch.setattr(observability, "LOG_PATH", str(log_path))

    client = observability.app.test_client()
    response = client.get("/logs?tail=1")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "raw line" in body
    assert "&#34;msg&#34;" not in body


def test_logs_returns_500_when_log_read_fails(monkeypatch, tmp_path):
    log_path = tmp_path / "watchdog.log"
    log_path.write_text("{}\n")
    monkeypatch.setattr(observability, "LOG_PATH", str(log_path))
    monkeypatch.setattr(observability.os.path, "exists", lambda _path: True)

    real_open = builtins.open

    def _failing_open(*args, **kwargs):  # type: ignore[no-untyped-def]
        if args and args[0] == str(log_path):
            raise OSError("denied")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", _failing_open)

    client = observability.app.test_client()
    response = client.get("/logs")
    body = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "Failed to read log" in body


def test_start_observability_server_spawns_thread(monkeypatch):
    called = threading.Event()

    def fake_serve(*args, **kwargs):
        called.set()

    monkeypatch.setattr(observability, "serve", fake_serve)

    thread = observability.start_observability_server(host="127.0.0.1", port=8123, threads=1)
    thread.join(timeout=2)

    assert called.is_set()
    assert thread.daemon is True
