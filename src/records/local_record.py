import os

from dataclasses import dataclass, field
from typing import Dict

from src.app.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class RecordInfo:
    device_id: str = "null"
    date: str = "null"
    daily_record_count: int = -1
    data_type: str = "null"
    institute: str = "null"
    user_id: str = "null"
    sample_id: str = "null"
    
@dataclass
class LocalRecord:
    long_id: str = "null"
    short_id: str = "null"
    name: str = "null"
    data_type: str = "null"
    is_in_db: bool = False
    file_uploaded: Dict[str, bool] = field(default_factory=dict)

    def add_item(self, path: str):
        if os.path.isfile(path):
            self.file_uploaded[path] = False
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.file_uploaded[file_path] = False
        else:
            logger.warning(f"Path '{path}' is neither a file nor a directory.")

    def mark_uploaded(self, file_path: str):
        if file_path in self.file_uploaded:
            self.file_uploaded[file_path] = True

    def count_files(self) -> int:
        return len(self.file_uploaded)

    def all_files_uploaded(self) -> bool:
        return all(self.file_uploaded.values())

    def to_dict(self) -> dict:
        return {
            "record_id": self.long_id,
            "record_name": self.short_id,
            "in_db": self.is_in_db,
            "files_uploaded": self.file_uploaded,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "LocalRecord":
        return cls(
            record_name=data.get("record_name", ""),
            record_id=data.get("record_id", ""),
            is_in_db=data.get("in_db", False),
            file_uploaded=data.get("files_uploaded", {})
        )