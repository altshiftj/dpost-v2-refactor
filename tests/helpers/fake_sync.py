from ipat_watchdog.sync.sync_abstract import ISyncManager

class DummySyncManager(ISyncManager):
    def __init__(self, ui=None):
        self.synced_records = []
        self.ui = ui

    def sync_record_to_database(self, local_record):
        self.synced_records.append(local_record)
        return False  # Simulate all files uploaded
