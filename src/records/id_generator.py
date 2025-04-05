"""
id_generator.py

This module defines the IdGenerator class, responsible for creating and parsing unique
identifiers for records and files based on provided metadata. It ensures
consistent ID formats for easy tracking, storage, and retrieval of records within the
application.
"""
from src.app.logger import setup_logger
from src.config.settings import DEVICE_TYPE, ID_SEP
from src.records.local_record import LocalRecord

logger = setup_logger(__name__)


class IdGenerator:
    """
    The IdGenerator class is responsible for constructing and parsing unique identifiers
    for records. It generates identifiers from the filename prefix provided by the user.

    Key Responsibilities:
        - Constructing record identifiers using institute, user ID, and sample ID.
        - Generating unique file IDs for associated files.
    """

    @staticmethod
    def generate_record_id(filename_prefix: str) -> str:
        """
        Constructs a record identifier using the device type and the provided filename prefix.

        Format:
            {device_type}-{user_id}-{institute}-{sample_id}

        Example:
            "rem-mus-ipat-sample_a"

        :param filename_prefix: The filename prefix to use in the identifier.
        :return: A string representing the identifier.
        """
        record_id = f"{DEVICE_TYPE}{ID_SEP}{filename_prefix}"

        # Convert to lowercase for consistency
        record_id = record_id.lower()
        logger.debug(f"Constructed record_id: {record_id}")
        return record_id
    
    @staticmethod
    def generate_file_id(filename_prefix: str) -> str:
        """
        Constructs a unique file identifier using the extracted sample_id from the provided filename prefix.

        Format:
            {device}-{sample_id}

        Example:
            "rem-sample_a.tiff"

        :param filename_prefix: The filename prefix from which we extract the sample_id.
        """
        # extract the sample_id as the last part of the filename prefix
        user_id, institute, sample_id = filename_prefix.split(ID_SEP)

        file_id = f"{DEVICE_TYPE}{ID_SEP}{sample_id}"

        return file_id