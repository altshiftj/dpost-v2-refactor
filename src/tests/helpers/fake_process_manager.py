class FakeFileProcessManager:
    def __init__(self, ui, sync_manager, session_manager, file_processor):
        self.processed = []
        self.logs_synced = False
        self.records_synced = False

    def process_item(self, path):
        self.processed.append(path)

    def sync_logs_to_database(self):
        self.logs_synced = True

    def sync_records_to_database(self):
        self.records_synced = True