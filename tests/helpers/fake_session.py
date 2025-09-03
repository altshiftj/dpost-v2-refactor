class FakeSessionManager:
    def __init__(self, ui=None, end_session_callback=None):
        self.session_active = False
        self.started = False
        self.ended = False
        self.end_session_callback = end_session_callback
        self.start_session_called = False
        self.reset_timer_called = False

    def start_session(self):
        self.session_active = True
        self.started = True
        self.start_session_called = True

    def end_session(self):
        self.session_active = False
        self.ended = True
        if self.end_session_callback:
            self.end_session_callback()

    def reset_timer(self):
        self.reset_timer_called = True