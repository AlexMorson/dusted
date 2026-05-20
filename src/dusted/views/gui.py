import bisect
import itertools
import logging
import os
import queue
import re
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox

from dustmaker.replay import Character, IntentStream, PlayerData, Replay

from dusted import dustforce, utils
from dusted.config import config
from dusted.models.cursor import Cursor
from dusted.models.inputs import Inputs, Intents
from dusted.models.inputs_grid import InputsGrid
from dusted.models.level import Level
from dusted.models.replay_diagnostics import ReplayDiagnostics
from dusted.models.undo_stack import UndoStack
from dusted.models.value import Value
from dusted.views.diagnostics_summary_view import DiagnosticsSummaryView
from dusted.views.dialog import SimpleDialog
from dusted.views.inputs_view import InputsView
from dusted.views.jump_to_frame import JumpToFrameDialog
from dusted.views.level_view import LevelView
from dusted.views.publish_replay_dialog import PublishReplayDialog
from dusted.views.replay_metadata import ReplayMetadata, ReplayMetadataDialog

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
        self.report_callback_exception = lambda *args: log.exception(
            "Uncaught exception"
        )

        self._filepath = Value[str | None](None)
        self._level = Level("downhill")
        self._character = Value(Character.DUSTMAN)
        self._inputs = Inputs([Intents.default()] * 55)
        self._diagnostics = ReplayDiagnostics(self._inputs)
        self._cursor = Cursor(InputsGrid(self._inputs))
        self._undo_stack = UndoStack(self._inputs, self._cursor)
        self._show_level = Value(config.show_level)

        self._diagnostics.subscribe(self.on_diagnostics_change)
        self._undo_stack.subscribe(self.on_undo_stack_change)
        self._show_level.subscribe(self.on_show_level_change)

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
        file_menu.add_command(
            label="Publish to dustkid...",
            command=self.publish_to_dustkid,
        )

        self.edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", underline=0, menu=self.edit_menu)

        self.edit_menu.add_command(
            label="Undo",
            command=self._undo_stack.undo,
            state=tk.DISABLED,
            accelerator="Ctrl+Z",
        )
        self.edit_menu.add_command(
            label="Redo",
            command=self._undo_stack.redo,
            state=tk.DISABLED,
            accelerator="Ctrl+Shift+Z",
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Jump to frame...",
            command=lambda: JumpToFrameDialog(self, self._cursor),
            accelerator="Ctrl+G",
        )
        self.edit_menu.add_command(
            label="Jump to next error",
            command=self.jump_to_next_diagnostic,
            state=tk.DISABLED,
            accelerator="F2",
        )
        self.edit_menu.add_command(
            label="Jump to previous error",
            command=self.jump_to_previous_diagnostic,
            state=tk.DISABLED,
            accelerator="Shift+F2",
        )
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Replay metadata...",
            command=self.edit_replay_metadata,
        )

        view_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="View", underline=0, menu=view_menu)

        show_level = tk.BooleanVar(self, value=self._show_level.get())
        view_menu.add_checkbutton(
            label="Show level",
            variable=show_level,
            onvalue=True,
            offvalue=False,
        )
        show_level.trace_add("write", lambda *_: self._show_level.set(show_level.get()))

        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Settings", underline=0, menu=settings_menu)

        settings_menu.add_command(
            label="Set Dustforce directory...",
            command=self.set_dustforce_directory,
        )

        self.config(menu=menu_bar)

        # Widgets
        toolbar = tk.Frame(self)
        watch_button = tk.Button(
            toolbar,
            text="Watch",
            command=self.watch,
        )
        load_and_watch_button = tk.Button(
            toolbar,
            text="Load State and Watch",
            command=self.load_state_and_watch,
        )
        diagnostics_summary = DiagnosticsSummaryView(
            toolbar,
            self._diagnostics,
            command_prev=self.jump_to_previous_diagnostic,
            command_next=self.jump_to_next_diagnostic,
        )

        self.level_view = LevelView(self, self._level, self._cursor)
        inputs_view = InputsView(
            self,
            self._inputs,
            self._diagnostics,
            self._cursor,
            self._undo_stack,
        )

        # Layout
        watch_button.pack(side=tk.LEFT)
        load_and_watch_button.pack(side=tk.LEFT)
        diagnostics_summary.pack(side=tk.RIGHT)

        toolbar.grid(row=0, sticky="EW")
        self.level_view.grid(row=1, sticky="NSEW")
        inputs_view.grid(row=2, sticky="EW")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Window state
        if config.window_geometry:
            self.geometry(config.window_geometry)
        self.on_show_level_change()

        self.update_title()

        # Hotkeys / Callbacks
        self.bind("<Configure>", self.on_configure)
        self.bind("<Control-KeyPress-n>", lambda e: self.new_file())
        self.bind("<Control-KeyPress-o>", lambda e: self.open_file())
        self.bind("<Control-KeyPress-s>", lambda e: self.save_file())
        self.bind("<Control-Shift-KeyPress-S>", lambda e: self.save_file(True))
        self.bind("<F2>", lambda e: self.jump_to_next_diagnostic())
        self.bind("<Shift-F2>", lambda e: self.jump_to_previous_diagnostic())
        self.bind("<F5>", lambda e: self.watch())
        self.bind("<F6>", lambda e: self.load_state_and_watch())

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
        filepath = self._filepath.get()
        if filepath is not None:
            title += f" - {filepath}"
            if self._undo_stack.is_modified:
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
            dustforce.watch_replay(self._filepath.get())

    def load_state_and_watch(self):
        if self.save_file():
            dustforce.watch_replay_load_state(self._filepath.get())

    def _current_replay(self) -> Replay:
        """Return a replay instance created from the current application state."""

        intent_streams = {
            IntentStream.X: [intents.x for intents in self._inputs],
            IntentStream.Y: [intents.y for intents in self._inputs],
            IntentStream.JUMP: [intents.jump for intents in self._inputs],
            IntentStream.DASH: [intents.dash for intents in self._inputs],
            IntentStream.FALL: [intents.fall for intents in self._inputs],
            IntentStream.LIGHT: [intents.light for intents in self._inputs],
            IntentStream.HEAVY: [intents.heavy for intents in self._inputs],
            IntentStream.TAUNT: [intents.taunt for intents in self._inputs],
        }
        return Replay(
            username=b"TAS",
            level=self._level.get().encode(),
            players=[PlayerData(self._character.get(), intent_streams)],
        )

    def save_file(self, save_as: bool = False) -> bool:
        """
        Save the current replay to a file.

        :return: True if the file was saved.
        """

        filepath = self._filepath.get()
        if not filepath or save_as:
            filepath = tkinter.filedialog.asksaveasfilename(
                defaultextension=".dfreplay",
                filetypes=[("replay files", "*.dfreplay")],
                title="Save replay",
            )
            if not filepath:
                return False
            self._filepath.set(filepath)
        elif not self._undo_stack.is_modified:
            return True

        replay = self._current_replay()
        utils.write_replay_to_file(filepath, replay)
        self._undo_stack.set_unmodified()

        return True

    def new_file(self):
        def callback(metadata: ReplayMetadata):
            self._filepath.set(None)
            self._level.set(metadata.level)
            self._character.set(metadata.character)
            self._inputs[:] = [Intents.default()] * 55
            self._undo_stack.clear()

        ReplayMetadataDialog(self, callback, creating=True)

    def export_as_nexus_script(self) -> None:
        """Export the current inputs as a nexus script."""

        # Show a warning if there are outstanding diagnostics.
        diagnostic_count = len(self._diagnostics.warnings) + len(
            self._diagnostics.errors
        )
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
            nexus_script: str = self._diagnostics.nexus_script.serialize()
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(nexus_script)

    def publish_to_dustkid(self) -> None:
        """Publish the current replay to dustkid."""

        if self._undo_stack.is_modified:
            tkinter.messagebox.showwarning(
                message="There are unsaved changes. Save or undo the changes before publishing."
            )
            return

        PublishReplayDialog(self, self._current_replay())

    def jump_to_previous_diagnostic(self) -> None:
        """Move the cursor to the next diagnostic."""

        # Sort diagnostics by their column then row.
        ordered_diagnostics = sorted(
            itertools.chain(self._diagnostics.warnings, self._diagnostics.errors),
            key=lambda row_col: (row_col[1], row_col[0]),
        )
        if not ordered_diagnostics:
            return

        # Find the index of the previous diagnostic.
        current_diagnostic_index = bisect.bisect_left(
            ordered_diagnostics,
            (self._cursor.current_col, self._cursor.current_row),
            key=lambda row_col: (row_col[1], row_col[0]),
        )
        if current_diagnostic_index == 0:
            previous_diagnostic_index = len(ordered_diagnostics) - 1
        else:
            previous_diagnostic_index = current_diagnostic_index - 1

        self._cursor.set(*ordered_diagnostics[previous_diagnostic_index])

    def jump_to_next_diagnostic(self) -> None:
        """Move the cursor to the previous diagnostic."""

        # Sort diagnostics by their column then row.
        ordered_diagnostics = sorted(
            itertools.chain(self._diagnostics.warnings, self._diagnostics.errors),
            key=lambda row_col: (row_col[1], row_col[0]),
        )
        if not ordered_diagnostics:
            return

        # Find the index of the next diagnostic.
        next_diagnostic_index = bisect.bisect_right(
            ordered_diagnostics,
            (self._cursor.current_col, self._cursor.current_row),
            key=lambda row_col: (row_col[1], row_col[0]),
        )
        if next_diagnostic_index == len(ordered_diagnostics):
            next_diagnostic_index = 0

        self._cursor.set(*ordered_diagnostics[next_diagnostic_index])

    def edit_replay_metadata(self):
        def callback(metadata: ReplayMetadata):
            self._level.set(metadata.level)
            self._character.set(metadata.character)

        metadata = ReplayMetadata(self._character.get(), self._level.get())
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
        self._filepath.set(filepath)
        self._level.set(replay.level.decode())
        self._character.set(replay.players[0].character)

        inputs: list[Intents] = []
        player_data = replay.players[0]
        frame_count = max(len(stream) for stream in player_data.intents.values())
        for frame in range(frame_count):
            inputs.append(
                Intents(
                    x=player_data.get_intent_value(IntentStream.X, frame),
                    y=player_data.get_intent_value(IntentStream.Y, frame),
                    jump=player_data.get_intent_value(IntentStream.JUMP, frame),
                    dash=player_data.get_intent_value(IntentStream.DASH, frame),
                    fall=player_data.get_intent_value(IntentStream.FALL, frame),
                    light=player_data.get_intent_value(IntentStream.LIGHT, frame),
                    heavy=player_data.get_intent_value(IntentStream.HEAVY, frame),
                    taunt=player_data.get_intent_value(IntentStream.TAUNT, frame),
                )
            )
        self._inputs[:] = inputs

        self._undo_stack.clear()
        if filepath is not None:
            self._undo_stack.set_unmodified()

    def set_dustforce_directory(self):
        new_path = tkinter.filedialog.askdirectory(initialdir=config.dustforce_path)
        if new_path and config.dustforce_path != new_path:
            config.dustforce_path = new_path
            self.write_config_soon()

    def on_diagnostics_change(self) -> None:
        """Called when the diagnostics change."""

        # Enable or disable the jump to next/previous diagnostic menu items.
        diagnostics_state = (
            tk.NORMAL
            if self._diagnostics.errors or self._diagnostics.warnings
            else tk.DISABLED
        )
        self.edit_menu.entryconfig(4, state=diagnostics_state)
        self.edit_menu.entryconfig(5, state=diagnostics_state)

    def on_undo_stack_change(self):
        undo_state = tk.NORMAL if self._undo_stack.can_undo else tk.DISABLED
        redo_state = tk.NORMAL if self._undo_stack.can_redo else tk.DISABLED

        undo_label = "Undo " + self._undo_stack.undo_text()
        redo_label = "Redo " + self._undo_stack.redo_text()

        self.edit_menu.entryconfig(0, state=undo_state, label=undo_label)
        self.edit_menu.entryconfig(1, state=redo_state, label=redo_label)

        self.update_title()

    def on_show_level_change(self) -> None:
        show = self._show_level.get()

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
