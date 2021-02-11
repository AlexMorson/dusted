import math
import os
import queue
import re
import tkinter as tk
import tkinter.filedialog

import dustforce
import geom
import inputs_view
import level
from dialog import Dialog
from replay import Replay
from utils import *

LEVEL_PATTERN = r"START (.*)"
COORD_PATTERN = r"(\d*) (-?\d*) (-?\d*)"
CHARACTERS = ["dustman", "dustgirl", "dustworth", "dustkid"]


class LevelView(tk.Canvas):
    def __init__(self, parent, level, cursor):
        super().__init__(parent, height=0)

        self.level = level
        self.level.subscribe(self.on_level_change)
        self.cursor = cursor
        self.cursor.subscribe(self.on_cursor_move)

        self.bind("<Button-4>", self.on_scroll) # Linux
        self.bind("<Button-5>", self.on_scroll)
        self.bind("<MouseWheel>", self.on_scroll) # Windows
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Button-3>", self.on_right_click)

        self.reset()

    def reset(self):
        self.zoom_level = 1
        self.offset_x = self.offset_y = 0
        self.prev_mx = self.prev_my = 0
        self.coords = []
        self.path_objects = []
        self.position_object = None
        self.delete("all")

    def on_level_change(self):
        self.reset()

        level_data = load_level_from_id(self.level.get())
        tiles = {(x, y) for (l, x, y), t in level_data.tiles.items() if l == 19}
        outlines = geom.tile_outlines(tiles)
        for outline in outlines:
            self.create_polygon(*[(48*x, 48*y) for x, y in outline[0]], fill="#bbb")
            for hole in outline[1:]:
                self.create_polygon(*[(48*x, 48*y) for x, y in hole], fill="#d9d9d9")

    def select_frame(self, frame):
        if self.position_object is not None: self.delete(self.position_object)
        if 0 <= frame < len(self.coords):
            x, y = self.coords[frame]
            self.position_object = self.create_rectangle(x-24, y-48, x+24, y+48)
            self.fix_object(self.position_object)
        else:
            self.position_object = None

    def add_coordinate(self, frame, x, y):
        if frame < len(self.coords): # Clear suffix
            for i in self.path_objects[max(0, frame-1):]:
                self.delete(i)
            self.path_objects = self.path_objects[:max(0, frame-1)]
            self.coords = self.coords[:frame]
        elif frame > len(self.coords): # Loaded state in the future, pad values
            self.path_objects.extend([-1] * (frame - min(1, len(self.coords)) + 1))
            self.coords.extend([(x, y)] * (frame - len(self.coords) + 1))
            return

        self.coords.append((x, y))
        if frame > 0:
            i = self.create_line(*self.coords[frame-1], *self.coords[frame])
            self.fix_object(i)
            self.path_objects.append(i)

    def fix_object(self, i):
        self.scale(i, 0, 0, self.zoom_level, self.zoom_level)
        self.move(i, self.offset_x, self.offset_y)

    def zoom(self, x, y, scale):
        self.zoom_level *= scale
        self.offset_x = (self.offset_x - x) * scale + x;
        self.offset_y = (self.offset_y - y) * scale + y;
        self.scale("all", x, y, scale, scale)

    def pan(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        self.move("all", dx, dy)

    def on_cursor_move(self):
        _, col = self.cursor.position()
        self.select_frame(col)

    def on_scroll(self, event):
        if event.num == 4 or event.delta == 120:
            scale = 1.25
        if event.num == 5 or event.delta == -120:
            scale = 0.8
        self.zoom(event.x, event.y, scale)

    def on_click(self, event):
        self.prev_mx = event.x
        self.prev_my = event.y

    def on_drag(self, event):
        dx = event.x - self.prev_mx
        dy = event.y - self.prev_my

        self.pan(dx, dy)

        self.prev_mx = event.x
        self.prev_my = event.y

    def on_right_click(self, event):
        cx = (event.x - self.offset_x) / self.zoom_level
        cy = (event.y - self.offset_y) / self.zoom_level

        closest = None
        dist = 1e10
        for i, (x, y) in enumerate(self.coords):
            d = math.hypot(cx-x, cy-y)
            if d < dist:
                dist = d
                closest = i

        if closest is not None:
            row, _ = self.cursor.position()
            self.cursor.set(row, closest)


class ReplayDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, "Replay id:", "Load")
        self.app = app

    def ok(self, replay_id):
        replay = load_replay_from_id(replay_id)
        self.app.load_replay(replay)
        return True


class LevelDialog(Dialog):
    def __init__(self, app, level):
        super().__init__(app, "Level id:", "Load")
        self.level = level

    def ok(self, text):
        self.level.set(text)
        return True


class SettingsDialog(tk.Toplevel):
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

        self.level = level.Level()
        self.character = 0
        self.inputs = inputs_view.Inputs()
        self.cursor = inputs_view.Cursor(self.inputs)

        # Menu bar
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_file)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        menubar.add_cascade(label="File", underline=0, menu=filemenu)
        loadmenu = tk.Menu(menubar, tearoff=0)
        loadmenu.add_command(label="Load replay", command=lambda: ReplayDialog(self))
        loadmenu.add_command(label="Load level", command=lambda: LevelDialog(self, self.level))
        menubar.add_cascade(label="Load", underline=0, menu=loadmenu)
        self.config(menu=menubar)

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(buttons, text="Watch", command=self.watch)
        button2 = tk.Button(buttons, text="Load State and Watch", command=self.load_state_and_watch)
        canvas = LevelView(self, self.level, self.cursor)
        inputs = inputs_view.InputsView(self, self.inputs, self.cursor)

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

    def select_frame(self, frame):
        self.canvas.select_frame(frame)

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
        write_replay_to_file(self.file, replay)
        return True

    def new_file(self):
        SettingsDialog(self, self.level, self.inputs)

    def open_file(self):
        filepath = tk.filedialog.askopenfilename(
            defaultextension=".dfreplay",
            filetypes=[("replay files", "*.dfreplay")],
            title="Load replay"
        )
        if filepath:
            replay = load_replay_from_file(filepath)
            self.load_replay(replay, filepath)

    def load_replay(self, replay, filepath=None):
        self.file = filepath
        self.level.set(replay.levelname)
        self.character = replay.character
        self.inputs.set(replay.inputs)


if __name__ == "__main__":
    App().mainloop()
