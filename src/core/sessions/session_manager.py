from src.core.config.settings_store import SettingsStore
from src.core.config.settings_base import BaseSettings
from src.core.app.logger import setup_logger
from src.core.ui.ui_abstract import UserInterface

logger = setup_logger(__name__)


class SessionManager:
    """
    Manages the lifecycle of a user session, including timeouts and session state.
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
        self.settings: BaseSettings = SettingsStore.get()

    @property
    def is_active(self) -> bool:
        return self.session_active

    def start_session(self):
        if not self.session_active:
            logger.debug("Starting a new session.")
            self.session_active = True
            self._schedule_timeout()
            self.ui.show_done_dialog(self.end_session)

    def end_session(self):
        if self.session_active:
            logger.debug("Ending the current session.")
            self.session_active = False
            self._cancel_timer()
            if self.end_session_callback:
                self.end_session_callback()

    def reset_timer(self):
        if self.session_active:
            logger.debug("Resetting session timeout timer.")
            self._schedule_timeout()

    def _schedule_timeout(self):
        self._cancel_timer()
        timeout_ms = self.settings.SESSION_TIMEOUT * 1000  # ✅ pulled from settings
        self.timer_id = self.ui.schedule_task(timeout_ms, self.end_session)

    def _cancel_timer(self):
        if self.timer_id is not None:
            self.ui.cancel_task(self.timer_id)
            self.timer_id = None
