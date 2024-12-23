"""
session_controller.py

This module defines the SessionController class, which manages user sessions within the application.
It interacts with the SessionManager to handle session states and uses the UserInterface to provide
feedback to the user through GUI dialogs.
"""

from src.sessions.session_manager import SessionManager
from src.gui.gui_manager import UserInterface
from src.app.logger import setup_logger

logger = setup_logger(__name__)

class SessionController:
    """
    The SessionController class oversees the management of user sessions by coordinating
    between the SessionManager and the UserInterface. It ensures that sessions are
    properly started, maintained, and terminated based on user interactions and
    application events.
    
    Key Responsibilities:
        - Initiating new user sessions.
        - Resetting session timers to prevent unintended session timeouts.
        - Displaying dialogs to inform users about the session status.
    """

    def __init__(self, session_manager: SessionManager, ui: UserInterface):
        """
        Initializes the SessionController with the necessary components.
        
        :param session_manager: An instance of SessionManager that handles the logic
                                related to starting, ending, and tracking session states.
        :param ui: An instance of UserInterface responsible for displaying dialogs and
                   messages to the user.
        """
        self.session_manager = session_manager  # Manages the session lifecycle
        self.ui = ui                            # Handles GUI interactions
    
    def manage_session(self):
        """
        Manages the current user session based on its active state.
        
        - If no session is active, it starts a new session and displays a "Done" dialog
          to the user, allowing them to end the session when finished.
        - If a session is already active, it resets the session timer to extend the session
          duration, preventing it from timing out due to inactivity.
        """
        if not self.session_manager.session_active:
            # No active session; start a new one
            self.session_manager.start_session()
            # Show a dialog informing the user that the session is active and can be ended
            self.ui.show_done_dialog(self.session_manager)
            logger.debug("Started a new session and displayed the 'Done' dialog.")
        else:
            # Session is active; reset the timer to extend the session
            self.session_manager.reset_timer()
            logger.debug("Session is active. Timer has been reset to extend the session.")
