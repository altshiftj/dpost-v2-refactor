import tkinter as tk
from abc import ABC, abstractmethod
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class SessionManagerInterface(ABC):
    @abstractmethod
    def start_session(self):
        pass

    @abstractmethod
    def reset_timer(self):
        pass

    @abstractmethod
    def end_session(self):
        pass

    @abstractmethod
    def cancel(self):
        pass

    @property
    @abstractmethod
    def session_active(self) -> bool:
        pass


class SessionManager(SessionManagerInterface):
    def __init__(self, session_timeout, end_session_callback, root: tk.Tk):
        self.session_timeout = session_timeout * 1000  # milliseconds
        self._session_active = False
        self.end_session_callback = end_session_callback
        self.root = root
        self.session_timer_id = None

    @property
    def session_active(self) -> bool:
        return self._session_active

    def start_session(self):
        if not self._session_active:
            self._session_active = True
            logger.info("Session started.")
            self.start_timer()

    def start_timer(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
        self.session_timer_id = self.root.after(self.session_timeout, self.end_session)
        logger.info("Session timer started/restarted.")

    def reset_timer(self):
        if self._session_active:
            self.start_timer()

    def end_session(self):
        if not self._session_active:
            logger.warning("SessionManager.end_session called but session already ended. Skipping.")
            return
        self._session_active = False
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
        logger.info("Session ended.")
        # Call the callback exactly once
        self.end_session_callback()

    def cancel(self):
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
