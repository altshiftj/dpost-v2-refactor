"""
session_manager.py

Handles user session management, including tracking session states,
enforcing timeouts, and triggering callbacks upon session termination.
Integrates with Tkinter's event loop for scheduling session-related actions.
"""

import tkinter as tk

from src.config.settings import SESSION_TIMEOUT
from src.app.logger import setup_logger

logger = setup_logger(__name__)

<<<<<<< HEAD
=======

>>>>>>> ref-sqlpersistence
class SessionManager:
    """
    Manages user sessions by tracking their active state, handling session timeouts,
    and invoking callbacks when sessions end.
    
    Attributes:
        session_timeout (int): Duration in milliseconds before a session times out.
        _session_active (bool): Indicates if a session is currently active.
        end_session_callback (callable): Function to call when a session ends.
        root (tk.Tk): Reference to the Tkinter root window for scheduling timers.
        session_timer_id (str or int): Identifier for the scheduled session timer.
    """

    def __init__(self, root: tk.Tk, end_session_callback):
        """
        Initializes the SessionManager.

        Args:
            root (tk.Tk): The main Tkinter root window.
            end_session_callback (callable): Callback to execute when the session ends.
        """
        self.session_timeout = SESSION_TIMEOUT * 1000  # Convert to milliseconds
        self._session_active = False
        self.end_session_callback = end_session_callback
        self.root = root
        self.session_timer_id = None

    @property
    def session_active(self) -> bool:
        """Returns True if a session is active, False otherwise."""
        return self._session_active

    def start_session(self):
        """
        Starts a new session if none is active and initiates the session timer.
        """
        if not self._session_active:
            self._session_active = True
            logger.info("Session started.")
            self.start_timer()
        else:
            logger.debug("Session already active. No action taken.")

    def start_timer(self):
        """
        Starts or restarts the session timeout timer.
        Cancels any existing timer before starting a new one.
        """
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            logger.debug("Existing session timer canceled.")

        self.session_timer_id = self.root.after(self.session_timeout, self.end_session)
        logger.debug("Session timer started with timeout of %d ms.", self.session_timeout)

    def reset_timer(self):
        """
        Resets the session timeout timer to extend the active session.
        """
        if self._session_active:
            self.start_timer()
            logger.debug("Session timer reset to extend session.")
        else:
            logger.debug("No active session to reset timer for.")

    def end_session(self):
        """
        Ends the current session, cancels the timer, and invokes the callback.
        """
        if not self._session_active:
            logger.warning("end_session called but no active session exists.")
            return

        self._session_active = False

        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
            logger.debug("Session timer canceled upon ending session.")

        logger.debug("Session ended.")
        self.end_session_callback()

    def cancel(self):
        """
        Cancels the active session timer without ending the session.
        Useful for cleanup during application shutdown.
        """
        if self.session_timer_id is not None:
            self.root.after_cancel(self.session_timer_id)
            self.session_timer_id = None
            logger.debug("Session timer canceled via cancel method.")
        else:
            logger.debug("No active session timer to cancel.")
<<<<<<< HEAD
=======

    def check_session_active_state(self):
        """
        Manages the current user session based on its active state.
        
        - If no session is active, it starts a new session and displays a "Done" dialog
          to the user, allowing them to end the session when finished.
        - If a session is already active, it resets the session timer to extend the session
          duration, preventing it from timing out due to inactivity.
        """
        if not self.session_active:
            # No active session; start a new one
            self.start_session()
            # Show a dialog informing the user that the session is active and can be ended
            self.ui.show_done_dialog(self.session_manager)
            logger.debug("Started a new session and displayed the 'Done' dialog.")
        else:
            # Session is active; reset the timer to extend the session
            self.session_manager.reset_timer()
            logger.debug("Session is active. Timer has been reset to extend the session.")

>>>>>>> ref-sqlpersistence
