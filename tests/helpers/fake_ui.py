# tests/helpers/fake_ui.py
from dpost.application.ports.interactions import (
    RenameDecision,
    RenamePrompt,
    UserInteractionPort,
)
from dpost.application.ports.ui import SessionPromptDetails


class HeadlessUI(UserInteractionPort):
    def __init__(self, *, use_virtual_time: bool = False):
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
        self.use_virtual_time = use_virtual_time
        self.virtual_time_ms = 0
        self._virtual_scheduled = []
        self._cancelled_task_handles = set()

        # For compatibility with existing tests
        self.calls = {
            "show_warning": [],
            "show_info": [],
            "show_error": [],
            "prompt_rename": [],
            "prompt_append_record": [],
            "show_rename_dialog": [],
        }
        self.prompt_rename_return = None
        self.prompt_append_record_return = None
        self.show_rename_dialog_return = None

        self.session_details_history = []

    # ------------------------------------------------------------------
    # UserInterface methods
    # ------------------------------------------------------------------
    def initialize(self):
        pass

    def destroy(self):
        self.destroyed = True

    def get_root(self):
        return None

    def run_main_loop(self):
        pass

    def show_warning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))
        self.calls["show_warning"].append((title, message))

    def show_info(self, title: str, message: str) -> None:
        self.infos.append((title, message))
        self.calls["show_info"].append((title, message))

    def show_error(self, title: str, message: str) -> None:
        self.errors.append((title, message))
        self.calls["show_error"].append((title, message))

    def prompt_rename(self):
        self.calls["prompt_rename"].append("called")
        if self.prompt_rename_return is not None:
            return self.prompt_rename_return
        return {"name": "test", "institute": "ipat", "sample_ID": "sample"}

    def show_rename_dialog(self, attempted_filename, analysis):
        self.calls["show_rename_dialog"].append((attempted_filename, analysis))
        if self.show_rename_dialog_return is not None:
            return self.show_rename_dialog_return
        if self.rename_inputs:
            return self.rename_inputs.pop(0)
        return None

    def prompt_append_record(self, record_name: str) -> bool:
        self.append_prompts.append(record_name)
        self.calls["prompt_append_record"].append(record_name)
        if self.prompt_append_record_return is not None:
            return self.prompt_append_record_return
        return True

    def show_done_dialog(self, session_details: SessionPromptDetails, on_done_callback):
        self.session_details_history.append(session_details)
        if self.auto_close_session:
            on_done_callback()

    def schedule_task(self, interval_ms, callback):
        self.task_counter += 1  # Increment to get a new unique handle
        handle = self.task_counter
        self.scheduled_tasks.append((interval_ms, callback))
        if self.use_virtual_time:
            delay_ms = interval_ms if isinstance(interval_ms, (int, float)) else 0
            due_ms = self.virtual_time_ms + max(int(delay_ms), 0)
            self._virtual_scheduled.append((due_ms, handle, callback))
        return handle  # Return unique handle

    def cancel_task(self, handle):
        # Align internal counter with the cancelled handle so next schedule returns handle+1
        if isinstance(handle, int):
            self.task_counter = max(self.task_counter, handle)
            if self.use_virtual_time:
                self._cancelled_task_handles.add(handle)

    def next_virtual_due_time_ms(self):
        """Return the next due virtual timestamp or None when no tasks are pending."""
        if not self.use_virtual_time:
            return None
        due_times = [
            due_ms
            for due_ms, handle, _callback in self._virtual_scheduled
            if handle not in self._cancelled_task_handles
        ]
        if not due_times:
            return None
        return min(due_times)

    def run_due_virtual_tasks(self, max_tasks: int | None = None):
        """Run tasks due at the current virtual time and return callback count."""
        if not self.use_virtual_time:
            return 0
        ran = 0
        while True:
            ready_index = None
            ready_item = None
            for idx, item in enumerate(self._virtual_scheduled):
                due_ms, handle, callback = item
                if handle in self._cancelled_task_handles:
                    ready_index = idx
                    ready_item = item
                    break
                if due_ms <= self.virtual_time_ms:
                    ready_index = idx
                    ready_item = item
                    break
            if ready_item is None or ready_index is None:
                break
            self._virtual_scheduled.pop(ready_index)
            _due_ms, handle, callback = ready_item
            if handle in self._cancelled_task_handles:
                self._cancelled_task_handles.discard(handle)
                continue
            callback()
            ran += 1
            if max_tasks is not None and ran >= max_tasks:
                break
        return ran

    def advance_virtual_time(self, milliseconds: int, *, max_tasks: int | None = None):
        """Advance virtual time and run all callbacks due at or before the new time."""
        if not self.use_virtual_time:
            return 0
        self.virtual_time_ms += max(int(milliseconds), 0)
        return self.run_due_virtual_tasks(max_tasks=max_tasks)

    def set_close_handler(self, callback):
        self.close_handler = callback

    def set_exception_handler(self, callback):
        self.exception_handler = callback

    # ------------------------------------------------------------------
    # Interaction port compatibility helpers
    # ------------------------------------------------------------------
    def request_rename(self, prompt: RenamePrompt) -> RenameDecision:
        self.calls["show_rename_dialog"].append(
            (prompt.attempted_prefix, prompt.analysis)
        )
        if prompt.contextual_reason:
            # record contextual hints so tests can inspect them via rename_inputs side effects
            self.calls.setdefault("contextual_reason", []).append(
                prompt.contextual_reason
            )

        if self.show_rename_dialog_return is not None:
            result = self.show_rename_dialog_return
        elif self.rename_inputs:
            result = self.rename_inputs.pop(0)
        else:
            result = None

        if result is None:
            return RenameDecision(cancelled=True, values=None)
        return RenameDecision(cancelled=False, values=result)

    def show_done_prompt(self, session_details: SessionPromptDetails, on_done_callback):
        self.show_done_dialog(session_details, on_done_callback)

    def schedule(self, interval_ms, callback):
        return self.schedule_task(interval_ms, callback)

    def cancel(self, handle):
        self.cancel_task(handle)
