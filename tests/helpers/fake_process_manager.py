class FakeFileProcessManager:
    def __init__(self, ui, sync_manager, session_manager, file_processor=None):
        self.processed = []
        self.records_synced = False

    def process_item(self, path):
        self.processed.append(path)

    def sync_records_to_database(self):
        self.records_synced = True