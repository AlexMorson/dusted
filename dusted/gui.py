import logging
import os
import queue
import re
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox

from dustmaker.replay import Replay, PlayerData, Character

from dusted import dustforce, utils
from dusted.config import config, ConfigOption
from dusted.cursor import Cursor
from dusted.dialog import SimpleDialog
from dusted.inputs import Inputs
from dusted.inputs_view import InputsView
from dusted.level import Level
from dusted.level_view import LevelView
from dusted.replay_metadata import ReplayMetadataDialog, ReplayMetadata
from dusted.undo_stack import UndoStack

LEVEL_PATTERN = r"START (.*)"
COORD_PATTERN = r"(\d*) (-?\d*) (-?\d*)"

log = logging.getLogger(__name__)


class LoadReplayDialog(SimpleDialog):
    def __init__(self, app):
        super().__init__(app, "Replay id:", "Load")
        self.app = app

    def ok(self, replay_id):
        replay = utils.load_replay_from_dustkid(replay_id)
        self.app.load_replay(replay)
        return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Log exceptions
        self.report_callback_exception = lambda *args: log.error("", exc_info=args)

        self.level = Level("downhill")
        self.character = Character.DUSTMAN
        self.inputs = Inputs()
        self.cursor = Cursor(self.inputs)
        self.undo_stack = UndoStack(self.inputs, self.cursor)
        self.undo_stack.subscribe(self.on_undo_stack_change)

        # Menu bar
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", underline=0, menu=file_menu)

        new_file_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="New", menu=new_file_menu)
        new_file_menu.add_command(label="Empty replay...", command=self.new_file, accelerator="Ctrl+N")
        new_file_menu.add_command(label="From replay id...", command=lambda: LoadReplayDialog(self))

        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=lambda: self.save_file(True), accelerator="Ctrl+Shift+S")

        self.edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", underline=0, menu=self.edit_menu)

        self.edit_menu.add_command(label="Undo", command=self.undo_stack.undo, state=tk.DISABLED, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self.undo_stack.redo, state=tk.DISABLED,
                                   accelerator="Ctrl+Shift+Z")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Replay metadata...", command=self.edit_replay_metadata)

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Settings", underline=0, menu=settings_menu)

        settings_menu.add_command(label="Set Dustforce directory...", command=self.set_dustforce_directory)

        self.config(menu=menu_bar)

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(buttons, text="Watch", command=self.watch)
        button2 = tk.Button(buttons, text="Load State and Watch", command=self.load_state_and_watch)
        canvas = LevelView(self, self.level, self.cursor)
        inputs = InputsView(self, self.inputs, self.cursor, self.undo_stack)

        # Layout
        button1.pack(side=tk.LEFT)
        button2.pack(side=tk.LEFT)
        buttons.pack(anchor=tk.W)
        canvas.pack(fill=tk.BOTH, expand=1)
        inputs.pack(fill=tk.X)

        # Hotkeys
        self.bind("<Control-KeyPress-n>", lambda e: self.new_file())
        self.bind("<Control-KeyPress-o>", lambda e: self.open_file())
        self.bind("<Control-KeyPress-s>", lambda e: self.save_file())
        self.bind("<Control-Shift-KeyPress-S>", lambda e: self.save_file(True))
        self.bind("<F5>", lambda e: self.watch())
        self.bind("<F6>", lambda e: self.load_state_and_watch())

        self.canvas = canvas
        self.file = None
        self.update_title()
        self.after_idle(self.handle_stdout)

        # Check if the Dustforce directory is valid
        if not os.path.isdir(config.get(ConfigOption.DUSTFORCE_PATH)):
            tk.messagebox.showwarning(message="Could not find the Dustforce directory. Please update it in Settings.")

    def update_title(self):
        title = "Dusted"
        if self.file is not None:
            title += f" - {self.file}"
            if self.undo_stack.is_modified:
                title += " [*]"
        self.title(title)

    def handle_stdout(self):
        try:
            while 1:
                line = dustforce.stdout.get_nowait()
                if m := re.match(COORD_PATTERN, line):
                    frame, x, y = map(int, m.group(1, 2, 3))
                    self.canvas.add_coordinate(frame, x, y - 48)
        except queue.Empty:
            self.after(16, self.handle_stdout)

    def watch(self):
        if self.save_file():
            dustforce.watch_replay(self.file)

    def load_state_and_watch(self):
        if self.save_file():
            dustforce.watch_replay_load_state(self.file)

    def save_file(self, save_as: bool = False):
        if not self.file or save_as:
            self.file = tk.filedialog.asksaveasfilename(
                defaultextension=".dfreplay",
                filetypes=[("replay files", "*.dfreplay")],
                title="Save replay"
            )
            if not self.file:
                return False
        elif not self.undo_stack.is_modified:
            return True

        replay = Replay(
            username=b"TAS",
            level=self.level.get().encode(),
            players=[PlayerData(self.character, self.inputs.get_intents())]
        )

        utils.write_replay_to_file(self.file, replay)
        self.undo_stack.set_unmodified()

        return True

    def new_file(self):
        def callback(metadata: ReplayMetadata):
            self.file = None
            self.level.set(metadata.level)
            self.character = metadata.character
            self.inputs.reset()
            self.undo_stack.clear()

        ReplayMetadataDialog(self, callback, creating=True)

    def edit_replay_metadata(self):
        def callback(metadata: ReplayMetadata):
            self.level.set(metadata.level)
            self.character = metadata.character

        metadata = ReplayMetadata(self.character, self.level.get())
        ReplayMetadataDialog(self, callback, defaults=metadata)

    def open_file(self):
        filepath = tk.filedialog.askopenfilename(
            defaultextension=".dfreplay",
            filetypes=[("replay files", "*.dfreplay")],
            title="Load replay"
        )
        if filepath:
            replay = utils.load_replay_from_file(filepath)
            self.load_replay(replay, filepath)

    def load_replay(self, replay: Replay, filepath: str = None):
        self.file = filepath
        self.level.set(replay.level.decode())
        self.character = replay.players[0].character
        self.inputs.set_intents(replay.players[0].intents)

        self.undo_stack.clear()
        if filepath is not None:
            self.undo_stack.set_unmodified()

    def set_dustforce_directory(self):
        current_path = config.get(ConfigOption.DUSTFORCE_PATH)
        new_path = tk.filedialog.askdirectory(initialdir=current_path)
        if new_path:
            config.set(ConfigOption.DUSTFORCE_PATH, new_path)
        config.write()

    def on_undo_stack_change(self):
        undo_state = tk.NORMAL if self.undo_stack.can_undo else tk.DISABLED
        redo_state = tk.NORMAL if self.undo_stack.can_redo else tk.DISABLED

        undo_label = "Undo " + self.undo_stack.undo_text()
        redo_label = "Redo " + self.undo_stack.redo_text()

        self.edit_menu.entryconfig(0, state=undo_state, label=undo_label)
        self.edit_menu.entryconfig(1, state=redo_state, label=redo_label)

        self.update_title()
