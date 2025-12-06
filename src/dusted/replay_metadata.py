import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox

from dustmaker.replay import Character

from dusted.dialog import Dialog

CHARACTER_NAMES = ["Dustman", "Dustgirl", "Dustkid", "Dustworth"]


@dataclass
class ReplayMetadata:
    character: Character
    level: str


class ReplayMetadataDialog(Dialog):
    def __init__(
        self,
        app,
        callback,
        *,
        defaults: ReplayMetadata | None = None,
        creating=False,
    ):
        super().__init__(app)
        self.callback = callback

        character_label = tk.Label(self, text="Character:")
        character_label.grid(row=0, column=0, sticky="e")
        self.character_var = tk.StringVar(self)
        character_choice = tk.OptionMenu(self, self.character_var, *CHARACTER_NAMES)
        character_choice.grid(row=0, column=1, sticky="ew")

        level_label = tk.Label(self, text="Level id:")
        level_label.grid(row=1, column=0, sticky="e")
        self.level_var = tk.StringVar(self)
        level_entry = tk.Entry(self, textvariable=self.level_var)
        level_entry.grid(row=1, column=1, sticky="ew")

        button = tk.Button(self, text="Create" if creating else "Save", command=self.ok)
        button.grid(row=2, columnspan=2)

        if defaults is None:
            defaults = ReplayMetadata(Character.DUSTMAN, "")
        self.character_var.set(CHARACTER_NAMES[defaults.character.value])
        self.level_var.set(defaults.level)

        self.bind("<Return>", lambda e: self.ok())

    def ok(self):
        character = Character(CHARACTER_NAMES.index(self.character_var.get()))
        level = self.level_var.get()

        if not level:
            messagebox.showwarning(message="Level cannot be empty.")
            return

        self.callback(ReplayMetadata(character, level))
        self.destroy()
