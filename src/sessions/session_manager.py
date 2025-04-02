"""
session_manager.py

This module contains classes for managing user sessions within the application.
It tracks session state, handles timeouts, and provides mechanisms for starting
and ending sessions.
"""

from src.config.settings import SESSION_TIMEOUT
from src.app.logger import setup_logger
from src.ui.ui_abstract import UserInterface

logger = setup_logger(__name__)

class SessionManager:
    """
    Manages the lifecycle of a user session, including timeouts and session state.
    This class is responsible for tracking the active state of a session and
    scheduling timeouts to automatically end sessions after a period of inactivity.
    """

    def __init__(self, ui: UserInterface, end_session_callback=None):
        """
        Initializes a new SessionManager.
        
        :param ui: A UserInterface implementation for scheduling/canceling tasks and showing dialogs.
        :param end_session_callback: Optional callback function to be executed when a session ends.
        """
        self.ui = ui
        self.end_session_callback = end_session_callback
        self.session_active = False

        # Holds a handle to the scheduled timeout task, if any
        self.timer_id = None

    def start_session(self):
        """
        Starts a new session or resets the current session's timeout.
        If a session is already active, this method does nothing.
        """
        if not self.session_active:
            logger.debug("Starting a new session.")
            self.session_active = True
            self._schedule_timeout()

            # Show the done dialog, passing the end_session method
            # We wrap it in a lambda to make it a zero-argument callable
            self.ui.show_done_dialog(lambda: self.end_session())

    def end_session(self):
        """
        Ends the current session, cancels any pending timeout,
        and executes the end_session_callback if provided.
        """
        if self.session_active:
            logger.debug("Ending the current session.")
            self.session_active = False

            # Cancel the timeout task if it exists
            if self.timer_id is not None:
                self.ui.cancel_task(self.timer_id)
                self.timer_id = None

            # Execute the callback if provided
            if self.end_session_callback:
                self.end_session_callback()

    def reset_timer(self):
        """
        Resets the session timeout timer if a session is active.
        This extends the session by canceling the current timeout and scheduling a new one.
        """
        if self.session_active:
            logger.debug("Resetting session timeout timer.")
            self._schedule_timeout()

    def _schedule_timeout(self):
        """
        Schedules a timeout to automatically end the session after SESSION_TIMEOUT seconds.
        If a timeout is already scheduled, it is canceled first.
        """
        # Cancel any existing timer
        if self.timer_id is not None:
            self.ui.cancel_task(self.timer_id)
            self.timer_id = None

        # Schedule a new timeout
        self.timer_id = self.ui.schedule_task(SESSION_TIMEOUT * 1000, self.end_session)
