import os

from src.config.settings import DEVICE_ID

from src.records.local_record import LocalRecord, RecordInfo
from src.records.record_persistence import RecordPersistence
from src.storage.path_manager import PathManager


class RecordManager:
    def __init__(self):
        self.persistence = RecordPersistence()
        self.paths = PathManager()
        self.daily_records_dict = self.persistence.load_daily_records()

    def get_or_create_record(self, record_info: RecordInfo) -> LocalRecord:
        daily_record_key = self.paths.construct_short_id(record_info)
        if daily_record_key not in self.daily_records_dict:
            self.daily_records_dict[daily_record_key] = LocalRecord(
                long_id=self.paths.construct_long_id(record_info),
                short_id=self.paths.construct_short_id(record_info),
                name=record_info.sample_id
            )
        
        return self.daily_records_dict[daily_record_key]

    def add_item_to_record(self, path: str, record_info: RecordInfo, in_db: bool=False):
        record = self.get_or_create_record(record_info)
        record.add_item(path)
        self.save_records()

    def save_records(self):
        self.persistence.save_daily_records(self.daily_records_dict)

    def get_all_records(self) -> dict:
        return self.daily_records_dict

    def get_num_records(self) -> int:
        return len(self.daily_records_dict.keys())

    def clear_all_records(self):
        self.daily_records_dict.clear()
        self.save_records()

    def get_record_by_short_id(self, short_id: str) -> LocalRecord:
        return self.daily_records_dict.get(short_id)
    
    def get_record_by_long_id(self, long_id: str) -> LocalRecord:
        for record in self.daily_records_dict.values():
            record: LocalRecord
            if record.long_id == long_id:
                return record
        return None
    
    def get_record_filepaths(self, record: LocalRecord) -> list[str]:
        return list(record.file_uploaded.items())
    
    def get_record_filepath_basenames(self, record: LocalRecord) -> list[str]:
        if not record:
            return []
        return [os.path.basename(fp) for fp in record.file_uploaded.keys()]
    

