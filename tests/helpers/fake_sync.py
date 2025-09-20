from ipat_watchdog.core.sync.sync_abstract import ISyncManager


class DummySyncManager(ISyncManager):
    def __init__(self, interactions):
        super().__init__(interactions)
        self.synced_records = []

    def sync_record_to_database(self, local_record):
        self.synced_records.append(local_record)
        return False  # Simulate all files uploaded
