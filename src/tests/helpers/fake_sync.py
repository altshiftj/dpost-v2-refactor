from sync.sync_abstract import ISyncManager

class DummySyncManager(ISyncManager):
    def __init__(self, ui=None):
        self.synced_records = []
        self.synced_logs = 0
        self.ui = ui

    def sync_record_to_database(self, local_record):
        self.synced_records.append(local_record)
        return False  # Simulate all files uploaded

    def sync_logs_to_database(self):
        self.synced_logs += 1
