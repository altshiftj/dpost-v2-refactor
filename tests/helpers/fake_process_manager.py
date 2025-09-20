from ipat_watchdog.core.processing.models import ProcessingResult, ProcessingStatus


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

    def shutdown(self):
        pass

    def sync_records_to_database(self):
        self.records_synced = True
