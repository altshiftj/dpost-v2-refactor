class FakeFileProcessManager:
    def __init__(self, ui, sync_manager, session_manager, settings_manager=None, file_processor=None, **kwargs):
        self.processed = []
        self.records_synced = False
        self._rejected = []

    def process_item(self, path):
        self.processed.append(path)

    def get_and_clear_rejected(self):
        rejected, self._rejected = self._rejected, []
        return rejected

    def shutdown(self):
        # No-op for fake
        pass

    def sync_records_to_database(self):
        self.records_synced = True