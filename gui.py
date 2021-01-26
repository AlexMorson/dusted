import math
import os
import queue
import re
import tkinter as tk
import functools

import dustforce
import geom
import inputs_view
from utils import *

LEVEL_PATTERN = r"START (.*)"
COORD_PATTERN = r"(\d*) (-?\d*) (-?\d*)"


class LevelView(tk.Canvas):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Events
        self.bind("<Button-4>", self.scroll) # Linux
        self.bind("<Button-5>", self.scroll)
        self.bind("<MouseWheel>", self.scroll) # Windows
        self.bind("<Button-1>", self.click)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Button-3>", self.right_click)

        # State
        self.zoom_level = 1
        self.offset_x = self.offset_y = 0
        self.prev_mx = self.prev_my = 0
        self.level_objects = []
        self.path_objects = []
        self.coords = []
        self.position_object = None

    def clear(self):
        self.zoom_level = 1
        self.offset_x = self.offset_y = 0
        for i in self.level_objects: self.delete(i)
        self.level_objects = []
        for i in self.path_objects: self.delete(i)
        self.path_objects = []
        if self.position_object is not None: self.delete(self.position_object)
        self.position_object = None

    def load_level(self, level_id):
        self.clear()
        self.level_id = level_id

        level = fetch_level(level_id)
        tiles = {(x, y) for (l, x, y), t in level.tiles.items() if l == 19}
        outlines = geom.tile_outlines(tiles)
        for outline in outlines:
            i = self.create_polygon(*[(48*x, 48*y) for x, y in outline[0]], fill="#bbb")
            self.level_objects.append(i)
            for hole in outline[1:]:
                i = self.create_polygon(*[(48*x, 48*y) for x, y in hole], fill="#d9d9d9")
                self.level_objects.append(i)

    def select_frame(self, frame):
        if self.position_object is not None: self.delete(self.position_object)
        if frame < len(self.coords):
            x, y = self.coords[frame]
            self.position_object = self.create_rectangle(x-24, y-48, x+24, y+48)
            self.fix_object(self.position_object)
        else:
            self.position_object = None

    def add_coordinate(self, frame, x, y):
        if frame < len(self.coords): # clear suffix
            for i in self.path_objects[max(0, frame-1):]:
                self.delete(i)
            self.path_objects = self.path_objects[:max(0, frame-1)]
            self.coords = self.coords[:frame]

        self.coords.append((x, y-48))
        if frame > 0:
            i = self.create_line(*self.coords[frame-1], *self.coords[frame])
            self.fix_object(i)
            self.path_objects.append(i)

    def fix_object(self, i):
        self.scale(i, 0, 0, self.zoom_level, self.zoom_level)
        self.move(i, self.offset_x, self.offset_y)

    def all_objects(self):
        yield from self.level_objects
        yield from self.path_objects
        if self.position_object: yield self.position_object

    def zoom(self, x, y, scale):
        self.zoom_level *= scale
        self.offset_x = (self.offset_x - x) * scale + x;
        self.offset_y = (self.offset_y - y) * scale + y;
        for i in self.all_objects():
            self.scale(i, x, y, scale, scale)

    def pan(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        for i in self.all_objects():
            self.move(i, dx, dy)

    def scroll(self, event):
        if event.num == 4 or event.delta == 120:
            scale = 1.25
        if event.num == 5 or event.delta == -120:
            scale = 0.8
        self.zoom(event.x, event.y, scale)

    def click(self, event):
        self.prev_mx = event.x
        self.prev_my = event.y

    def drag(self, event):
        dx = event.x - self.prev_mx
        dy = event.y - self.prev_my

        self.pan(dx, dy)

        self.prev_mx = event.x
        self.prev_my = event.y

    def right_click(self, event):
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
            self.app.select_frame(closest)


class ReplayDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)

        self.app = app

        label = tk.Label(self, text="Replay id:")
        entry = tk.Entry(self)
        button = tk.Button(self, text="Load", command=self.load)

        label.pack(side=tk.LEFT)
        entry.pack(side=tk.LEFT)
        button.pack(side=tk.LEFT)

        entry.bind("<Return>", lambda e: self.load())
        entry.focus_set()
        self.entry = entry

        self.attributes('-type', 'dialog')
        self.grab_set()

    def load(self):
        self.app.load_replay(self.entry.get())
        self.destroy()


class LevelDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)

        self.app = app

        label = tk.Label(self, text="Level id:")
        entry = tk.Entry(self)
        button = tk.Button(self, text="Load", command=self.load)

        label.pack(side=tk.LEFT)
        entry.pack(side=tk.LEFT)
        button.pack(side=tk.LEFT)

        entry.bind("<Return>", lambda e: self.load())
        entry.focus_set()
        self.entry = entry

        self.attributes('-type', 'dialog')
        self.grab_set()

    def load(self):
        self.app.load_level(self.entry.get())
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Menu bar
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load replay", command=lambda: ReplayDialog(self))
        filemenu.add_command(label="Load level", command=lambda: LevelDialog(self))
        menubar.add_cascade(label="Load", underline=0, menu=filemenu)
        self.config(menu=menubar)

        self.inputs = inputs_view.Inputs(["10243", "10000000000", "10111111111aaaaaaaaaaaabbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb00000000000000000000000000001111111111", "alsfkjasdflgikjh", "lfshberouibhreoiugsdliggggggggggggggggggggkjjjjjjjjjjjjjjjjjjjjjjjjjeqwwwwwwwwwwwwwwwwwwwwwwwwwwwwh", "wowee", "sdoligkrwjghsipo"])

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(buttons, text="Watch", command=self.watch)
        button2 = tk.Button(buttons, text="Load State and Watch", command=self.load_state_and_watch)
        canvas = LevelView(self, app=self)
        inputs = inputs_view.InputsView(self, self.inputs)

        # Layout
        button1.pack(side=tk.LEFT)
        button2.pack(side=tk.LEFT)
        buttons.pack(anchor=tk.W)
        canvas.pack(fill=tk.BOTH, expand=1)
        inputs.pack(fill=tk.X)

        self.canvas = canvas
        self.character = 0
        self.after(100, self.handle_stdout)

    def handle_stdout(self):
        try:
            while 1:
                line = dustforce.stdout.get_nowait()
                if m := re.match(COORD_PATTERN, line):
                    frame, x, y = map(int, m.group(1, 2, 3))
                    self.canvas.add_coordinate(frame, x, y)
        except queue.Empty:
            self.after(16, self.handle_stdout)

    def select_frame(self, frame):
        self.canvas.select_frame(frame)

    def watch(self):
        inputs = self.inputs.inputs
        write_replay_to_file("test.dfreplay", "TAS!", self.canvas.level_id, self.character, inputs)
        dustforce.watch_replay(os.getcwd() + "/test.dfreplay")

    def load_state_and_watch(self):
        inputs = self.inputs.inputs
        write_replay_to_file("test.dfreplay", "TAS!", self.canvas.level_id, self.character, inputs)
        dustforce.watch_replay_load_state(os.getcwd() + "/test.dfreplay")

    def load_replay(self, replay_id):
        replay = fetch_replay(replay_id)
        self.inputs.load(replay["inputs"][0])
        self.load_level(replay["header"]["levelname"])
        self.character = replay["header"]["characters"][0]

    def load_level(self, level_id):
        self.canvas.load_level(level_id)


if __name__ == "__main__":
    App().mainloop()
