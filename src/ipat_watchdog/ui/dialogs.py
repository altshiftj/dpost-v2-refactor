"""
dialogs.py

This module defines UI dialog components for collecting user input and displaying information.
It provides reusable dialog components that encapsulate specific UI interactions.
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
from typing import Optional, Any
from ipat_watchdog.ui.ui_messages import DialogPrompts, WarningMessages 


class EntryWithPlaceholder(tk.Entry):
    """
    A custom Tkinter Entry widget that displays placeholder text when empty.

    Features:
        - Shows placeholder text in a specified color when no user input is present.
        - Clears placeholder text upon user input.
        - Restores placeholder text if the field is left empty after losing focus.
    """

    def __init__(
        self, master=None, placeholder="PLACEHOLDER", color="grey", *args, **kwargs
    ):
        """
        Initializes the EntryWithPlaceholder widget.

        :param master: The parent widget.
        :param placeholder: The placeholder text to display when the entry is empty.
        :param color: The color of the placeholder text.
        :param args: Additional positional arguments for tk.Entry.
        :param kwargs: Additional keyword arguments for tk.Entry.
        """
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self["fg"]  # Store the default text color
        self.bind("<FocusOut>", self._on_focus_out)  # Bind event when focus is lost
        self.bind("<Key>", self._on_key_pressed)  # Bind event on key press
        self._show_placeholder()  # Initially show placeholder

    def _show_placeholder(self) -> None:
        """
        Displays the placeholder text if the entry is empty.
        """
        if not super().get():
            self.delete(0, tk.END)  # Ensure field is empty before adding placeholder
            self.insert(0, self.placeholder)
            self["fg"] = self.placeholder_color

    def _hide_placeholder(self) -> None:
        """
        Clears the placeholder text and restores the default text color.
        """
        if self["fg"] == self.placeholder_color:
            self.delete(0, tk.END)
            self["fg"] = self.default_fg_color

    def _on_key_pressed(self, event: Any) -> None:
        """
        Event handler for key presses. Clears the placeholder when the user starts typing.

        :param event: The Tkinter event object.
        """
        if self["fg"] == self.placeholder_color:
            self.delete(0, tk.END)
            self["fg"] = self.default_fg_color

    def _on_focus_out(self, event: Any) -> None:
        """
        Event handler for losing focus. Restores the placeholder if the entry is empty.

        :param event: The Tkinter event object.
        """
        if not super().get():
            self._show_placeholder()

    def get(self) -> str:
        """
        Retrieves the current text in the entry. Returns an empty string if only placeholder is present.

        :return: The text entered by the user, or an empty string if the placeholder is active.
        """
        content = super().get()
        if self["fg"] == self.placeholder_color:
            return ""
        else:
            return content

    def set(self, value: str) -> None:
        """
        Sets the content of the entry field, handling placeholder text appropriately.

        :param value: The value to set in the entry field.
        """
        self.delete(0, tk.END)
        if value:
            self["fg"] = self.default_fg_color
            self.insert(0, value)
        else:
            self._show_placeholder()


class RenameDialog(simpledialog.Dialog):
    def __init__(
        self,
        parent: tk.Tk,
        attempted_filename: str,
        violation_info: dict,
        title: Optional[str] = None,
    ):
        self.result = None
        self.attempted_filename = attempted_filename
        self.violation_info = violation_info
        if title is None:
            title = DialogPrompts.RENAME_FILE
        super().__init__(parent, title)

    def body(self, master: tk.Frame) -> tk.Widget:
        tk.Label(
            master, text=DialogPrompts.RENAME_EXAMPLE, font=("Arial", 10, "italic")
        ).pack(pady=(5, 0))

        # --- Highlighted Filename Display ---
        tk.Label(master, text=WarningMessages.INVALID_NAME, font=("Arial", 10, "bold")).pack(
            pady=(5, 0)
        )

        text_widget = tk.Text(master, height=1, width=len(self.attempted_filename) + 6)
        text_widget.pack(padx=10, pady=(0, 5))
        text_widget.insert("1.0", self.attempted_filename)
        text_widget.tag_config("center", justify="center")
        text_widget.tag_add("center", "1.0", "end")

        for start, end in self.violation_info.get("highlight_spans", []):
            tag = f"bad_{start}"
            text_widget.tag_add(tag, f"1.{start}", f"1.{end}")
            text_widget.tag_config(tag, foreground="red", font=("Courier", 10, "bold"))
        text_widget.config(state="disabled")

        for reason in self.violation_info.get("reasons", []):
            tk.Label(
                master, text=f"- {reason}", anchor="w", justify="left", wraplength=400
            ).pack(fill="x", padx=10)

        # --- User Input Fields ---
        form_frame = tk.Frame(master)
        form_frame.pack(pady=(10, 0), padx=10, fill="x")

        tk.Label(form_frame, text=DialogPrompts.LABEL_NAME).grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        tk.Label(form_frame, text=DialogPrompts.LABEL_INSTITUTE).grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        tk.Label(form_frame, text=DialogPrompts.LABEL_SAMPLE_NAME).grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )

        self.user_entry = tk.Entry(form_frame)
        self.institute_entry = tk.Entry(form_frame)
        self.sample_entry = tk.Entry(form_frame)

        self.user_entry.grid(row=0, column=1, sticky="we", padx=5, pady=2)
        self.institute_entry.grid(row=1, column=1, sticky="we", padx=5, pady=2)
        self.sample_entry.grid(row=2, column=1, sticky="we", padx=5, pady=2)

        form_frame.grid_columnconfigure(1, weight=1)

        return self.user_entry

    def buttonbox(self):
        box = tk.Frame(self)
        tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE).pack(
            side=tk.LEFT, padx=5, pady=5
        )
        tk.Button(box, text="Cancel", width=10, command=self.cancel).pack(
            side=tk.LEFT, padx=5, pady=5
        )
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def validate(self) -> bool:
        user = self.user_entry.get().strip()
        institute = self.institute_entry.get().strip()
        sample = self.sample_entry.get().strip()

        if not user or not institute or not sample:
            messagebox.showerror(
                WarningMessages.INCOMPLETE_INFO,
                WarningMessages.INCOMPLETE_INFO_DETAILS,
                parent=self,
            )
            return False

        return True

    def apply(self) -> None:
        """
        Called automatically after validate() returns True.
        We only get here if all fields are non-empty (and any other checks pass).
        """
        user = self.user_entry.get().strip()
        institute = self.institute_entry.get().strip()
        sample = self.sample_entry.get().strip()

        self.result = {"name": user, "institute": institute, "sample_ID": sample}

        super().apply()
