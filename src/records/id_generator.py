"""
id_generator.py

This module defines the IdGenerator class, responsible for creating and parsing unique
identifiers (`short_id` and `long_id`) for records based on provided metadata. It ensures
consistent ID formats for easy tracking, storage, and retrieval of records within the
application.
"""

import re
import datetime
from typing import Tuple

from src.app.logger import setup_logger
from src.records.local_record import RecordInfo

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
    
    def __init__(self, device_id: str):
        """
        Initializes the IdGenerator with a specific device identifier.

        :param device_id: The device identifier, e.g., from src.config.settings.DEVICE_ID
        """
        self.device_id = device_id
        logger = None  # Assuming logger is set up elsewhere if needed

    def construct_short_id(self, id_info: RecordInfo) -> str:
        """
        Constructs a short identifier (`short_id`) using the RecordInfo object's institute,
        user ID, and sample ID. This identifier is concise and typically used for quick
        references.

        Format:
            {institute}_{user_id}_{sample_id}

        Example:
            "IPAT_MuS_SampleA"

        :param id_info: A RecordInfo object containing metadata for the record.
        :return: A string representing the short_id.
        """
        short_id = f"{id_info.institute}_{id_info.user_id}_{id_info.sample_id}"
        logger.debug(f"Constructed short_id: {short_id} from RecordInfo: {id_info}")
        return short_id
    
    def construct_long_id(self, id_info: RecordInfo) -> str:
        """
        Constructs a long identifier (`long_id`) using comprehensive metadata from the
        RecordInfo object. This identifier includes device ID, date, daily record count,
        data type, institute, and user ID, making it suitable for detailed tracking and
        database storage.

        Format:
            {device_id}-{date}-REC_{daily_record_count:03}-{data_type}-{institute}-{user_id}

        Example:
            "DEV_01-20240101-REC_001-IMG-IPAT-MuS"

        :param id_info: A RecordInfo object containing metadata for the record.
        :return: A string representing the long_id.
        """
        long_id = (
            f"{id_info.device_id}-"
            f"{id_info.date}-"
            f"REC_{id_info.daily_record_count:03}-"
            f"{id_info.data_type}-"
            f"{id_info.institute}-"
            f"{id_info.user_id}"
        )
        logger.debug(f"Constructed long_id: {long_id} from RecordInfo: {id_info}")
        return long_id

    def parse_long_id(self, long_id: str) -> RecordInfo:
        """
        Parses a `long_id` string back into a RecordInfo object. This method validates
        the format of the long_id and extracts the relevant components to reconstruct
        the original RecordInfo.

        Expected Format:
            {device_id}-{date}-REC_{daily_record_count}-{data_type}-{institute}-{user_id}

        Example:
            "DEV_01-20240101-REC_001-IMG-IPAT-MuS"

        :param long_id: The long_id string to parse.
        :return: A RecordInfo object populated with the extracted data.
        :raises ValueError: If the long_id does not match the expected format.
        """
        pattern = (
            r'^(?P<device_id>[A-Za-z0-9_-]+)-'
            r'(?P<date>\d{8})-'
            r'REC_(?P<daily_record_count>\d{3})-'
            r'(?P<data_type>[A-Za-z0-9_-]+)-'
            r'(?P<institute>[A-Za-z0-9_-]+)-'
            r'(?P<user_id>[A-Za-z0-9_-]+)$'
        )
        match = re.match(pattern, long_id)
        if not match:
            logger.error(f"Invalid long_id format: {long_id}")
            raise ValueError(f"Invalid long_id format: {long_id}")

        record_info = RecordInfo(
            device_id=match.group('device_id'),
            date=match.group('date'),
            daily_record_count=int(match.group('daily_record_count')),
            data_type=match.group('data_type'),
            institute=match.group('institute'),
            user_id=match.group('user_id'),
            sample_id=""  # Sample ID is not included in long_id; handled separately
        )
        logger.debug(f"Parsed RecordInfo from long_id '{long_id}': {record_info}")
        return record_info
    
    def generate_new_record_info(
        self, 
        base_name: str, 
        data_type: str, 
        record_count: int
    ) -> RecordInfo:
        """
        Generates a new RecordInfo object based on the provided base name, data type,
        and current record count. This method parses the base name to extract the 
        institute, user ID, and sample ID, and combines it with the device ID and 
        current date to create a comprehensive RecordInfo object.

        The base_name is expected to follow the format:
            {institute}_{user_ID}_{sample_ID}

        Example:
            "IPAT_MuS_SampleA"

        :param base_name: A string containing the base name in the format 
                          "{institute}_{user_ID}_{sample_ID}".
        :param data_type: The type of data the record contains (e.g., 'IMG', 'ELID').
        :param record_count: The current count of records for the day, used to increment.
        :return: A RecordInfo object populated with the new record's metadata.
        :raises ValueError: If the base_name does not follow the expected format.
        """
        try:
            institute, user_ID, sample_ID = base_name.split('_')
        except ValueError:
            logger.error(f"Base name '{base_name}' is not in the expected format 'Institute_UserID_SampleID'.")
            raise ValueError(f"Base name '{base_name}' is not in the expected format 'Institute_UserID_SampleID'.")

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
    
    def generate_file_id(self, base_name: str) -> str:
        """
        Generates a unique file identifier (`file_id`) based on the provided base name.
        The file_id includes the device name, institute, user ID, sample ID, and the
        current date, ensuring uniqueness and traceability.

        Format:
            {device_name}_{institute}_{user_ID}_{sample_ID}_{YYYYMMDD}

        Example:
            "DEV_IPAT_MuS_SampleA_20240101"

        :param base_name: A string containing the base name in the format 
                          "{institute}_{user_ID}_{sample_ID}".
        :return: A string representing the unique file_id.
        :raises ValueError: If the base_name does not follow the expected format.
        """
        try:
            institute, user_ID, sample_ID = base_name.split('_')
        except ValueError:
            logger.error(f"Base name '{base_name}' is not in the expected format 'Institute_UserID_SampleID'.")
            raise ValueError(f"Base name '{base_name}' is not in the expected format 'Institute_UserID_SampleID'.")

        device_name = self.device_id.split('_')[0]
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        
        file_id = f"{device_name}_{institute}_{user_ID}_{sample_ID}_{current_date}"
        logger.debug(f"Generated file_id: {file_id} from base_name: {base_name}")
        return file_id
