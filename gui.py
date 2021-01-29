import math
import os
import queue
import re
import tkinter as tk

import dustforce
import geom
import inputs_view
from dialog import Dialog
from utils import *

LEVEL_PATTERN = r"START (.*)"
COORD_PATTERN = r"(\d*) (-?\d*) (-?\d*)"


class LevelView(tk.Canvas):
    def __init__(self, parent, cursor):
        super().__init__(parent, height=0)

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

    def load_level(self, level_id):
        self.reset()
        self.level_id = level_id

        level = fetch_level(level_id)
        tiles = {(x, y) for (l, x, y), t in level.tiles.items() if l == 19}
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

    def ok(self, text):
        self.app.load_replay(text)
        return True


class LevelDialog(Dialog):
    def __init__(self, app):
        super().__init__(app, "Level id:", "Load")
        self.app = app

    def ok(self, text):
        self.app.load_level(text)
        return True


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
        self.cursor = inputs_view.Cursor(self.inputs)

        # Widgets
        buttons = tk.Frame(self)
        button1 = tk.Button(buttons, text="Watch", command=self.watch)
        button2 = tk.Button(buttons, text="Load State and Watch", command=self.load_state_and_watch)
        canvas = LevelView(self, self.cursor)
        inputs = inputs_view.InputsView(self, self.inputs, self.cursor)

        # Layout
        button1.pack(side=tk.LEFT)
        button2.pack(side=tk.LEFT)
        buttons.pack(anchor=tk.W)
        canvas.pack(fill=tk.BOTH, expand=1)
        inputs.pack(fill=tk.X)

        self.canvas = canvas
        self.character = 0
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
