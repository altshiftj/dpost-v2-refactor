"""
id_generator.py

This module defines the IdGenerator class, responsible for creating and parsing unique
identifiers (`short_id,` `long_id,` and `file_id`) for records based on provided metadata. It ensures
consistent ID formats for easy tracking, storage, and retrieval of records within the
application.
"""

import datetime
from dataclasses import dataclass

from src.app.logger import setup_logger
from src.records.local_record import RecordInfo
from src.config.settings import DEVICE_ID, ID_SEP

logger = setup_logger(__name__)


class IdGenerator:
    """
    The IdGenerator class is responsible for constructing and parsing unique identifiers
    for records. It generates both concise (`short_id`) and detailed (`long_id`) identifiers
    based on record metadata provided through a RecordInfo object.

    Key Responsibilities:
        - Constructing `short_id` using institute, user ID, and sample ID.
        - Constructing `long_id` with comprehensive metadata including device ID, date,
          record count, and data type.
        - Parsing `long_id` back into a RecordInfo object for easy reconstruction.
        - Generating new RecordInfo objects based on a base name and data type.
        - Generating unique file IDs for associated files.
    """
    
    def __init__(self):
        """
        Initializes the IdGenerator with a specific device identifier.

        :param device_id: The device identifier, e.g., from src.config.settings.DEVICE_ID
        """
        self.device_id = DEVICE_ID

    def construct_short_id(self, id_info: RecordInfo) -> str:
        """
        Constructs a short identifier (`short_id`) using the RecordInfo object's institute,
        user ID, and sample ID. This identifier is used to store and retrieve records in the
        daily record log.

        Format:
            {institute}-{user_id}-{sample_id}

        Example:
            "IPAT-MuS-Sample_A"

        :param id_info: A RecordInfo object containing metadata for the record.
        :return: A string representing the short_id.
        """
        short_id = f"{id_info.institute}{ID_SEP}{id_info.user_id}{ID_SEP}{id_info.sample_id}"
        short_id = short_id.lower()
        logger.debug(f"Constructed short_id: {short_id} from RecordInfo: {id_info}")
        return short_id
    
    def construct_long_id(self, id_info: RecordInfo) -> str:
        """
        Constructs a long identifier (`long_id`) using comprehensive metadata from the
        RecordInfo object. This identifier includes device ID, date, daily record count,
        data type, institute, and user ID, making it suitable for detailed tracking and
        database storage without incorporating the user defined sample_id which 
        can contain unsafe characters.

        Format:
            {device_id}-{date}-rec_{daily_record_count:03}-{data_type}-{institute}-{user_id}

        Example:
            "dev_01-20240101-rec_001-img-ipat-mus"

        :param id_info: A RecordInfo object containing metadata for the record.
        :return: A string representing the long_id.
        """
        long_id = (
            f"{id_info.device_id}{ID_SEP}"
            f"{id_info.date}{ID_SEP}"
            f"rec_{id_info.daily_record_count:03}{ID_SEP}"
            f"{id_info.data_type}{ID_SEP}"
            f"{id_info.institute}{ID_SEP}"
            f"{id_info.user_id}"
        )
        long_id = long_id.lower()
        logger.debug(f"Constructed long_id: {long_id} from RecordInfo: {id_info}")
        return long_id
 
    def generate_new_record_info(
        self, 
        filename_prefix: str, 
        data_type: str, 
        record_count: int
    ) -> RecordInfo:
        """
        Generates a new RecordInfo object based on the provided base name, data type,
        and current record count. This method parses the base name to extract the 
        institute, user ID, and sample ID, and combines it with the device ID and 
        current date to create a comprehensive RecordInfo object.

        The filename_prefix is expected to follow the format:
            {institute}-{user_ID}-{sample_ID}

        Example:
            "IPAT-MuS-Sample_A"

        :param filename_prefix: A string containing the base name in the format 
                          "{institute}-{user_ID}-{sample_ID}".
        :param data_type: The type of data the record contains (e.g., 'IMG', 'ELID').
        :param record_count: The current count of records for the day, used to increment.
        :return: A RecordInfo object populated with the new record's metadata.
        :raises ValueError: If the filename_prefix does not follow the expected format.
        """
        try:
            institute, user_ID = filename_prefix.split(ID_SEP)[:2]
            sample_ID = ID_SEP.join(filename_prefix.split(ID_SEP)[2:])
        except ValueError:
            logger.error(f"Base name '{filename_prefix}' is not in the expected format 'Institute-UserID-Sample_ID'.")
            raise ValueError(f"Base name '{filename_prefix}' is not in the expected format 'Institute-UserID-Sample_ID'.")

        current_date = datetime.datetime.now().strftime('%Y%m%d')
        
        record_info = RecordInfo(
            device_id=self.device_id,
            date=current_date,
            daily_record_count=record_count + 1,
            data_type=data_type,
            institute=institute,
            user_id=user_ID,
            sample_id=sample_ID
        )
        logger.debug(f"Generated new RecordInfo: {record_info}")
        return record_info
    
    def generate_file_id(self, filename_prefix: str) -> str:
        """
        Generates a unique file identifier (`file_id`) based on the provided filename prefix.
        The file_id includes the device name, institute, user ID, sample ID, and the
        current date, ensuring uniqueness and traceability.

        Format:
            {device_name}-{institute}-{userID}-{sample_ID}-{YYYYMMDD}

        Example:
            "DEV-IPAT-MuS-Sample_A-20240101"-
        :param base_name: A string containing the base name in the format 
                          "{institute}-{user_ID}-{sample_ID}".
        :return: A string representing the unique file_id.
        :raises ValueError: If the base_name does not follow the expected format.
        """
        try:
            institute, user_ID = filename_prefix.split(ID_SEP)[:2] #TODO: Make a utility function to split the filename
            sample_ID = ID_SEP.join(filename_prefix.split(ID_SEP)[2:])
            sample_ID.replace(' ', '_')
        except ValueError:
            logger.error(f"Base name '{filename_prefix}' is not in the expected format 'Institute-UserID-Sample_ID'.")
            raise ValueError(f"Base name '{filename_prefix}' is not in the expected format 'Institute-UserID-Sample_ID'.")

        device_type = self.device_id.split('_')[0]
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        
        file_id = f"{device_type}{ID_SEP}{institute.upper()}{ID_SEP}{user_ID.upper()}{ID_SEP}{sample_ID}{ID_SEP}{current_date}"
        logger.debug(f"Generated file_id: {file_id} from base_name: {filename_prefix}")
        return file_id
