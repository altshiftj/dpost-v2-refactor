"""Tk dialog helpers used by the dpost desktop runtime UI adapter."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Any

from dpost.application.interactions import DialogPrompts, WarningMessages


class EntryWithPlaceholder(tk.Entry):
    """Entry widget that shows placeholder text while the field is empty."""

    def __init__(
        self,
        master=None,
        placeholder: str = "PLACEHOLDER",
        color: str = "grey",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self["fg"]
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Key>", self._on_key_pressed)
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        if not super().get():
            self.delete(0, tk.END)
            self.insert(0, self.placeholder)
            self["fg"] = self.placeholder_color

    def _on_key_pressed(self, event: Any) -> None:
        if self["fg"] == self.placeholder_color:
            self.delete(0, tk.END)
            self["fg"] = self.default_fg_color

    def _on_focus_out(self, event: Any) -> None:
        if not super().get():
            self._show_placeholder()

    def get(self) -> str:
        if self["fg"] == self.placeholder_color:
            return ""
        return super().get()

    def set(self, value: str) -> None:
        self.delete(0, tk.END)
        if value:
            self["fg"] = self.default_fg_color
            self.insert(0, value)
            return
        self._show_placeholder()


class RenameDialog(simpledialog.Dialog):
    """Modal dialog that guides users through repairing an invalid filename."""

    def __init__(
        self,
        parent: tk.Tk,
        attempted_filename: str,
        violation_info: dict,
        title: str | None = None,
    ) -> None:
        self.result = None
        self.attempted_filename = attempted_filename
        self.violation_info = violation_info
        super().__init__(parent, title or DialogPrompts.RENAME_FILE)

    def body(self, master: tk.Frame) -> tk.Widget:
        self.wm_attributes("-topmost", 1)
        self.lift()
        self.focus_force()
        self.geometry(f"+{self.winfo_screenwidth() // 2 - 200}+0")

        tk.Label(
            master,
            text=DialogPrompts.RENAME_EXAMPLE,
            font=("Arial", 10, "italic"),
        ).pack(pady=(5, 0))

        tk.Label(
            master,
            text=WarningMessages.INVALID_NAME,
            font=("Arial", 10, "bold"),
        ).pack(pady=(5, 0))

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
                master,
                text=f"- {reason}",
                anchor="w",
                justify="left",
                wraplength=400,
            ).pack(fill="x", padx=10)

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

        self.after_idle(self._focus_primary_input)
        return self.user_entry

    def _focus_primary_input(self) -> None:
        try:
            self.user_entry.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def buttonbox(self) -> None:
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
        user = self.user_entry.get().strip()
        institute = self.institute_entry.get().strip()
        sample = self.sample_entry.get().strip()
        self.result = {"name": user, "institute": institute, "sample_ID": sample}
        super().apply()
