import pytest
from ipat_watchdog.core.session.session_manager import SessionManager


def test_start_session(fake_ui, tmp_settings):
    """
    When start_session() is called on an inactive session,
    it should mark the session as active, schedule a timeout task,
    and show the done dialog — but not end the session unless the user says so.
    """
    fake_ui.auto_close_session = False  # Control when session ends
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)

    assert not session_manager.session_active
    assert session_manager.timer_id is None

    session_manager.start_session()

    assert session_manager.session_active is True
    assert session_manager.timer_id == 1  # HeadlessUI returns task handle as int


def test_end_session_calls_callback(fake_ui, tmp_settings):
    """
    When end_session() is called, the session should deactivate,
    cancel its timer, and invoke the callback.
    """
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


def test_reset_timer_reschedules(fake_ui, tmp_settings):
    # Ensure device context is set for settings manager
    from ipat_watchdog.core.config.settings_store import SettingsStore
    settings_manager = SettingsStore.get_manager()
    if hasattr(settings_manager, '_devices'):
        for device in settings_manager._devices.values():
            if device.get_device_id() == "test_device":
                settings_manager.set_current_device(device)
                break

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = True
    session_manager.timer_id = 1

    session_manager.reset_timer()

    assert session_manager.timer_id == 2
    assert fake_ui.scheduled_tasks[-1][0] == tmp_settings.SESSION_TIMEOUT * 1000


def test_reset_timer_when_inactive_does_nothing(fake_ui, tmp_settings):
    """
    When reset_timer() is called on an inactive session, it should not schedule anything.
    """
    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui)
    session_manager.session_active = False
    session_manager.timer_id = None

    session_manager.reset_timer()

    assert session_manager.timer_id is None
    assert fake_ui.scheduled_tasks == []


def test_auto_end_session(fake_ui, tmp_settings):
    """
    If HeadlessUI is set to auto-close sessions, start_session() should immediately end it.
    """
    fake_ui.auto_close_session = True
    ended = []

    def on_done():
        ended.append(True)

    session_manager = SessionManager(interactions=fake_ui, scheduler=fake_ui, end_session_callback=on_done)
    session_manager.start_session()

    assert session_manager.session_active is False
    assert ended == [True]
