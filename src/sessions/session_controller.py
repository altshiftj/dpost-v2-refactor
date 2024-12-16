from src.sessions.session_manager import SessionManagerInterface
from src.gui.gui_manager import UserInterface

class SessionController:
    def __init__(self, session_manager: SessionManagerInterface, ui: UserInterface):
        self.session_manager = session_manager
        self.ui = ui

    def manage_session(self):
        if not self.session_manager.session_active:
            self.session_manager.start_session()
            self.ui.show_done_dialog(self.session_manager)
        else:
            self.session_manager.reset_timer()
