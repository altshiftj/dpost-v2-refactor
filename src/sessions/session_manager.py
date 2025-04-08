from src.config.settings import SESSION_TIMEOUT
from src.app.logger import setup_logger
from src.ui.ui_abstract import UserInterface

logger = setup_logger(__name__)


class SessionManager:
    """
    Manages the lifecycle of a user session, including timeouts and session state.
    This class tracks active sessions and schedules timeouts to automatically end sessions
    after a period of inactivity.
    """

    def __init__(self, ui: UserInterface, end_session_callback=None):
        """
        Initializes a new SessionManager.

        :param ui: A UserInterface implementation for scheduling/canceling tasks and showing dialogs.
        :param end_session_callback: Optional callback function executed when a session ends.
        """
        self.ui = ui
        self.end_session_callback = end_session_callback
        self.session_active = False
        self.timer_id = None

    @property
    def is_active(self) -> bool:
        """Read-only property for checking if the session is active."""
        return self.session_active

    def start_session(self):
        """
        Starts a new session if one is not already active. This method marks the session as active,
        schedules a timeout, and shows a 'done' dialog for the user.
        """
        if not self.session_active:
            logger.debug("Starting a new session.")
            self.session_active = True
            self._schedule_timeout()
            # Directly pass self.end_session since it requires no arguments.
            self.ui.show_done_dialog(self.end_session)

    def end_session(self):
        """
        Ends the current session by marking it inactive, canceling any pending timeout,
        and executing the end-session callback if provided.
        """
        if self.session_active:
            logger.debug("Ending the current session.")
            self.session_active = False
            self._cancel_timer()
            if self.end_session_callback:
                self.end_session_callback()

    def reset_timer(self):
        """
        Resets the session timeout timer if a session is active. This cancels the existing timeout
        and schedules a new one.
        """
        if self.session_active:
            logger.debug("Resetting session timeout timer.")
            self._schedule_timeout()

    def _schedule_timeout(self):
        """
        Cancels any existing timeout and schedules a new one to end the session after SESSION_TIMEOUT seconds.
        """
        self._cancel_timer()
        self.timer_id = self.ui.schedule_task(SESSION_TIMEOUT * 1000, self.end_session)

    def _cancel_timer(self):
        """
        Cancels the currently scheduled timeout, if any.
        """
        if self.timer_id is not None:
            self.ui.cancel_task(self.timer_id)
            self.timer_id = None
