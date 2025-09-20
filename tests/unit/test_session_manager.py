import pytest
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.config import current
from ipat_watchdog.core.records.local_record import LocalRecord


def _make_record(identifier: str = "udr_01-mus-ipat-sample_a") -> LocalRecord:
    return LocalRecord(identifier=identifier)



def test_start_session(fake_ui, config_service):
    """When start_session() is called on an inactive session it should schedule a timeout."""
    fake_ui.auto_close_session = False
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    assert not session_manager.session_active
    assert session_manager.timer_id is None

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 1  # HeadlessUI returns task handle as int




def test_note_activity_starts_session(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    record = _make_record()

    session_manager.note_activity(record)

    assert session_manager.session_active is True
    assert fake_ui.session_details_history[-1].users == ("mus-ipat",)
    assert fake_ui.session_details_history[-1].records == (f"{record.sample_name} (Files: 1)",)


def test_note_activity_refreshes_timer_and_details(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    first = _make_record("udr_01-mus-ipat-sample_a")
    second = _make_record("udr_01-mus-ipat-sample_b")

    session_manager.note_activity(first)
    session_manager.note_activity(second)

    assert len(fake_ui.session_details_history) == 2
    latest = fake_ui.session_details_history[-1]
    assert latest.users == ("mus-ipat",)
    assert latest.records == (
        f"{first.sample_name} (Files: 1)",
        f"{second.sample_name} (Files: 1)",
    )
    assert fake_ui.scheduled_tasks[-1][0] == current().session_timeout * 1000


def test_note_activity_tracks_multiple_users(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    primary = _make_record("udr_01-mus-ipat-sample_a")
    secondary = _make_record("udr_01-jfi-ipat-sample_b")

    session_manager.note_activity(primary)
    session_manager.note_activity(secondary)
    session_manager.note_activity(primary)

    latest = fake_ui.session_details_history[-1]
    assert latest.users == ("mus-ipat", "jfi-ipat")
    assert latest.records == (
        f"{primary.sample_name} (Files: 2)",
        f"{secondary.sample_name} (Files: 1)",
    )


def test_note_activity_counts_increment(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    record = _make_record("udr_01-mus-ipat-sample_a")

    session_manager.note_activity(record)
    session_manager.note_activity(record)

    latest = fake_ui.session_details_history[-1]
    assert latest.records == (f"{record.sample_name} (Files: 2)",)


def test_end_session_calls_callback(fake_ui, config_service):
    ended = []

    def on_done():
        ended.append(True)

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, end_session_callback=on_done)
    session_manager.session_active = True
    session_manager.timer_id = 1

    session_manager.end_session()

    assert session_manager.session_active is False
    assert session_manager.timer_id is None
    assert ended == [True]


def test_reset_timer_reschedules(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True
    session_manager.timer_id = 1

    session_manager.reset_timer()

    assert session_manager.timer_id == 2
    assert fake_ui.scheduled_tasks[-1][0] == current().session_timeout * 1000


def test_reset_timer_when_inactive_does_nothing(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = False
    session_manager.timer_id = None

    session_manager.reset_timer()

    assert session_manager.timer_id is None
    assert fake_ui.scheduled_tasks == []


def test_auto_end_session(fake_ui, config_service):
    fake_ui.auto_close_session = True
    ended = []

    def on_done():
        ended.append(True)

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, end_session_callback=on_done)
    session_manager.start_session()

    assert session_manager.session_active is False
    assert ended == [True]

def test_start_session_noop_when_already_active(fake_ui, config_service):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True
    session_manager.timer_id = 5

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 5
    assert fake_ui.scheduled_tasks == []


def test_reset_timer_ignores_disabled_timeout(fake_ui, monkeypatch):
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True

    stub = type("StubConfig", (), {"session_timeout": -1})()
    monkeypatch.setattr("ipat_watchdog.core.session.session_manager.current", lambda: stub)

    session_manager.reset_timer()

    assert session_manager.timer_id is None
    assert fake_ui.scheduled_tasks == []
