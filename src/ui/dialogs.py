"""
dialogs.py

This module defines UI dialog components for collecting user input and displaying information.
It provides reusable dialog components that encapsulate specific UI interactions.
"""

import tkinter as tk
from tkinter import simpledialog
from typing import Dict, Optional, Any
from src.ui.ui_messages import DialogPrompts, InfoMessages


class EntryWithPlaceholder(tk.Entry):
    """
    A custom Tkinter Entry widget that displays placeholder text when empty.
    
    Features:
        - Shows placeholder text in a specified color when no user input is present.
        - Clears placeholder text upon user input.
        - Restores placeholder text if the field is left empty after losing focus.
    """
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', *args, **kwargs):
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
        self.default_fg_color = self['fg']  # Store the default text color
        self.bind("<FocusOut>", self._on_focus_out)  # Bind event when focus is lost
        self.bind("<Key>", self._on_key_pressed)      # Bind event on key press
        self._show_placeholder()                    # Initially show placeholder

    def _show_placeholder(self) -> None:
        """
        Displays the placeholder text if the entry is empty.
        """
        if not super().get():
            self.delete(0, tk.END)  # Ensure field is empty before adding placeholder
            self.insert(0, self.placeholder)
            self['fg'] = self.placeholder_color

    def _hide_placeholder(self) -> None:
        """
        Clears the placeholder text and restores the default text color.
        """
        if self['fg'] == self.placeholder_color:
            self.delete(0, tk.END)
            self['fg'] = self.default_fg_color

    def _on_key_pressed(self, event: Any) -> None:
        """
        Event handler for key presses. Clears the placeholder when the user starts typing.
        
        :param event: The Tkinter event object.
        """
        if self['fg'] == self.placeholder_color:
            self.delete(0, tk.END)
            self['fg'] = self.default_fg_color

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
        if self['fg'] == self.placeholder_color:
            return ''
        else:
            return content

    def set(self, value: str) -> None:
        """
        Sets the content of the entry field, handling placeholder text appropriately.
        
        :param value: The value to set in the entry field.
        """
        self.delete(0, tk.END)
        if value:
            self['fg'] = self.default_fg_color
            self.insert(0, value)
        else:
            self._show_placeholder()


