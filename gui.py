import queue
import re
import tkinter as tk
import tkinter.filedialog

import dustforce
import utils
from cursor import Cursor
from dialog import Dialog
from inputs import Inputs
from inputs_view import InputsView
from level import Level
from level_view import LevelView
from replay import Replay

LEVEL_PATTERN = r"START (.*)"
COORD_PATTERN = r"(\d*) (-?\d*) (-?\d*)"
CHARACTERS = ["dustman", "dustgirl", "dustworth", "dustkid"]


class LoadReplayDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, "Replay id:", "Load")
        self.app = app

    def ok(self, replay_id):
        replay = utils.load_replay_from_id(replay_id)
        self.app.load_replay(replay)
        return True


class NewReplayDialog(tk.Toplevel):
    def __init__(self, app, level, inputs):
        super().__init__(app)
        self.app = app
        self.level = level
        self.inputs = inputs

        character_label = tk.Label(self, text="Character:")
        character_label.grid(row=0, column=0)
        self.character_var = tk.StringVar(self)
        character_choice = tk.OptionMenu(self, self.character_var, *CHARACTERS)
        character_choice.grid(row=0, column=1)

        level_label = tk.Label(self, text="Level id:")
        level_label.grid(row=1, column=0)
        self.level_entry = tk.Entry(self)
        self.level_entry.grid(row=1, column=1)

        button = tk.Button(self, text="Create", command=self.ok)
        button.grid(row=2, columnspan=2)

        self.character_var.set(CHARACTERS[app.character])

    def ok(self):
        level_id = self.level_entry.get()
        character = CHARACTERS.index(self.character_var.get())
        self.level.set(level_id)
        self.app.character = character
        self.inputs.reset()
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.level = Level()
        self.character = 0
        self.inputs = Inputs()
        self.cursor = Cursor(self.inputs)

        # Menu bar
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        newfilemenu = tk.Menu(filemenu, tearoff=0)

        menubar.add_cascade(label="File", underline=0, menu=filemenu)
        filemenu.add_cascade(label="New", menu=newfilemenu)

        newfilemenu.add_command(label="Empty replay", command=lambda: NewReplayDialog(self, self.level, self.inputs))
        newfilemenu.add_command(label="From replay id", command=lambda: LoadReplayDialog(self))
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        self.config(menu=menubar)

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(buttons, text="Watch", command=self.watch)
        button2 = tk.Button(buttons, text="Load State and Watch", command=self.load_state_and_watch)
        canvas = LevelView(self, self.level, self.cursor)
        inputs = InputsView(self, self.inputs, self.cursor)

        # Layout
        button1.pack(side=tk.LEFT)
        button2.pack(side=tk.LEFT)
        buttons.pack(anchor=tk.W)
        canvas.pack(fill=tk.BOTH, expand=1)
        inputs.pack(fill=tk.X)

        self.canvas = canvas
        self.file = None
        self.after_idle(self.handle_stdout)

    def handle_stdout(self):
        try:
            while 1:
                line = dustforce.stdout.get_nowait()
                if m := re.match(COORD_PATTERN, line):
                    frame, x, y = map(int, m.group(1, 2, 3))
                    self.canvas.add_coordinate(frame, x, y-48)
        except queue.Empty:
            self.after(16, self.handle_stdout)

    def watch(self):
        if self.save_file():
            dustforce.watch_replay(self.file)

    def load_state_and_watch(self):
        if self.save_file():
            dustforce.watch_replay_load_state(self.file)

    def save_file(self):
        if not self.file:
            self.file = tk.filedialog.asksaveasfilename(
                defaultextension=".dfreplay",
                filetypes=[("replay files", "*.dfreplay")],
                title="Save replay"
            )
            if not self.file:
                return False
        replay = Replay("TAS", self.level.get(), self.character, self.inputs.get())
        utils.write_replay_to_file(self.file, replay)
        return True

    def open_file(self):
        filepath = tk.filedialog.askopenfilename(
            defaultextension=".dfreplay",
            filetypes=[("replay files", "*.dfreplay")],
            title="Load replay"
        )
        if filepath:
            replay = utils.load_replay_from_file(filepath)
            self.load_replay(replay, filepath)

    def load_replay(self, replay, filepath=None):
        self.file = filepath
        self.level.set(replay.levelname)
        self.character = replay.character
        self.inputs.set(replay.inputs)


if __name__ == "__main__":
    App().mainloop()
