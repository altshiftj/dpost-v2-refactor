import os
import json
import queue
import logging
import threading
import time
import tifffile
import hashlib
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

def hash_file(file_path):
    """
    Generates a hash for the file at the specified path.
    """
    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as file:
            while True:
                data = file.read(65536)  # 64 KB chunks
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()
    except Exception as e:
        logging.error(f"Failed to hash file {file_path}: {e}")
        return None

def extract_metadata(file_path):
    """
    Extracts metadata from an SEM TIFF file and returns it as a dictionary organized into categories.
    """
    base_name = os.path.basename(file_path)
    file_hash = hash_file(file_path)

    metadata = {
        "File Name": base_name,
        "Image Metadata": {},
        "Instrument Metadata": {},
        "Advanced Metadata": {},
        "File Hash": file_hash
    }
    try:
        with tifffile.TiffFile(file_path) as tif:
            # Extract tags from the first page
            page = tif.pages[0]
            tags = page.tags

            # Process TIFF tags
            for tag in tags.values():
                tag_name = tag.name
                tag_value = tag.value
                # Convert bytes to string if necessary
                if isinstance(tag_value, bytes):
                    try:
                        tag_value = tag_value.decode('utf-8')
                    except UnicodeDecodeError:
                        tag_value = tag_value.decode('latin-1')

                # Organize tags into categories
                if tag_name in ["ImageWidth", "ImageLength"]:
                    metadata["Image Metadata"][tag_name] = tag_value
                elif tag_name == "DateTime":
                    metadata["Image Metadata"]["Time"] = tag_value
                elif tag_name == "FEI_TITAN":
                    # Parse embedded XML
                    xml_metadata = parse_xml_metadata(tag_value)
                    organize_xml_metadata(xml_metadata, metadata)
                else:
                    # Store other TIFF tags in Advanced Metadata
                    metadata["Advanced Metadata"][tag_name] = tag_value

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

def etree_to_dict(element):
    """
    Converts an ElementTree element into a nested dictionary, capturing units where applicable.
    """
    d = {element.tag: {} if element.attrib else None}

    # If the element has attributes, add them to the dictionary with `@` prefix
    if element.attrib:
        for k, v in element.attrib.items():
            # Check if there's a 'unit' attribute and treat it as such
            if k == "unit":
                d[element.tag] = {"value": element.text.strip() if element.text else None, "unit": v}
            else:
                d[element.tag]['@' + k] = v

    # If the element has child elements, recurse and add them as nested dictionaries
    children = list(element)
    if children:
        child_dict = {}
        for child in children:
            child_dict.update(etree_to_dict(child))
        d[element.tag] = child_dict
    else:
        # If no children and no specific unit handling above, add the element text
        if "unit" not in element.attrib:
            d[element.tag] = element.text.strip() if element.text else None

    return d

def organize_xml_metadata(xml_dict, metadata):
    """
    Organizes XML metadata into Image Metadata and Instrument Metadata categories.
    """
    # Extract Image Metadata
    image_meta_keys = [
        'databarHeight', 'databarFields', 'databarLabel', 'displayWidth',
        'pixelWidth', 'pixelHeight', 'time', 'integrations', 'cropHint',
        'appliedContrast', 'appliedBrightness', 'appliedGamma', 'displayBlackLevel',
        'displayWhiteLevel', 'samplePosition', 'samplePressureEstimate',
        'workingDistance'
    ]

    fei_image = xml_dict.get('FeiImage', {})

    for key in image_meta_keys:
        if key in fei_image:
            metadata["Image Metadata"][key] = fei_image[key]

    # Extract Instrument Metadata
    instrument_meta_keys = [
        'instrument', 'applicationID', 'PPI', 'acquisition', 'multiStage'
    ]

    for key in instrument_meta_keys:
        if key in fei_image:
            metadata["Instrument Metadata"][key] = fei_image[key]

    # if there are any other keys in the XML, add them to Advanced Metadata
    # and log them for further investigation
    for key, value in fei_image.items():
        if key not in image_meta_keys and key not in instrument_meta_keys:
            metadata["Advanced Metadata"][key] = value
            logging.warning(f"Unknown key in XML metadata: {key}")

    # Handle units and attributes in tags
    metadata["Image Metadata"] = handle_units_and_attributes(metadata["Image Metadata"])
    metadata["Instrument Metadata"] = handle_units_and_attributes(metadata["Instrument Metadata"])

def handle_units_and_attributes(data):
    """
    Processes units and attributes in the metadata.
    """
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Handle units in attributes
                unit = value.get('unit')
                if unit:
                    new_key = f"{key} (unit=\"{unit}\")"
                    new_value = value.get('value', '')
                    new_data[new_key] = handle_units_and_attributes(new_value)
                elif '@id' in value:
                    # Handle id in attributes
                    id_value = value['@id']
                    new_key = f"{key} (id=\"{id_value}\")"
                    value.pop('@id')
                    new_data[new_key] = handle_units_and_attributes(value)
                else:
                    new_data[key] = handle_units_and_attributes(value)
            else:
                new_data[key] = value
        return new_data
    elif isinstance(data, list):
        return [handle_units_and_attributes(item) for item in data]
    else:
        return data

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
        json_file_name = f"{name}.json"
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

    # Retry a few times to ensure stability
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
        Moves or deletes the processed file, appending a counter if a file with the same name exists.
        """
        try:
            # Example: Move the processed file to an archive directory
            archive_dir = self.output_dir
            os.makedirs(archive_dir, exist_ok=True)
            base_name = os.path.basename(file_path)
            destination = os.path.join(archive_dir, base_name)

            # Check if the file already exists and append a counter if necessary
            counter = 1
            while os.path.exists(destination):
                name, ext = os.path.splitext(base_name)
                new_name = f"{name}_{counter}{ext}"
                destination = os.path.join(archive_dir, new_name)
                counter += 1

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
    input_dir = r"test_monitor\Validated"
    output_dir = r"test_monitor\Processed"

    app = MetadataExtractorApp(input_dir, output_dir)
    app.run()
