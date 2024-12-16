import tkinter as tk
from tkinter import simpledialog, messagebox

# Custom Entry widget with placeholder text
class EntryWithPlaceholder(tk.Entry):
    """
    Entry with placeholder text.
    """
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']
        self.bind("<FocusOut>", self._focus_out)
        self.bind("<Key>", self._key_pressed)
        self._show_placeholder()

    def _show_placeholder(self):
        if not super().get():
            self.insert(0, self.placeholder)
            self['fg'] = self.placeholder_color

    def _hide_placeholder(self):
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _key_pressed(self, event):
        if self['fg'] == self.placeholder_color:
            self.delete(0, 'end')
            self['fg'] = self.default_fg_color

    def _focus_out(self, event):
        if not super().get():
            self._show_placeholder()

    def get(self):
        content = super().get()
        if self['fg'] == self.placeholder_color:
            return ''
        else:
            return content

# Custom dialog using EntryWithPlaceholder to collect Name, Institute, and Sample Name from users when a file name is incorrect
class MultiFieldDialog(simpledialog.Dialog):
    """
    Dialog to collect Name, Institute, and Sample Name.
    """
    def __init__(self, parent, title=None):
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="Name:").grid(row=0, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Institute:").grid(row=1, column=0, sticky='e', padx=5, pady=2)
        tk.Label(master, text="Sample-Name:").grid(row=2, column=0, sticky='e', padx=5, pady=2)

        self.user_ID_var = tk.StringVar()
        self.institute_var = tk.StringVar()
        self.sample_ID_var = tk.StringVar()

        self.example_user_ID = "Ex: MuS"
        self.example_institute = "Ex: IPAT"
        self.example_sample_ID = "Ex: Cathode-20XD6-SO4"

        self.name_entry = EntryWithPlaceholder(master, self.example_user_ID, textvariable=self.user_ID_var)
        self.institute_entry = EntryWithPlaceholder(master, self.example_institute, textvariable=self.institute_var)
        self.data_qualifier_entry = EntryWithPlaceholder(master, self.example_sample_ID, textvariable=self.sample_ID_var)

        self.name_entry.grid(row=0, column=1, sticky='we', padx=5, pady=2)
        self.institute_entry.grid(row=1, column=1, sticky='we', padx=5, pady=2)
        self.data_qualifier_entry.grid(row=2, column=1, sticky='we', padx=5, pady=2)

        master.grid_columnconfigure(0, weight=0)
        master.grid_columnconfigure(1, weight=1)
        self.after(0, self._bring_to_front)
        return self.name_entry

    def _bring_to_front(self):
        self.lift()
        self.wm_attributes("-topmost", True)

    def apply(self):
        userID = self.user_ID_var.get()
        institute = self.institute_var.get()
        sample_ID = self.sample_ID_var.get()

        if userID == self.example_user_ID:
            userID = ""
        if institute == self.example_institute:
            institute = ""
        if sample_ID == self.example_sample_ID:
            sample_ID = ""

        self.result = {
            'name': userID,
            'institute': institute,
            'sample_ID': sample_ID,
        }
