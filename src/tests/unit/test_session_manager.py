import pytest
from unittest.mock import MagicMock

from src.sessions.session_manager import SessionManager
from src.config.settings import SESSION_TIMEOUT


@pytest.fixture
def dummy_ui():
    """
    Provides a dummy UI that simulates the UserInterface.
    The schedule_task method returns a fixed dummy timer ID.
    """
    ui = MagicMock()
    ui.schedule_task.return_value = "dummy_timer"
    return ui


def test_start_session(dummy_ui):
    """
    When start_session() is called on an inactive session,
    it should mark the session as active, schedule a timeout task,
    and show the done dialog.
    """
    session_manager = SessionManager(ui=dummy_ui)
    # Initial state: inactive, no timer scheduled.
    assert not session_manager.session_active
    assert session_manager.timer_id is None

    # Start the session.
    session_manager.start_session()

    # The session should now be active.
    assert session_manager.session_active is True

    # A timeout should be scheduled with SESSION_TIMEOUT * 1000 ms.
    dummy_ui.schedule_task.assert_called_with(
        SESSION_TIMEOUT * 1000, session_manager.end_session
    )

    # A done dialog should be shown (its argument is a callable).
    dummy_ui.show_done_dialog.assert_called()

    # The timer_id should be updated.
    assert session_manager.timer_id == "dummy_timer"


def test_end_session(dummy_ui):
    """
    When end_session() is invoked on an active session,
    it should mark the session inactive, cancel the timer,
    and invoke the end-session callback if provided.
    """
    dummy_callback = MagicMock()
    session_manager = SessionManager(ui=dummy_ui, end_session_callback=dummy_callback)
    session_manager.session_active = True
    session_manager.timer_id = "dummy_timer"

    # End the session.
    session_manager.end_session()

    # The session should be inactive.
    assert session_manager.session_active is False

    # The timer should be cancelled.
    dummy_ui.cancel_task.assert_called_with("dummy_timer")
    assert session_manager.timer_id is None

    # The end-session callback should be called.
    dummy_callback.assert_called_once()


def test_reset_timer_when_session_active(dummy_ui):
    """
    If the session is active and reset_timer() is called,
    the existing timer is cancelled and a new one is scheduled.
    """
    session_manager = SessionManager(ui=dummy_ui)
    session_manager.session_active = True
    session_manager.timer_id = "old_timer"

    # Call reset_timer.
    session_manager.reset_timer()

    # The old timer should be cancelled.
    dummy_ui.cancel_task.assert_called_with("old_timer")

    # A new timeout should be scheduled.
    dummy_ui.schedule_task.assert_called_with(
        SESSION_TIMEOUT * 1000, session_manager.end_session
    )

    # Timer id should be updated.
    assert session_manager.timer_id == "dummy_timer"


def test_reset_timer_when_session_inactive(dummy_ui):
    """
    If the session is inactive, reset_timer() should do nothing.
    """
    session_manager = SessionManager(ui=dummy_ui)
    session_manager.session_active = False
    session_manager.timer_id = "old_timer"

    # Call reset_timer.
    session_manager.reset_timer()

    # schedule_task should not be called.
    dummy_ui.schedule_task.assert_not_called()

    # Timer id remains unchanged.
    assert session_manager.timer_id == "old_timer"
