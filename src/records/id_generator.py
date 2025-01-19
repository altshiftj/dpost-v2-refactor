"""
id_generator.py

This module defines the IdGenerator class, responsible for creating and parsing unique
identifiers (`short_id,` `long_id,` and `file_id`) for records based on provided metadata. It ensures
consistent ID formats for easy tracking, storage, and retrieval of records within the
application.
"""
from src.app.logger import setup_logger
from src.config.settings import DEVICE_ID, ID_SEP

logger = setup_logger(__name__)


class IdGenerator:
    """
    The IdGenerator class is responsible for constructing and parsing unique identifiers
    for records. It generates both concise (`short_id`) and detailed (`long_id`) identifiers
    based on record metadata provided through a RecordInfo object.

    Key Responsibilities:
        - Constructing record identifiers using institute, user ID, and sample ID.
        - Generating unique file IDs for associated files.
    """

    @staticmethod
    def generate_record_id(filename_prefix: str) -> str:
        """
        Constructs a record identifier using the device name and the provided filename prefix.

        Format:
            {device}-{institute}-{user_id}-{sample_id}

        Example:
            "rem-ipat-mus-sample_a"

        :param id_info: A RecordInfo object containing metadata for the record.
        :return: A string representing the identifier.
        """
        device_type = DEVICE_ID.split('_')[0]

        record_id = f"{device_type}{ID_SEP}{filename_prefix}"
        record_id = record_id.lower()
        logger.debug(f"Constructed record_id: {record_id}")
        return record_id
        
