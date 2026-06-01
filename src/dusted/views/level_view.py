import math
import tkinter as tk

from dusted import geom, utils
from dusted.models.cursor import Cursor
from dusted.models.game_states import GameStates, Node
from dusted.models.inputs import Inputs
from dusted.models.level import Level


class LevelView(tk.Canvas):
    def __init__(
        self,
        parent: tk.Misc,
        level: Level,
        cursor: Cursor,
        inputs: Inputs,
        game_states: GameStates,
    ):
        super().__init__(parent, height=0)

        self._level = level
        self._level.subscribe(self._on_level_change)
        self._cursor = cursor
        self._cursor.subscribe(self._on_cursor_move)
        self._inputs = inputs
        self._inputs.subscribe(self._update_path)
        self._game_states = game_states
        self._game_states.subscribe(self._update_path)

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
        # The current zoom and offset.
        self._zoom_level = 1.0
        self._offset_x = self._offset_y = 0.0

        # Previous mouse position, used for drag events.
        self._prev_mx = self._prev_my = 0.0

        # The final node in the currently shown path.
        self._path_node: Node | None = None

        # The coordinates of each state along the path.
        self._coords: list[tuple[float, float]] = []

        # The objects making up the path.
        self._path_objects: list[int] = []

        # The rectangle showing the position at the current frame.
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

        # Pan to level start.
        start = level_data.start_position()
        width = self.winfo_width()
        height = self.winfo_height()
        self.pan(width // 2 - start.x, height // 2 - start.y)

    def _update_path(self) -> None:
        # Clear the path if there is no state, or it is on a different level.
        current_node = self._game_states.current
        if current_node is None or self._game_states.level != self._level.get():
            while self._path_objects:
                self.delete(self._path_objects.pop())
            self._path_node = None
            self._coords = []
            return

        if self._path_node is None:
            first_differing_frame = 0
        elif ancestor := self._path_node.common_ancestor(current_node):
            first_differing_frame = ancestor.frame + 1
        else:
            first_differing_frame = 0

        # Clear the old suffix.
        remove_objects_from = max(0, first_differing_frame - 1)
        to_remove = self._path_objects[remove_objects_from:]
        for obj in to_remove:
            self.delete(obj)
        del self._path_objects[remove_objects_from:]
        del self._coords[first_differing_frame:]

        # Add the new line segments.
        new_objects = []
        new_coords = []
        next_node = current_node
        while next_node.frame >= first_differing_frame:
            new_coords.append((next_node.state.x, next_node.state.y - 48))
            if next_node.parent is None:
                break
            obj = self.create_line(
                next_node.state.x,
                next_node.state.y - 48,
                next_node.parent.state.x,
                next_node.parent.state.y - 48,
            )
            self._transform_object(obj)
            new_objects.append(obj)
            next_node = next_node.parent

        self._path_objects.extend(reversed(new_objects))
        self._coords.extend(reversed(new_coords))
        self._path_node = current_node

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
