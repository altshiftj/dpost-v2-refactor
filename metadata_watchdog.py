import os
import json
import queue
import logging
import threading
import time
import tifffile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class NewTIFFHandler(FileSystemEventHandler):
    """
    Event handler that processes new TIFF files.
    """
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.tif', '.tiff')):
            # Add the file path to the queue
            self.event_queue.put(event.src_path)
            logging.info(f"New TIFF file detected: {event.src_path}")

def extract_metadata(file_path):
    """
    Extracts metadata from a TIFF file and returns it as a dictionary.
    """
    metadata = {}
    try:
        with tifffile.TiffFile(file_path) as tif:
            # Extract tags from all pages
            for page_number, page in enumerate(tif.pages):
                tags = page.tags
                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value
                    # Convert bytes to string if necessary
                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode('utf-8')
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode('latin-1')
                    
                    metadata[f"{tag_name}"] = tag_value
                    
                    # Potentially use page number to avoid overwriting tags from different pages
                    # TODO: Verify if this is necessary
                    # metadata[f"{tag_name}_page{page_number}"] = tag_value

            # If there's embedded XML, extract and parse it
            for key in metadata.keys():
                if 'ImageDescription' in key:
                    xml_data = metadata[key]
                    xml_metadata = parse_xml_metadata(xml_data)
                    metadata.update(xml_metadata)
                    # Optionally remove the raw XML data
                    # del metadata[key]
                    break  # Assuming only one ImageDescription is needed
    except Exception as e:
        logging.error(f"Failed to extract metadata from {file_path}: {e}")
        return None
    return metadata

def parse_xml_metadata(xml_string):
    """
    Parses XML string and returns a nested dictionary.
    """
    try:
        root = ET.fromstring(xml_string)
        xml_dict = etree_to_dict(root)
        return xml_dict
    except Exception as e:
        logging.error(f"Failed to parse XML metadata: {e}")
        return {}

def etree_to_dict(t):
    """
    Converts an ElementTree object to a dictionary.
    """
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = {}
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {t.tag: dd}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text and t.text.strip():
        text = t.text.strip()
        if children or t.attrib:
            d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d

def metadata_to_json(metadata):
    """
    Converts metadata dictionary to a JSON string.
    """
    try:
        json_data = json.dumps(metadata, indent=4)
        return json_data
    except Exception as e:
        logging.error(f"Failed to convert metadata to JSON: {e}")
        return None

def save_json(json_data, original_file_path, output_dir):
    """
    Saves the JSON data to a file.
    """
    try:
        base_name = os.path.basename(original_file_path)
        name, _ = os.path.splitext(base_name)
        json_file_name = f"{name}_metadata.json"
        json_file_path = os.path.join(output_dir, json_file_name)

        with open(json_file_path, 'w') as json_file:
            json_file.write(json_data)
        logging.info(f"Metadata saved to {json_file_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON data: {e}")

def is_file_stable(file_path, check_interval=1, retries=3):
    """
    Checks if the file size remains constant over a period of time.
    """
    previous_size = -1
    for _ in range(retries):
        if not os.path.exists(file_path):
            return False
        current_size = os.path.getsize(file_path)
        if current_size == previous_size:
            return True
        previous_size = current_size
        time.sleep(check_interval)
    return False

class MetadataExtractorApp:
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.stop_event = threading.Event()

        # Ensure directories exist
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize event queue
        self.event_queue = queue.Queue()

        # Set up the observer and event handler
        self.event_handler = NewTIFFHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.input_dir, recursive=False)
        self.observer.start()
        logging.info(f"Monitoring directory: {self.input_dir}")

        # Process existing files on startup
        self.process_existing_files()

        # Start the event processing thread
        self.processing_thread = threading.Thread(target=self.process_events)
        self.processing_thread.start()

    def process_existing_files(self):
        """
        Processes existing TIFF files in the input directory.
        """
        for filename in os.listdir(self.input_dir):
            if filename.lower().endswith(('.tif', '.tiff')):
                file_path = os.path.join(self.input_dir, filename)
                self.event_queue.put(file_path)

    def process_events(self):
        """
        Processes file events from the queue.
        """
        while not self.stop_event.is_set():
            try:
                file_path = self.event_queue.get(timeout=1)
                if is_file_stable(file_path):
                    logging.info(f"Processing file: {file_path}")
                    metadata = extract_metadata(file_path)
                    if metadata:
                        json_data = metadata_to_json(metadata)
                        if json_data:
                            save_json(json_data, file_path, self.output_dir)
                            # Optionally move or delete the processed file
                            # self.move_processed_file(file_path)
                    else:
                        logging.error(f"No metadata extracted from {file_path}")
                else:
                    logging.warning(f"File {file_path} is not stable yet. Re-queueing.")
                    self.event_queue.put(file_path)
                    time.sleep(1)  # Wait before retrying
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing file: {e}")

    def move_processed_file(self, file_path):
        """
        Moves or deletes the processed file.
        """
        try:
            # Example: Move the processed file to an archive directory
            archive_dir = os.path.join(self.input_dir, 'Processed')
            os.makedirs(archive_dir, exist_ok=True)
            destination = os.path.join(archive_dir, os.path.basename(file_path))
            os.rename(file_path, destination)
            logging.info(f"Moved processed file to {destination}")
            # Or, to delete the file:
            # os.remove(file_path)
            # logging.info(f"Deleted processed file: {file_path}")
        except Exception as e:
            logging.error(f"Failed to move or delete processed file {file_path}: {e}")

    def run(self):
        """
        Keeps the application running.
        """
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received. Shutting down...")
            self.stop()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            self.stop()

    def stop(self):
        """
        Stops the observer and processing thread.
        """
        self.observer.stop()
        self.stop_event.set()
        self.observer.join()
        self.processing_thread.join()
        logging.info("Application stopped.")

if __name__ == "__main__":
    import sys

    # Replace these paths with your actual directories
    input_dir = r"D:/Monitored_Folders/SEM/Processed"
    output_dir = r"D:/Monitored_Folders/SEM/Metadata"

    # Ensure directories exist
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    app = MetadataExtractorApp(input_dir, output_dir)
    app.run()
