"""
file_event_handler.py

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
    Custom event handler that processes newly created files and directories.
    
    Features:
        - Debounce mechanism to wait for a specified time after a file/directory
          creation event before processing, ensuring the item is fully written.
        - Differentiates between files and directories to handle each appropriately.
        - Maintains timers for each path to manage debounce delays and prevent
          premature processing.
    """
    
    def __init__(self, event_queue: Queue):
        """
        Initializes the FileEventHandler.
        
        :param event_queue: A Queue object where paths of fully written files 
                            and directories will be placed for further processing.
        """
        super().__init__()
        self.event_queue = event_queue                # Queue to hold paths ready for processing
        self.debounce_time = DEBOUNCE_TIME           # Time in seconds to wait before processing
        self.timers = {}                             # Dictionary to map paths to their debounce timers
    
    def on_created(self, event):
        """
        Called when a file or directory is created.
        
        Determines whether the created item is a file or directory and starts 
        or resets a debounce timer accordingly.
        
        :param event: The event object containing information about the creation.
        """
        if event.is_directory:
            logger.info(f"Directory created: {event.src_path}")
            self._start_debounce(event.src_path, is_directory=True)
        else:
            logger.info(f"File created: {event.src_path}")
            self._start_debounce(event.src_path, is_directory=False)
    
    def _start_debounce(self, path: str, is_directory: bool):
        """
        Starts or resets a debounce timer for the given path.
        
        If a timer for the path already exists, it is canceled and restarted. This 
        ensures that only after the debounce_time has passed without new events 
        for the same path will the path be considered ready for processing.
        
        :param path: The file or directory path that was created.
        :param is_directory: Boolean indicating whether the path is a directory.
        """
        if path in self.timers:
            self.timers[path].cancel()  # Cancel the existing timer
            logger.debug(f"Resetting debounce timer for: {path}")
    
        # Create a new timer that will call _add_item_to_queue after debounce_time
        timer = Timer(self.debounce_time, self._add_item_to_queue, args=[path, is_directory])
        self.timers[path] = timer
        timer.start()
        logger.debug(f"Started debounce timer for: {path}")
    
    def _add_item_to_queue(self, path: str, is_directory: bool):
        """
        Called when the debounce timer expires. Checks if the path still exists and 
        adds it to the processing queue if valid.
        
        :param path: The file or directory path to add to the queue.
        :param is_directory: Boolean indicating whether the path is a directory.
        """
        if os.path.exists(path):
            item_type = 'Directory' if is_directory else 'File'
            logger.info(f"{item_type} ready for processing: {path}")
            self.event_queue.put((path, is_directory))
        else:
            item_type = 'Directory' if is_directory else 'File'
            logger.warning(f"{item_type} no longer exists: {path}")
        
        # Remove the timer from the dictionary as it's no longer needed
        del self.timers[path]
