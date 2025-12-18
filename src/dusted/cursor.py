from dusted.broadcaster import Broadcaster
from dusted.inputs import INTENT_COUNT, Inputs


class Cursor(Broadcaster):
    """Manages the cursor and current selection."""

    def __init__(self, inputs: Inputs) -> None:
        super().__init__()
        self.inputs = inputs

        self.start_row = self.start_col = 0
        self.current_row = self.current_col = 0

        self.selection_top = self.selection_bottom = 0
        self.selection_left = self.selection_right = 0

    def is_selected(self, row: int, col: int) -> bool:
        return (
            self.selection_top <= row <= self.selection_bottom
            and self.selection_left <= col <= self.selection_right
        )

    def set(self, row: int, col: int, keep_selection: bool = False) -> None:
        new_row = max(0, min(INTENT_COUNT - 1, row))
        new_col = max(0, min(len(self.inputs), col))

        if new_row == self.current_row and new_col == self.current_col:
            return

        self.current_row = new_row
        self.current_col = new_col

        if not keep_selection:
            self.start_row = self.current_row
            self.start_col = self.current_col

        self._update_selection_vars()

    def select(self, selection: tuple[int, int, int, int]) -> None:
        self.current_row, self.current_col, self.start_row, self.start_col = selection
        self._update_selection_vars()

    def move(
        self,
        row_offset: int,
        col_offset: int,
        keep_selection: bool = False,
    ) -> None:
        self.set(
            row=self.current_row + row_offset,
            col=self.current_col + col_offset,
            keep_selection=keep_selection,
        )

    @property
    def position(self) -> tuple[int, int]:
        return self.current_row, self.current_col

    @property
    def selection(self) -> tuple[int, int, int, int]:
        return (
            self.selection_top,
            self.selection_left,
            self.selection_bottom,
            self.selection_right,
        )

    @property
    def selection_start(self) -> tuple[int, int]:
        return self.selection_top, self.selection_left

    @property
    def selection_end(self) -> tuple[int, int]:
        return self.selection_bottom, self.selection_right

    @property
    def selection_width(self) -> int:
        return self.selection_right - self.selection_left + 1

    @property
    def selection_height(self) -> int:
        return self.selection_bottom - self.selection_top + 1

    @property
    def has_selection(self) -> bool:
        return (
            self.selection_left < self.selection_right
            or self.selection_top < self.selection_bottom
        )

    def _update_selection_vars(self) -> None:
        self.selection_top = min(self.start_row, self.current_row)
        self.selection_bottom = max(self.start_row, self.current_row)
        self.selection_left = min(self.start_col, self.current_col)
        self.selection_right = max(self.start_col, self.current_col)
        self.broadcast()
