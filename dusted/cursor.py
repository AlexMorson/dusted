from .broadcaster import Broadcaster
from .inputs import INTENT_COUNT


class Cursor(Broadcaster):
    """Manages the cursor and current selection."""

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

        self.start_row = self.start_col = 0
        self.current_row = self.current_col = 0

        self.selection_top = self.selection_bottom = 0
        self.selection_left = self.selection_right = 0

    def write(self, char):
        self.inputs.fill_block(
            self.selection_top, self.selection_left,
            self.selection_bottom + 1, self.selection_right + 1,
            char
        )

    def paste(self, block):
        if self.selection_top + len(block) <= INTENT_COUNT:
            self.inputs.set_block(self.selection_top, self.selection_left, block)

    def read(self):
        return self.inputs.get_block(
            self.selection_top,
            self.selection_left,
            self.selection_bottom + 1,
            min(len(self.inputs), self.selection_right + 1),
        )

    def insert_cols(self, n):
        self.inputs.insert_cols(self.selection_left, n)

    def delete_cols(self):
        self.inputs.delete_cols(
            self.selection_left,
            min(len(self.inputs), self.selection_right + 1)
        )
        self.start_col = self.current_col = self.selection_left
        self._update_selection_vars()

    def clear(self):
        self.inputs.clear_block(
            self.selection_top,
            self.selection_left,
            self.selection_bottom + 1,
            min(len(self.inputs), self.selection_right + 1),
        )

    def is_selected(self, row, col):
        return (
            self.selection_top <= row <= self.selection_bottom and
            self.selection_left <= col <= self.selection_right
        )

    def set(self, row, col, keep_selection=False):
        self.current_row = max(0, min(INTENT_COUNT - 1, row))
        self.current_col = max(0, min(len(self.inputs), col))
        if not keep_selection:
            self.start_row = self.current_row
            self.start_col = self.current_col
        self._update_selection_vars()

    def move(self, row_offset, col_offset, keep_selection=False):
        self.current_row = max(0, min(INTENT_COUNT - 1, self.current_row + row_offset))
        self.current_col = max(0, min(len(self.inputs), self.current_col + col_offset))
        if not keep_selection:
            self.start_row = self.current_row
            self.start_col = self.current_col
        self._update_selection_vars()

    def position(self):
        return self.current_row, self.current_col

    def _update_selection_vars(self):
        self.selection_top    = min(self.start_row, self.current_row)
        self.selection_bottom = max(self.start_row, self.current_row)
        self.selection_left   = min(self.start_col, self.current_col)
        self.selection_right  = max(self.start_col, self.current_col)
        self.broadcast()
