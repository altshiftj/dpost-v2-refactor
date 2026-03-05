class FakeFileEventHandler:
    def __init__(self, event_queue):
        self.event_queue = event_queue
        self.created_paths = []

    def on_created(self, event):
        self.created_paths.append(event.src_path)
        self.event_queue.put(event.src_path)

    def get_and_clear_rejected(self):
        return []
