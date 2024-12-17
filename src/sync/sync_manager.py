import os

from src.records.local_record import LocalRecord
from src.app.logger import setup_logger

from kadi_apy import KadiManager


logger = setup_logger(__name__)

class SyncManager:
    def __init__(self, db_manager):
        # db_manager_factory could be something like KadiManager or a callable that returns a DB manager instance.
        self.db_manager_factory = db_manager

    def sync_record_to_database(self, local_record: LocalRecord):
        try:
            with self.db_manager_factory as db_manager:
                db_manager: KadiManager
                db_record = db_manager.record(create=True, identifier=local_record.long_id)
                
                if not local_record.is_in_db:
                    db_record.set_attribute('title', local_record.name)

                for file_path, uploaded in local_record.file_uploaded.items():
                    if not uploaded:
                        db_record.upload_file(file_path)
                        local_record.file_uploaded[file_path] = True
                        logger.info(f"Uploaded file: {os.path.basename(file_path)}")
                local_record.is_in_db = True
                logger.info("Files have been synced to the database.")
        except Exception as e:
            logger.exception(f"Failed to upload files to the database: {e}")
