# tests/helpers/fake_ui.py
from ipat_watchdog.core.ui.ui_abstract import UserInterface

class HeadlessUI(UserInterface):
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []
        self.rename_inputs = []
        self.append_prompts = []
        self.scheduled_tasks = []
        self.close_handler = None
        self.exception_handler = None
        self.destroyed = False

        self.auto_close_session = False  # Control session ending in tests
        self.task_counter = 0  # Ensure unique task handles

    def show_warning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))

    def show_info(self, title: str, message: str) -> None:
        self.infos.append((title, message))

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def prompt_rename(self):
        return {"name": "test", "institute": "ipat", "sample_ID": "sample"}

    def show_rename_dialog(self, attempted_filename, analysis):
        if self.rename_inputs:
            return self.rename_inputs.pop(0)
        return None

    def prompt_append_record(self, record_name: str) -> bool:
        self.append_prompts.append(record_name)
        return True

    def show_done_dialog(self, on_done_callback):
        if self.auto_close_session:
            on_done_callback()

    def initialize(self):
        pass

    def destroy(self):
        self.destroyed = True

    def get_root(self):
        return None

    def schedule_task(self, interval_ms, callback):
        self.task_counter += 1  # Increment to get a new unique handle
        self.scheduled_tasks.append((interval_ms, callback))
        return self.task_counter  # Return unique handle

    def cancel_task(self, handle):
        self.task_counter += 1  # Simulate next unique handle after cancel

    def set_close_handler(self, callback):
        self.close_handler = callback

    def set_exception_handler(self, callback):
        self.exception_handler = callback

    def run_main_loop(self):
        pass
