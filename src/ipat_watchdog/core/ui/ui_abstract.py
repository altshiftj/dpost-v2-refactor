"""Abstract UI contract implemented by concrete frontend adapters."""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Callable

from ipat_watchdog.core.interactions import SessionPromptDetails


class UserInterface(ABC):
    """
    A single abstract interface for all UI implementations.
    Any class that implements this interface can serve as the user interface
    for the application, whether it's Tkinter-based, CLI, or something else.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize any UI components or data. Called before the main loop
        starts running. Use this to set up windows, dialogs, or any needed
        internal structures.
        """
        pass

    # -------------------------------------------------------------------------
    # User Interaction Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """
        Display a warning message to the user.
        """
        pass

    @abstractmethod
    def show_info(self, title: str, message: str) -> None:
        """
        Display an informational message to the user.
        """
        pass

    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """
        Display an error message to the user.
        """
        pass

    @abstractmethod
    def prompt_rename(self) -> Optional[Dict[str, str]]:
        """
        Prompt the user to rename a file or folder.
        Returns a dictionary with user inputs if they confirm,
        or None if they cancel.
        """
        pass

    def show_rename_dialog(
        self, attempted_filename: str, violation_info: Dict[str, str]
    ) -> Optional[Dict[str, str]]:
        """
        Show a unified rename dialog with the attempted filename and violation info.
        Returns a dictionary with user inputs if they confirm, or None if they cancel.
        """
        pass

    @abstractmethod
    def prompt_append_record(self, record_name: str) -> bool:
        """
        Ask the user if they want to append new data to an existing record.
        Returns True if they confirm, False otherwise.
        """
        pass

    @abstractmethod
    def show_done_dialog(
        self, session_details: SessionPromptDetails, on_done_callback: Callable[[], None]
    ) -> None:
        """
        Show a dialog or prompt that the user can acknowledge to end the session.
        Invoke 'on_done_callback' when the user chooses to finish.
        """
        pass

    @abstractmethod
    def get_root(self) -> Any:
        """
        Return the main underlying UI object if applicable (e.g. a Tk root).
        If there's no single root concept, return None.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        """
        Destroy and clean up all UI resources, closing any windows/dialogs if necessary.
        """
        pass

    # -------------------------------------------------------------------------
    # Event-loop Lifecycle Operations
    # -------------------------------------------------------------------------

    @abstractmethod
    def schedule_task(self, interval_ms: int, callback: Callable[[], None]) -> Any:
        """
        Schedule a callback to run once after 'interval_ms' milliseconds.
        Return a handle (e.g., an ID or reference) that can be used to cancel
        the scheduled task if needed.
        """
        pass

    @abstractmethod
    def cancel_task(self, handle: Any) -> None:
        """
        Cancel a previously scheduled task, identified by the 'handle' returned
        from schedule_task(...). No action if the handle is invalid or already canceled.
        """
        pass

    @abstractmethod
    def set_close_handler(self, callback: Callable[[], None]) -> None:
        """
        Set a callback to be invoked if the user attempts to close the UI window.
        """
        pass

    @abstractmethod
    def set_exception_handler(self, callback: Callable[..., None]) -> None:
        """
        Set a global exception handler for the UI environment. If the UI framework
        supports it, uncaught exceptions in the UI thread are passed to this callback.
        """
        pass

    @abstractmethod
    def run_main_loop(self) -> None:
        """
        Start the UI's main event loop. Blocks until the interface is closed or
        otherwise interrupted.
        """
        pass
