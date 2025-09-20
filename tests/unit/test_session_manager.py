import pytest
from ipat_watchdog.core.session.session_manager import SessionManager
from ipat_watchdog.core.config import current


def test_start_session(fake_ui, config_service):
    """When start_session() is called on an inactive session it should schedule a timeout."""
    fake_ui.auto_close_session = False
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    assert not session_manager.session_active
    assert session_manager.timer_id is None

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 1  # HeadlessUI returns task handle as int


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
