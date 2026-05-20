import math
import tkinter as tk

from dusted import geom, utils


class LevelView(tk.Canvas):
    def __init__(self, parent, level, cursor):
        super().__init__(parent, height=0)

        self.level = level
        self.level.subscribe(self.on_level_change)
        self.cursor = cursor
        self.cursor.subscribe(self.on_cursor_move)

        self.bind("<Button-4>", self.on_scroll)  # Linux
        self.bind("<Button-5>", self.on_scroll)
        self.bind("<MouseWheel>", self.on_scroll)  # Windows
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<B3-Motion>", self.on_right_click)
        self.bind("<Shift-Button-3>", lambda e: self.on_right_click(e, True))
        self.bind("<Shift-B3-Motion>", lambda e: self.on_right_click(e, True))

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

        level_data = utils.load_level(self.level.get())
        tiles = {(x, y) for layer, x, y in level_data.tiles if layer == 19}
        outlines = geom.tile_outlines(tiles)
        for outline in outlines:
            self.create_polygon(*[(48 * x, 48 * y) for x, y in outline[0]], fill="#bbb")
            for hole in outline[1:]:
                self.create_polygon(
                    *[(48 * x, 48 * y) for x, y in hole], fill="#d9d9d9"
                )

        # Pan to level start
        start = level_data.start_position()
        width = self.winfo_width()
        height = self.winfo_height()
        self.pan(width // 2 - start.x, height // 2 - start.y)

    def select_frame(self, frame):
        if self.position_object is not None:
            self.delete(self.position_object)
        if 0 <= frame < len(self.coords):
            x, y = self.coords[frame]
            self.position_object = self.create_rectangle(x - 24, y - 48, x + 24, y + 48)
            self.fix_object(self.position_object)
        else:
            self.position_object = None

    def add_coordinate(self, frame, x, y):
        if frame < len(self.coords):  # Clear suffix
            for i in self.path_objects[max(0, frame - 1) :]:
                self.delete(i)
            self.path_objects = self.path_objects[: max(0, frame - 1)]
            self.coords = self.coords[:frame]
        elif frame > len(self.coords):  # Loaded state in the future, pad values
            self.path_objects.extend([-1] * (frame - min(1, len(self.coords)) + 1))
            self.coords.extend([(x, y)] * (frame - len(self.coords) + 1))
            return

        self.coords.append((x, y))
        if frame > 0:
            i = self.create_line(*self.coords[frame - 1], *self.coords[frame])
            self.fix_object(i)
            self.path_objects.append(i)

    def fix_object(self, i):
        self.scale(i, 0, 0, self.zoom_level, self.zoom_level)
        self.move(i, self.offset_x, self.offset_y)

    def zoom(self, x, y, scale):
        self.zoom_level *= scale
        self.offset_x = (self.offset_x - x) * scale + x
        self.offset_y = (self.offset_y - y) * scale + y
        self.scale("all", x, y, scale, scale)

    def pan(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        self.move("all", dx, dy)

    def on_cursor_move(self):
        self.select_frame(self.cursor.current_col)

    def on_scroll(self, event):
        if event.num == 4:
            scale = 1.25
        elif event.num == 5:
            scale = 0.8
        else:
            scale = pow(1.25, event.delta // 120)
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

    def on_right_click(self, event, keep_selection=False):
        cx = (event.x - self.offset_x) / self.zoom_level
        cy = (event.y - self.offset_y) / self.zoom_level

        closest = None
        dist = 1e10
        for i, (x, y) in enumerate(self.coords):
            d = math.hypot(cx - x, cy - y)
            if d < dist:
                dist = d
                closest = i

        if closest is not None:
            row, _ = self.cursor.position
            self.cursor.set(row, closest, keep_selection)
