import re
import datetime

from typing import Tuple
from src.records.local_record import RecordInfo

class IdGenerator:
    def __init__(self, device_id: str):
        """
        :param device_id: The device identifier, e.g., from src.config.settings.DEVICE_ID
        """
        self.device_id = device_id

    def construct_short_id(self, id_info: RecordInfo) -> str:
        """
        Construct the short_id using a RecordInfo object.
        Format: {institute}_{user_id}_{sample_id}
        """
        return f"{id_info.institute}_{id_info.user_id}_{id_info.sample_id}"
    
    def construct_long_id(self, id_info: RecordInfo) -> str:
        """
        Construct the long_id with all fields we expect to parse later.
        Format:
            {device_id}-{date}-REC_{daily_record_count:03}-{data_type}-{institute}-{user_id}
        """
        return (
            f"{id_info.device_id}-"
            f"{id_info.date}-"
            f"REC_{id_info.daily_record_count:03}-"
            f"{id_info.data_type}-"
            f"{id_info.institute}-"
            f"{id_info.user_id}"
        )

    def parse_long_id(self, long_id: str) -> RecordInfo:
        """
        Parse a long_id string back into a RecordInfo object.
        
        Expected format:
            {device_id}-{date}-REC_{daily_record_count}-{data_type}-{institute}-{user_id}

        Example:
            DEV_01-20240101-REC_001-IMG-INST-USR
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
            raise ValueError(f"Invalid long_id format: {long_id}")

        return RecordInfo(
            device_id=match.group('device_id'),
            date=match.group('date'),
            daily_record_count=int(match.group('daily_record_count')),
            data_type=match.group('data_type'),
            institute=match.group('institute'),
            user_id=match.group('user_id'),
            # This field is not in the long_id, so we set it blank or handle accordingly
            sample_id=""
        )
    
    def generate_new_record_info(
        self, 
        base_name: str, 
        data_type: str, 
        record_count: int
    ) -> RecordInfo:
        """
        Given a 'base_name' of the format '{institute}_{user_ID}_{sample_ID}',
        create the next RecordInfo object with the daily record count incremented.
        """
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        institute, user_ID, sample_ID = base_name.split('_')

        return RecordInfo(
            device_id           =self.device_id,
            date                =current_date,
            daily_record_count  =record_count + 1,
            data_type           =data_type,
            institute           =institute,
            user_id             =user_ID,
            sample_id           =sample_ID
        )

    def generate_file_id(self, base_name: str) -> str:
        """
        Generate a short file ID that includes the device name, institute, user ID, sample ID, 
        and current date, e.g.: 
            {device_name}_{institute}_{user_ID}_{sample_ID}_{YYYYMMDD}
        """
        device_name = self.device_id.split('_')[0]
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        institute, user_ID, sample_ID = base_name.split('_')

        return f"{device_name}_{institute}_{user_ID}_{sample_ID}_{current_date}"
