class DummySyncManager:
    def __init__(self, interactions):
        self.interactions = interactions
        self.synced_records = []

    def sync_record_to_database(self, local_record):
        self.synced_records.append(local_record)
        # Mark all files as uploaded
        for file_path in local_record.files_uploaded.keys():
            local_record.mark_uploaded(file_path)
        return True  # Simulate all files uploaded
