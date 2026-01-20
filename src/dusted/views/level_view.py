import math
import tkinter as tk

from dusted import geom, utils
from dusted.models.cursor import Cursor
from dusted.models.level import Level


class LevelView(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        level: Level,
        cursor: Cursor,
    ):
        super().__init__(parent, height=0)

        self._level = level
        self._level.subscribe(self._on_level_change)
        self._cursor = cursor
        self._cursor.subscribe(self._on_cursor_move)

        self.bind("<Button-4>", self._on_scroll)  # Linux
        self.bind("<Button-5>", self._on_scroll)
        self.bind("<MouseWheel>", self._on_scroll)  # Windows
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<B3-Motion>", self._on_right_click)
        self.bind("<Shift-Button-3>", lambda e: self._on_right_click(e, True))
        self.bind("<Shift-B3-Motion>", lambda e: self._on_right_click(e, True))

        self.reset()

    def reset(self) -> None:
        self._zoom_level = 1.0
        self._offset_x = self._offset_y = 0.0
        self._prev_mx = self._prev_my = 0.0
        self._coords: list[tuple[float, float]] = []
        self._path_objects: list[int] = []
        self._position_object: int | None = None
        self.delete("all")

    def _on_level_change(self) -> None:
        self.reset()

        level_data = utils.load_level(self._level.get())
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

    def select_frame(self, frame: int) -> None:
        if self._position_object is not None:
            self.delete(self._position_object)
        if 0 <= frame < len(self._coords):
            x, y = self._coords[frame]
            self._position_object = self.create_rectangle(
                x - 24, y - 48, x + 24, y + 48
            )
            self._transform_object(self._position_object)
        else:
            self._position_object = None

    def add_coordinate(self, frame: int, x: float, y: float) -> None:
        if frame < len(self._coords):  # Clear suffix
            for i in self._path_objects[max(0, frame - 1) :]:
                self.delete(i)
            self._path_objects = self._path_objects[: max(0, frame - 1)]
            self._coords = self._coords[:frame]
        elif frame > len(self._coords):  # Loaded state in the future, pad values
            self._path_objects.extend([-1] * (frame - min(1, len(self._coords)) + 1))
            self._coords.extend([(x, y)] * (frame - len(self._coords) + 1))
            return

        self._coords.append((x, y))
        if frame > 0:
            i = self.create_line(*self._coords[frame - 1], *self._coords[frame])
            self._transform_object(i)
            self._path_objects.append(i)

    def _transform_object(self, i: int) -> None:
        self.scale(i, 0, 0, self._zoom_level, self._zoom_level)
        self.move(i, self._offset_x, self._offset_y)

    def zoom(self, x: float, y: float, scale: float) -> None:
        self._zoom_level *= scale
        self._offset_x = (self._offset_x - x) * scale + x
        self._offset_y = (self._offset_y - y) * scale + y
        self.scale("all", x, y, scale, scale)

    def pan(self, dx: float, dy: float) -> None:
        self._offset_x += dx
        self._offset_y += dy
        self.move("all", dx, dy)

    def _on_cursor_move(self) -> None:
        self.select_frame(self._cursor.current_col)

    def _on_scroll(self, event: tk.Event) -> None:
        if event.num == 4:
            scale = 1.25
        elif event.num == 5:
            scale = 0.8
        else:
            scale = pow(1.25, event.delta // 120)
        self.zoom(event.x, event.y, scale)

    def _on_click(self, event: tk.Event) -> None:
        self._prev_mx = event.x
        self._prev_my = event.y

    def _on_drag(self, event: tk.Event) -> None:
        dx = event.x - self._prev_mx
        dy = event.y - self._prev_my

        self.pan(dx, dy)

        self._prev_mx = event.x
        self._prev_my = event.y

    def _on_right_click(self, event: tk.Event, keep_selection: bool = False) -> None:
        cx = (event.x - self._offset_x) / self._zoom_level
        cy = (event.y - self._offset_y) / self._zoom_level

        closest = None
        dist = 1e10
        for i, (x, y) in enumerate(self._coords):
            d = math.hypot(cx - x, cy - y)
            if d < dist:
                dist = d
                closest = i

        if closest is not None:
            row, _ = self._cursor.position
            self._cursor.set(row, closest, keep_selection)
