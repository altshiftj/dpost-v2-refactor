"""
gui_manager.py

This module defines classes for handling GUI-related interactions using Tkinter.
It includes a custom Entry widget with placeholder functionality and a dialog
to collect multiple fields from the user when renaming files or folders.
"""

import tkinter as tk
from tkinter import simpledialog

# Custom Entry widget with placeholder text
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
        self.bind("<FocusOut>", self._focus_out)  # Bind event when focus is lost
        self.bind("<Key>", self._key_pressed)      # Bind event on key press
        self._show_placeholder()                    # Initially show placeholder

    def _show_placeholder(self):
        """
        Displays the placeholder text if the entry is empty.
        """
        if not super().get():
            self.insert(0, self.placeholder)
            self['fg'] = self.placeholder_color

    def _hide_placeholder(self):
        """
        Clears the placeholder text and restores the default text color.
        """
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _key_pressed(self, event):
        """
        Event handler for key presses. Clears the placeholder when the user starts typing.
        
        :param event: The Tkinter event object.
        """
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _focus_out(self, event):
        """
        Event handler for losing focus. Restores the placeholder if the entry is empty.
        
        :param event: The Tkinter event object.
        """
        if not super().get():
            self._show_placeholder()

    def get(self):
        """
        Retrieves the current text in the entry. Returns an empty string if only placeholder is present.
        
        :return: The text entered by the user, or an empty string if the placeholder is active.
        """
        content = super().get()
        if self['fg'] == self.placeholder_color:
            return ''
        else:
            return content


# Custom dialog using EntryWithPlaceholder to collect Name, Institute, and Sample Name from users when a file name is incorrect
class MultiFieldDialog(simpledialog.Dialog):
    """
    A custom dialog to collect multiple fields (Name, Institute, Sample Name) from the user.
    
    This dialog is typically invoked when a file or folder name does not adhere to the
    expected naming convention, prompting the user to input the necessary components
    to rename the item correctly.
    """
    def __init__(self, parent, title=None):
        """
        Initializes the MultiFieldDialog.
        
        :param parent: The parent widget.
        :param title: The title of the dialog window.
        """
        super().__init__(parent, title)

    def body(self, master):
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
        self.example_user_ID = "Ex: MuS"
        self.example_institute = "Ex: IPAT"
        self.example_sample_ID = r"Ex: Cathode_20%_SO4_-20C"

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

    def _bring_to_front(self):
        """
        Brings the dialog window to the front and keeps it above other windows.
        """
        self.lift()
        self.wm_attributes("-topmost", True)

    def apply(self):
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
