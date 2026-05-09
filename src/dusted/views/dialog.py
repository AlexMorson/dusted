import platform
import tkinter as tk


class Dialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        if platform.system() == "Linux":
            self.attributes("-type", "dialog")
        self.resizable(False, False)
        self.grab_set()
        self.bind("<Escape>", lambda e: self.destroy())


class SimpleDialog(Dialog):
    def __init__(self, parent, label_text, button_text):
        super().__init__(parent)

        label = tk.Label(self, text=label_text)
        entry = tk.Entry(self)
        button = tk.Button(self, text=button_text, command=self._ok)

        label.pack(side=tk.LEFT)
        entry.pack(side=tk.LEFT)
        button.pack(side=tk.LEFT)

        entry.focus_set()
        self.entry = entry
        self.bind("<Return>", lambda e: self._ok())

    def _ok(self):
        if self.ok(self.entry.get()):
            self.destroy()

    def ok(self, text):
        raise NotImplementedError
