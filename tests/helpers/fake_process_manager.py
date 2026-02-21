from dataclasses import dataclass
from enum import Enum, auto


class ProcessingStatus(Enum):
    PROCESSED = auto()


@dataclass(frozen=True)
class ProcessingResult:
    status: ProcessingStatus
    message: str


class FakeFileProcessManager:
    def __init__(self, interactions, sync_manager, session_manager, config_service=None, file_processor=None, **kwargs):
        self.processed = []
        self.records_synced = False
        self._rejected = []
        self.interactions = interactions
        self.config_service = config_service

    def process_item(self, path):
        self.processed.append(path)
        return ProcessingResult(ProcessingStatus.PROCESSED, "fake")

    def get_and_clear_rejected(self):
        rejected, self._rejected = self._rejected, []
        return rejected

    def should_queue_modified(self, path: str) -> bool:
        return False

    def shutdown(self):
        pass

    def sync_records_to_database(self):
        self.records_synced = True
