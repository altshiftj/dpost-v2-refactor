from src.app.logger import setup_logger

from watchdog.events import FileSystemEventHandler

logger = setup_logger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Event handler that processes new files.
    """
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        self.event_queue.put(event.src_path)
        logger.info(f"New file detected: {event.src_path}")
