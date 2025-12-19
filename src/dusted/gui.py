import logging
import os
import queue
import re
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox

from dustmaker.replay import Character, PlayerData, Replay

from dusted import dustforce, utils
from dusted.config import config
from dusted.cursor import Cursor
from dusted.dialog import SimpleDialog
from dusted.inputs import Inputs
from dusted.inputs_view import InputsView
from dusted.jump_to_frame import JumpToFrameDialog
from dusted.level import Level
from dusted.level_view import LevelView
from dusted.replay_diagnostics import ReplayDiagnostics
from dusted.replay_metadata import ReplayMetadata, ReplayMetadataDialog
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
        self.diagnostics = ReplayDiagnostics(self.inputs)
        self.cursor = Cursor(self.inputs)
        self.undo_stack = UndoStack(self.inputs, self.cursor)
        self.undo_stack.subscribe(self.on_undo_stack_change)

        self.write_config_timer = None

        # Menu bar
        menu_bar = tk.Menu(self)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", underline=0, menu=file_menu)

        new_file_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="New", menu=new_file_menu)
        new_file_menu.add_command(
            label="Empty replay...",
            command=self.new_file,
            accelerator="Ctrl+N",
        )
        new_file_menu.add_command(
            label="From replay id...",
            command=lambda: LoadReplayDialog(self),
        )

        file_menu.add_command(
            label="Open...",
            command=self.open_file,
            accelerator="Ctrl+O",
        )
        file_menu.add_command(
            label="Save",
            command=self.save_file,
            accelerator="Ctrl+S",
        )
        file_menu.add_command(
            label="Save As...",
            command=lambda: self.save_file(True),
            accelerator="Ctrl+Shift+S",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Export as nexus script...",
            command=self.export_as_nexus_script,
        )

        self.edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", underline=0, menu=self.edit_menu)

        self.edit_menu.add_command(
            label="Undo",
            command=self.undo_stack.undo,
            state=tk.DISABLED,
            accelerator="Ctrl+Z",
        )
        self.edit_menu.add_command(
            label="Redo",
            command=self.undo_stack.redo,
            state=tk.DISABLED,
            accelerator="Ctrl+Shift+Z",
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Jump to frame...",
            command=lambda: JumpToFrameDialog(self, self.cursor),
            accelerator="Ctrl+G",
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Replay metadata...",
            command=self.edit_replay_metadata,
        )

        view_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="View", underline=0, menu=view_menu)

        show_level = tk.BooleanVar(self, value=True)
        view_menu.add_checkbutton(
            label="Show level",
            variable=show_level,
            onvalue=True,
            offvalue=False,
        )
        show_level.trace_add(
            "write", lambda *_: self.on_show_level_change(show_level.get())
        )

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Settings", underline=0, menu=settings_menu)

        settings_menu.add_command(
            label="Set Dustforce directory...",
            command=self.set_dustforce_directory,
        )

        self.config(menu=menu_bar)

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(
            buttons,
            text="Watch",
            command=self.watch,
        )
        button2 = tk.Button(
            buttons,
            text="Load State and Watch",
            command=self.load_state_and_watch,
        )
        self.level_view = LevelView(self, self.level, self.cursor)
        inputs_view = InputsView(
            self,
            self.inputs,
            self.diagnostics,
            self.cursor,
            self.undo_stack,
        )

        # Layout
        button1.pack(side=tk.LEFT)
        button2.pack(side=tk.LEFT)

        buttons.grid(row=0, sticky="W")
        self.level_view.grid(row=1, sticky="NSEW")
        inputs_view.grid(row=2, sticky="EW")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Apply config state
        if config.window_geometry:
            self.geometry(config.window_geometry)
        show_level.set(config.show_level)

        # Hotkeys / Callbacks
        self.bind("<Configure>", self.on_configure)
        self.bind("<Control-KeyPress-n>", lambda e: self.new_file())
        self.bind("<Control-KeyPress-o>", lambda e: self.open_file())
        self.bind("<Control-KeyPress-s>", lambda e: self.save_file())
        self.bind("<Control-Shift-KeyPress-S>", lambda e: self.save_file(True))
        self.bind("<F5>", lambda e: self.watch())
        self.bind("<F6>", lambda e: self.load_state_and_watch())

        self.file = None
        self.update_title()
        self.after_idle(self.handle_stdout)

        # Check if the Dustforce directory is valid
        if not os.path.isdir(config.dustforce_path):
            tkinter.messagebox.showwarning(
                message="Could not find the Dustforce directory. Please update it in Settings."
            )

    def write_config_soon(self) -> None:
        """
        Schedule writing the config file.

        This is to debounce successive quick config changes, to avoid
        constantly writing to the disk.
        """

        # If a write has already been scheduled, cancel it.
        if self.write_config_timer is not None:
            self.after_cancel(self.write_config_timer)

        # Schedule a new write soon.
        self.write_config_timer = self.after(ms=1000, func=config.write)

    def on_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return

        geometry = self.geometry()
        if config.window_geometry != geometry:
            config.window_geometry = geometry
            self.write_config_soon()

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
                    self.level_view.add_coordinate(frame, x, y - 48)
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
            self.file = tkinter.filedialog.asksaveasfilename(
                defaultextension=".dfreplay",
                filetypes=[("replay files", "*.dfreplay")],
                title="Save replay",
            )
            if not self.file:
                return False
        elif not self.undo_stack.is_modified:
            return True

        replay = Replay(
            username=b"TAS",
            level=self.level.get().encode(),
            players=[PlayerData(self.character, self.inputs.get_intents())],
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

    def export_as_nexus_script(self) -> None:
        """Export the current inputs as a nexus script."""

        # Show a warning if there are oustanding diagnostics.
        diagnostic_count = len(self.diagnostics.warnings) + len(self.diagnostics.errors)
        if diagnostic_count > 0:
            if not tkinter.messagebox.askokcancel(
                message=f"""\
This replay has {diagnostic_count} unresolved warning/error(s).
The exported nexus script will be legal, but may not play back as expected.""",
                icon="warning",
            ):
                return

        filepath = tkinter.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("nexus scripts", "*.txt")],
            initialdir=os.path.join(config.dustforce_path, "tas"),
            title="Export as nexus script",
        )
        if filepath:
            nexus_script: str = self.diagnostics.nexus_script.serialize()
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(nexus_script)

    def edit_replay_metadata(self):
        def callback(metadata: ReplayMetadata):
            self.level.set(metadata.level)
            self.character = metadata.character

        metadata = ReplayMetadata(self.character, self.level.get())
        ReplayMetadataDialog(self, callback, defaults=metadata)

    def open_file(self):
        filepath = tkinter.filedialog.askopenfilename(
            defaultextension=".dfreplay",
            filetypes=[("replay files", "*.dfreplay")],
            title="Load replay",
        )
        if filepath:
            replay = utils.load_replay_from_file(filepath)
            self.load_replay(replay, filepath)

    def load_replay(self, replay: Replay, filepath: str | None = None) -> None:
        self.file = filepath
        self.level.set(replay.level.decode())
        self.character = replay.players[0].character
        self.inputs.set_intents(replay.players[0].intents)

        self.undo_stack.clear()
        if filepath is not None:
            self.undo_stack.set_unmodified()

    def set_dustforce_directory(self):
        new_path = tkinter.filedialog.askdirectory(initialdir=config.dustforce_path)
        if new_path and config.dustforce_path != new_path:
            config.dustforce_path = new_path
            self.write_config_soon()

    def on_undo_stack_change(self):
        undo_state = tk.NORMAL if self.undo_stack.can_undo else tk.DISABLED
        redo_state = tk.NORMAL if self.undo_stack.can_redo else tk.DISABLED

        undo_label = "Undo " + self.undo_stack.undo_text()
        redo_label = "Redo " + self.undo_stack.redo_text()

        self.edit_menu.entryconfig(0, state=undo_state, label=undo_label)
        self.edit_menu.entryconfig(1, state=redo_state, label=redo_label)

        self.update_title()

    def on_show_level_change(self, show):
        # Process events so that we read up-to-date widget dimensions.
        self.update_idletasks()

        current_width = self.winfo_width()
        requested_height = self.winfo_reqheight()

        if show:
            # Add the level view back into the layout.
            self.level_view.grid()

            # Enable vertical resizing.
            self.resizable(True, True)

            # Give the level view some space to fill.
            self.geometry(f"{current_width}x{requested_height + current_width // 3}")
        else:
            # Remove the level view from the layout.
            self.level_view.grid_remove()

            # Disable vertical resizing.
            self.resizable(True, False)

            # Resize the window to fit contents.
            self.geometry(f"{current_width}x{requested_height}")

            # Increase the maximum window size. For some reason, without this
            # you can't resize the window to be larger than its current size.
            self.maxsize(100_000, 100_000)

        if config.show_level != show:
            config.show_level = show
            self.write_config_soon()
