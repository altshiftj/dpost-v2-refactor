import os
import re
import sys
import json
import logging
import queue
import time
import datetime
import hashlib
import tifffile
import xmltodict
import shutil
from watchdog.observers import Observer

from kadi_apy import KadiManager
from FileProcessor import FileProcessor
from event_gui_session import FileEventHandler, GUIManager, SessionManager

DEVICE_NAME = "REM_01"

WATCH_DIR = r"monitored_folder"
RENAME_DIR = os.path.join(WATCH_DIR, 'To_Rename')
STAGING_DIR = os.path.join(WATCH_DIR, 'Staging')
ARCHIVE_DIR = os.path.join(WATCH_DIR, 'Archive')
EXCEPTIONS_DIR = os.path.join(WATCH_DIR, 'Exceptions')
ARCHIVED_FILES_JSON = os.path.join(ARCHIVE_DIR, 'processed_files.json')

FILENAME_PATTERN = re.compile(r'^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9-]+$')

logging.basicConfig(filename='watchdog.log', level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class DeviceWatchdogApp:
    """
    Main application class
    """
    def __init__(
        self,
        watch_dir,
        device_name,
        rename_folder,
        staging_dir,
        archive_dir,
        exceptions_dir,
        test_path,
        session_timeout=60,
        testing=False,
    ):
        self.testing = testing
        self.test_path = test_path
        self.watch_dir = watch_dir
        self.archive_dir = archive_dir
        self.session_timeout = session_timeout

        if testing:
            for root, dirs, files in os.walk(watch_dir):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    shutil.rmtree(os.path.join(root, dir))

        self.ui = GUIManager()
        self.session_manager = SessionManager(session_timeout, self.end_session, self.ui.root)

        os.makedirs(rename_folder, exist_ok=True)
        os.makedirs(staging_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(exceptions_dir, exist_ok=True)

        self.file_processor: FileProcessor = FileProcessor(
            device_id=device_name,
            rename_folder=rename_folder,
            staging_dir=staging_dir,
            archive_dir=archive_dir,
            exceptions_dir=exceptions_dir,
            ui=self.ui,
            session_manager=self.session_manager
        )

        self.event_queue = queue.Queue()
        self.session_timer = None

        self.event_handler = FileEventHandler(self.event_queue)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, path=self.watch_dir, recursive=False)
        self.observer.start()
        logger.info(f"Monitoring directory: {self.watch_dir}")

        self.ui.root.after(100, self.process_events)
        self.ui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.ui.root.report_callback_exception = self.handle_exception

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        logger.error("An unexpected error occurred", exc_info=(exc_type, exc_value, exc_traceback))
        self.ui.show_error("Application Error", "An unexpected error occurred. Please contact the administrator.")
        self.on_closing()

    def end_session(self):
        logger.info("DeviceWatchdogApp.end_session called.")
        try:
            self.sync_records_to_database()
        except Exception as e:
            logger.exception(f"An error occurred during session end: {e}")
            self.ui.show_error("Session End Error", f"An error occurred during session end: {e}")
        finally:
            if hasattr(self.ui, 'done_dialog') and self.ui.done_dialog.winfo_exists():
                self.ui.done_dialog.destroy()
            logger.info("End session logic completed.")

    def sync_records_to_database(self):
        logger.info("Syncing files to the database...")
        self.file_processor.sync_records_to_database()

    def process_events(self):
        while not self.event_queue.empty():

            # wait for file/folder to be fully written
            # May need to be more dynamic in the future
            time.sleep(0.5)

            data_path = self.event_queue.get()
            self.file_processor.process_incoming_path(data_path)
        self.ui.root.after(100, self.process_events)

        if self.testing:
            if os.path.isfile(self.test_path):
                shutil.copy(self.test_path, self.watch_dir)
            elif os.path.isdir(self.test_path):
                shutil.copytree(self.test_path, os.path.join(self.watch_dir, os.path.basename(self.test_path)))
            self.testing = False

        if datetime.datetime.now().hour == 0:
            self.file_processor.clear_daily_records_dict()

    def on_closing(self):
        if self.session_timer:
            self.session_timer.cancel()
        self.observer.stop()
        self.observer.join()
        self.ui.destroy()
        logger.info("Monitoring stopped.")

    def run(self):
        try:
            self.ui.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()
        except Exception:
            self.handle_exception(*sys.exc_info())


if __name__ == "__main__":
    testing = True
    test_path = r""

    logger.info("Starting Device Watchdog application...")
    app = DeviceWatchdogApp(
        watch_dir=WATCH_DIR,
        device_name=DEVICE_NAME,
        rename_folder=RENAME_DIR,
        staging_dir=STAGING_DIR,
        archive_dir=ARCHIVE_DIR,
        exceptions_dir=EXCEPTIONS_DIR,
        test_path=test_path,
        session_timeout=300,
        testing=testing,
    )
    try:
        app.run()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        logger.info("Application closed.")


class MetadataExtractor:
    @staticmethod
    def hash_file(file_path, chunk_size=65536):
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as file:
                while True:
                    data = file.read(chunk_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()
        except Exception as e:
            logger.exception(f"Failed to hash file {file_path}: {e}")
            return None

    @staticmethod
    def flatten_xml_dict(d, parent_key='', sep='_'):
        items = {}
        if parent_key.startswith('FeiImage'):
            parent_key = parent_key.replace('FeiImage', '')

        for k, v in d.items():
            if k.startswith('@'):
                attr_name = k[1:]
                new_key = f"{parent_key}{sep}{attr_name}" if parent_key else attr_name
                items[new_key] = v
            elif k == '#text':
                if v.strip():
                    new_key = parent_key if parent_key else 'text'
                    items[new_key] = v.strip()
            else:
                new_parent_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.update(MetadataExtractor.flatten_xml_dict(v, new_parent_key, sep=sep))
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        items.update(MetadataExtractor.flatten_xml_dict(item, f"{new_parent_key}{sep}{i}", sep=sep))
                elif isinstance(v, tuple):
                    for i, item in enumerate(v):
                        items.update(MetadataExtractor.flatten_xml_dict(item, f"{new_parent_key}{sep}{i}", sep=sep))
                else:
                    new_key = new_parent_key
                    items[new_key] = v
        return items
    
    @staticmethod
    def parse_xml_metadata(xml_string):
        try:
            xml_dict = xmltodict.parse(xml_string)
            flat_dict = MetadataExtractor.flatten_xml_dict(xml_dict)
            return flat_dict
        except Exception as e:
            logger.exception(f"Failed to parse XML metadata: {e}")
            return {}

    @staticmethod
    def extract_tiff_metadata(file_path):
        base_name = os.path.basename(file_path)
        file_name, ext = os.path.splitext(base_name)
        file_hash = MetadataExtractor.hash_file(file_path)

        metadata = {}
        flattened_data = {}
        try:
            with tifffile.TiffFile(file_path) as tif:
                page = tif.pages[0]
                tags = page.tags

                for tag in tags.values():
                    tag_name = tag.name
                    tag_value = tag.value

                    if isinstance(tag_value, tuple):
                        flattened_data = {f"{tag_name}_{i}": value for i, value in enumerate(tag_value)}

                    if isinstance(tag_value, bytes):
                        try:
                            tag_value = tag_value.decode('utf-8')
                        except UnicodeDecodeError:
                            tag_value = tag_value.decode('latin-1')

                    if flattened_data:
                        metadata.update(flattened_data)
                        flattened_data = {}
                    else:
                        metadata[tag_name] = tag_value

                    if tag_name == "FEI_TITAN":
                        xml_metadata = MetadataExtractor.parse_xml_metadata(tag_value)
                        for k, v in xml_metadata.items():
                            if v is None:
                                xml_metadata[k] = 'null'
                            elif re.match(r'^-?\d+$', v):
                                xml_metadata[k] = int(v)
                            elif re.match(r'^-?\d+(\.\d+)?$', v):
                                xml_metadata[k] = float(v)
                            elif re.match(r'^-?\d+(\.\d+)?[eE][-+]?\d+$', v):
                                xml_metadata[k] = float(v)
                        metadata.update(xml_metadata)

            metadata.pop('FEI_TITAN', None)
            metadata.pop('xmlns:xsi', None)
            metadata.pop('xsi:noNamespaceSchemaLocation', None)

            metadata[f"filehash"] = file_hash
            metadata = {f"{file_name}|{k}": v for k, v in metadata.items()}

        except Exception as e:
            logger.exception(f"Failed to extract metadata from {file_path}: {e}")
            return None
        return metadata
