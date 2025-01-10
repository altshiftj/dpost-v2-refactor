"""
This module defines the FileEventHandler class, which extends watchdog's 
FileSystemEventHandler to handle file and directory creation events. 
It incorporates a debounce mechanism to ensure that files or directories 
are fully written before they are added to a processing queue. This helps 
prevent issues related to partially written files being processed prematurely.
"""

import os
import logging
from watchdog.events import FileSystemEventHandler
from threading import Timer
from queue import Queue

from src.config.settings import DEBOUNCE_TIME

# Initialize the logger for this module
logger = logging.getLogger(__name__)

class FileEventHandler(FileSystemEventHandler):
    """
    Custom event handler that processes newly created paths (files or directories)
    with a debounce mechanism to ensure they are fully written before processing.
    """
    
    def __init__(self, event_queue: Queue):
        super().__init__()
        self.event_queue = event_queue               # Queue to hold paths ready for processing
        self.debounce_time = DEBOUNCE_TIME           # Time in seconds to wait before processing
        self.timers = {}                             # Dictionary to map paths to their debounce timers
    
    def on_created(self, event):
        """
        Called when a file or directory is created. Starts or resets a debounce timer.
        
        :param event: The event object containing information about the creation.
        """
        logger.info(f"Path created: {event.src_path}")
        self._start_debounce(event.src_path)
    
    def _start_debounce(self, path: str):
        """
        Starts or resets a debounce timer for the given path.
        
        :param path: The file or directory path that was created.
        """
        if path in self.timers:
            self.timers[path].cancel()  # Cancel the existing timer
            logger.debug(f"Resetting debounce timer for: {path}")
    
        # Create a new timer that will call _add_item_to_queue after debounce_time
        timer = Timer(self.debounce_time, self._add_item_to_queue, args=[path])
        self.timers[path] = timer
        timer.start()
        logger.debug(f"Started debounce timer for: {path}")
    
    def _add_item_to_queue(self, path: str):
        """
        Called when the debounce timer expires. Checks if the path still exists and 
        adds it to the processing queue if valid.
        
        :param path: The file or directory path to add to the queue.
        """
        if os.path.exists(path):
            logger.info(f"Path ready for processing: {path}")
            self.event_queue.put(path)
        else:
            logger.warning(f"Path no longer exists: {path}")
        
        # Remove the timer from the dictionary as it's no longer needed
        del self.timers[path]

