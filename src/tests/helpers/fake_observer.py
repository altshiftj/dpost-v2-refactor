from unittest.mock import MagicMock

class FakeObserver:
    def __init__(self):
        self.schedule = MagicMock()
        self.start = MagicMock()
        self.stop = MagicMock()
        self.join = MagicMock()
        self.handler = None

    # Optional: keep tracking the handler if needed
    def schedule_with_handler(self, handler, path, recursive):
        self.handler = handler
        self.schedule(handler, path, recursive)