class MultiFieldDialog(simpledialog.Dialog):
    """
    A custom dialog to collect multiple fields (Name, Institute, Sample Name) from the user.
    
    This dialog is typically invoked when a file or folder name does not adhere to the
    expected naming convention, prompting the user to input the necessary components
    to rename the item correctly.
    """
    def __init__(self, parent: tk.Tk, title: Optional[str] = None):
        """
        Initializes the MultiFieldDialog.
        
        :param parent: The parent widget.
        :param title: The title of the dialog window.
        """
        self.result = None
        if title is None:
            title = DialogPrompts.RENAME_FILE
        super().__init__(parent, title)

    def body(self, master: tk.Frame) -> tk.Widget:
        """
        Creates the body of the dialog with labels and entry fields for user input.
        
        :param master: The parent widget for the dialog.
        :return: The widget that should have initial focus (name_entry).
        """
        # Create labels for each field
        tk.Label(master, text="Name (Initials):").grid(row=0, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Institute (Initials):").grid(row=1, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Sample Name:").grid(row=2, column=0, sticky='e', padx=5, pady=2)

        # Initialize StringVar instances to hold user input
        self.user_ID_var = tk.StringVar()
        self.institute_var = tk.StringVar()
        self.sample_ID_var = tk.StringVar()

        # Example placeholder texts to guide the user
        self.example_user_ID = DialogPrompts.PLACEHOLDER_USER_ID
        self.example_institute = DialogPrompts.PLACEHOLDER_INSTITUTE
        self.example_sample_ID = DialogPrompts.PLACEHOLDER_SAMPLE_ID

        # Create EntryWithPlaceholder widgets for each field
        self.name_entry = EntryWithPlaceholder(
            master, 
            self.example_user_ID, 
            textvariable=self.user_ID_var
        )
        self.institute_entry = EntryWithPlaceholder(
            master, 
            self.example_institute, 
            textvariable=self.institute_var
        )
        self.data_qualifier_entry = EntryWithPlaceholder(
            master, 
            self.example_sample_ID, 
            textvariable=self.sample_ID_var
        )

        # Place the entry widgets in the grid
        self.name_entry.grid(row=0, column=1, sticky='we', padx=5, pady=2)
        self.institute_entry.grid(row=1, column=1, sticky='we', padx=5, pady=2)
        self.data_qualifier_entry.grid(row=2, column=1, sticky='we', padx=5, pady=2)

        # Configure grid columns to adjust with window resizing
        master.grid_columnconfigure(0, weight=0)  # Labels have fixed width
        master.grid_columnconfigure(1, weight=1)  # Entries expand horizontally

        # Ensure the dialog window is brought to the front
        self.after(0, self._bring_to_front)

        # Return the first entry widget to have initial focus
        return self.name_entry

    def buttonbox(self) -> None:
        """
        Creates the standard OK and Cancel buttons.
        This method is overridden to customize button appearance and behavior.
        """
        box = tk.Frame(self)

        ok_button = tk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        ok_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        cancel_button = tk.Button(box, text="Cancel", width=10, command=self.cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def _bring_to_front(self) -> None:
        """
        Brings the dialog window to the front and keeps it above other windows.
        """
        self.lift()
        self.wm_attributes("-topmost", True)
        self.focus_force()  # Make sure dialog gets focus

    def apply(self) -> None:
        """
        Processes the user input after the dialog is closed with 'OK'.
        
        It retrieves the input from the entry fields, checks if they are still the
        placeholder values, and sets the result accordingly.
        """
        # Retrieve the input from each field
        userID = self.user_ID_var.get()
        institute = self.institute_var.get()
        sample_ID = self.sample_ID_var.get()

        # If the user didn't change the placeholder, treat it as empty input
        if userID == self.example_user_ID:
            userID = ""
        if institute == self.example_institute:
            institute = ""
        if sample_ID == self.example_sample_ID:
            sample_ID = ""

        # Store the result as a dictionary
        self.result = {
            'name': userID,
            'institute': institute,
            'sample_ID': sample_ID
        }

class ViolationHighlightDialog(tk.Toplevel):
    def __init__(self, parent, filename: str, analysis: dict):
        super().__init__(parent)
        self.title("Filename Violation")
        self.attributes("-topmost", True)

        tk.Label(self, text="Invalid Filename", font=("Arial", 12, "bold")).pack(pady=(10, 5))

        # Highlighted text
        text_widget = tk.Text(self, height=2, width=len(filename) + 4)
        text_widget.pack(padx=10)
        text_widget.insert("1.0", filename)
        for start, end in analysis.get("highlight_spans", []):
            tag = f"bad_{start}"
            text_widget.tag_add(tag, f"1.{start}", f"1.{end}")
            text_widget.tag_config(tag, foreground="red", font=("Courier", 10, "bold"))
        text_widget.config(state="disabled")

        # Reasons
        for reason in analysis.get("reasons", []):
            tk.Label(self, text=f"- {reason}", anchor="w", justify="left", wraplength=400).pack(fill="x", padx=10)

        tk.Button(self, text="OK", command=self.destroy).pack(pady=10)


# class MessageDialog(tk.Toplevel):
#     """
#     A custom message dialog that can be used to display messages, warnings, or errors.
#     This provides more control over appearance and behavior than the standard messagebox.
#     """
#     def __init__(self, parent, title, message, message_type='info', on_close=None):
#         """
#         Initialize a custom message dialog.
        
#         :param parent: The parent widget.
#         :param title: The title of the dialog.
#         :param message: The message to display.
#         :param message_type: The type of message ('info', 'warning', 'error').
#         :param on_close: Optional callback when dialog is closed.
#         """
#         super().__init__(parent)
#         self.title(title)
#         self.on_close = on_close
#         self.attributes("-topmost", True)
        
#         # Configure based on message type
#         if message_type == 'warning':
#             bg_color = '#fff3cd'  # Light yellow
#             fg_color = '#856404'  # Dark yellow/gold
#             icon = '⚠️'
#         elif message_type == 'error':
#             bg_color = '#f8d7da'  # Light red
#             fg_color = '#721c24'  # Dark red
#             icon = '❌'
#         else:  # info
#             bg_color = '#d1ecf1'  # Light blue
#             fg_color = '#0c5460'  # Dark blue
#             icon = 'ℹ️'
        
#         # Main frame
#         main_frame = tk.Frame(self, padx=10, pady=10, bg=bg_color)
#         main_frame.pack(fill=tk.BOTH, expand=True)
        
#         # Icon and message
#         header_frame = tk.Frame(main_frame, bg=bg_color)
#         header_frame.pack(fill=tk.X, pady=(0, 10))
        
#         icon_label = tk.Label(header_frame, text=icon, font=("Arial", 24), bg=bg_color, fg=fg_color)
#         icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
#         message_label = tk.Label(main_frame, text=message, wraplength=300, 
#                                justify=tk.LEFT, bg=bg_color, fg=fg_color)
#         message_label.pack(fill=tk.BOTH, expand=True)
        
#         # Button
#         button_frame = tk.Frame(main_frame, bg=bg_color)
#         button_frame.pack(fill=tk.X, pady=(10, 0))
        
#         ok_button = tk.Button(button_frame, text="OK", width=10, command=self.close)
#         ok_button.pack(side=tk.RIGHT)
        
#         # Set up close behavior
#         self.protocol("WM_DELETE_WINDOW", self.close)
#         self.bind("<Escape>", lambda e: self.close())
#         self.bind("<Return>", lambda e: self.close())
        
#         # Center the dialog relative to parent
#         self.geometry("")  # Reset geometry to shrink wrap
#         self.update_idletasks()  # Make sure size is updated
        
#         width = self.winfo_width()
#         height = self.winfo_height()
#         parent_x = parent.winfo_rootx()
#         parent_y = parent.winfo_rooty()
#         parent_width = parent.winfo_width()
#         parent_height = parent.winfo_height()
        
#         x = parent_x + (parent_width - width) // 2
#         y = parent_y + (parent_height - height) // 2
        
#         self.geometry(f"{width}x{height}+{x}+{y}")
        
#         # Focus on dialog
#         self.focus_force()
    
#     def close(self):
#         """Close the dialog and call on_close callback if provided."""
#         if self.on_close:
#             self.on_close()
#         self.destroy()