import random
import tkinter as tk

from dialog import Dialog
from broadcaster import Broadcaster

INTENT_COUNT = 7
GRID_ROWS = INTENT_COUNT + 1
GRID_SIZE = 20

DEFAULT_INPUTS = "1100000"
VALID_INPUTS = [
    "012",
    "012",
    "012",
    "01",
    "01",
    "0123456789ab",
    "0123456789ab"
]


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


class Inputs(Broadcaster):
    """Stores a rectangular grid of inputs."""

    def __init__(self, inputs=None):
        super().__init__()
        if inputs is not None:
            self.set(inputs)
        else:
            self.reset()

    def __len__(self):
        """Return the number of frames that the inputs cover."""
        return self.length

    def reset(self):
        """Reset to default inputs."""
        self.set(list(zip(*[DEFAULT_INPUTS for _ in range(55)])))

    def set(self, inputs):
        """Load a (not necessarily rectangular) grid of inputs."""
        self.length = max(len(line) for line in inputs)
        self.inputs = []
        for line, default in zip(inputs, DEFAULT_INPUTS):
            line_length = len(line)
            # Pad rows to the same length
            self.inputs.append(list(line) + [default] * (self.length - line_length))
        self.broadcast()

    def fill_block(self, top, left, bottom, right, char):
        """Fill a block of the grid with a single character, appending columns if needed."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right
        # Extend the grid if needed
        if right > self.length:
            self.insert_cols(self.length, right - self.length)
        # Fill in the block
        for row in range(max(0, top), min(INTENT_COUNT, bottom)):
            if char in VALID_INPUTS[row]:
                for col in range(left, right):
                    self.inputs[row][col] = char
        self.broadcast()

    def set_block(self, top, left, block):
        """Paste a block of inputs into the grid, appending columns if needed."""
        assert 0 <= top and 0 <= left and top + len(block) <= INTENT_COUNT
        # Extend the grid if needed
        block_right = left + max(len(row) for row in block)
        if block_right > self.length:
            self.insert_cols(self.length, block_right - self.length)
        # Copy over the new block
        for row, line in enumerate(block, start=top):
            for col, char in enumerate(line, start=left):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def delete_cols(self, left, right):
        """Delete some columns of the grid."""
        assert 0 <= left <= right <= self.length
        for row in range(0, INTENT_COUNT):
            del self.inputs[row][left:right]
        self.length -= right - left
        self.broadcast()

    def insert_cols(self, col, n):
        """Insert default-initialised columns into the grid."""
        assert 0 <= col <= self.length
        for row in range(0, INTENT_COUNT):
            self.inputs[row][col:col] = [DEFAULT_INPUTS[row]] * n
        self.length += n
        self.broadcast()

    def clear_block(self, top, left, bottom, right):
        """Reset a block of the grid to the default inputs."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right <= self.length
        for row in range(top, bottom):
            char = DEFAULT_INPUTS[row]
            for col in range(left, right):
                self.inputs[row][col] = char
        self.broadcast()

    def get(self):
        """Return all inputs."""
        return self.inputs

    def get_block(self, top, left, bottom, right):
        """Return a block of the grid."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right <= self.length
        return [list(self.inputs[row][left:right]) for row in range(top, bottom)]

    def at(self, row, col):
        """Return a single cell of the grid."""
        assert 0 <= row < INTENT_COUNT and 0 <= col < self.length
        return self.inputs[row][col]


class InsertFramesDialog(Dialog):
    def __init__(self, parent, cursor):
        super().__init__(parent, "Number of frames: ", "Insert")
        self.cursor = cursor

    def ok(self, text):
        try:
            n = int(text)
        except ValueError:
            return False
        if n >= 0:
            self.cursor.insert_cols(n)
            return True
        return False


class Grid(tk.Canvas):
    def __init__(self, parent, scrollbar, inputs, cursor):
        super().__init__(parent, height=GRID_SIZE*(GRID_ROWS+1), borderwidth=0, highlightthickness=0)

        self.scrollbar = scrollbar
        self.inputs = inputs
        self.cursor = cursor

        self.pixel_width = 0 # view width
        self.cell_width = 0 # number of cells in view
        self.grid_objects = [[] for _ in range(GRID_ROWS)]
        self.frame_objects = []
        self.current_col = 0
        self.redraw_scheduled = False

        self.inputs.subscribe(self.redraw)
        self.cursor.subscribe(self.on_cursor_move)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.cut)
        self.context_menu.add_command(label="Copy", command=self.copy)
        self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_command(label="Insert frames", command=self.insert_frames)
        self.context_menu.add_command(label="Delete frames", command=self.cursor.delete_cols)

        self.bind("<Configure>", lambda e: self.resize())

        self.bind("<Button-1>", self.on_click)
        self.bind("<Shift-Button-1>", lambda e: self.on_click(e, True))
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-3>", self.on_right_click)
        self.bind("<Button-4>", lambda e: self.on_scroll(tk.SCROLL, -1, tk.UNITS))
        self.bind("<Button-5>", lambda e: self.on_scroll(tk.SCROLL,  1, tk.UNITS))

        self.bind("<Control-KeyPress-x>", lambda e: self.cut())
        self.bind("<Control-KeyPress-c>", lambda e: self.copy())
        self.bind("<Control-KeyPress-v>", lambda e: self.paste())

        self.bind("<Delete>", lambda e: self.cursor.clear())
        self.bind("<BackSpace>", lambda e: self.cursor.clear())

        self.bind("<KeyPress-Left>" , lambda e: self.cursor.move( 0, -1))
        self.bind("<KeyPress-Right>", lambda e: self.cursor.move( 0,  1))
        self.bind("<KeyPress-Up>"   , lambda e: self.cursor.move(-1,  0))
        self.bind("<KeyPress-Down>" , lambda e: self.cursor.move( 1,  0))
        self.bind("<KeyPress-Home>" , lambda e: self.cursor.set(self.cursor.position()[0], 0))
        self.bind("<KeyPress-End>"  , lambda e: self.cursor.set(self.cursor.position()[0], len(self.inputs)-1))

        self.bind("<Shift-KeyPress-Left>" , lambda e: self.cursor.move( 0, -1, True))
        self.bind("<Shift-KeyPress-Right>", lambda e: self.cursor.move( 0,  1, True))
        self.bind("<Shift-KeyPress-Up>"   , lambda e: self.cursor.move(-1,  0, True))
        self.bind("<Shift-KeyPress-Down>" , lambda e: self.cursor.move( 1,  0, True))
        self.bind("<Shift-KeyPress-Home>" , lambda e: self.cursor.set(self.cursor.position()[0], 0, True))
        self.bind("<Shift-KeyPress-End>"  , lambda e: self.cursor.set(self.cursor.position()[0], len(self.inputs)-1, True))

        self.bind("<KeyPress>", self.on_key)

    def resize(self):
        new_pixel_width = self.winfo_width()
        new_cell_width = new_pixel_width // GRID_SIZE + 1

        if new_cell_width > self.cell_width:
            for col in range(self.cell_width, new_cell_width):
                x = GRID_SIZE * col

                # Create frame tick
                if col % 10 == 0:
                    line = self.create_line(x, 0, x, GRID_SIZE, width=2)
                    text = self.create_text(x + 5, GRID_SIZE // 2, text=str(col), anchor="w")
                    self.frame_objects.append((line, text))

                # Create cells
                for row in range(GRID_ROWS):
                    y = GRID_SIZE * (row + 1)
                    rect = self.create_rectangle(x, y, x + GRID_SIZE, y + GRID_SIZE, outline="gray")
                    text = self.create_text(x + GRID_SIZE // 2, y + GRID_SIZE // 2)
                    self.grid_objects[row].append((rect, text))
        else:
            for col in reversed(range(new_cell_width, self.cell_width)):
                # Delete off-screen frame ticks
                if col % 10 == 0:
                    line, text = self.frame_objects[col // 10]
                    self.delete(line)
                    self.delete(text)
                    del self.frame_objects[col // 10]

                # Delete off-screen cells
                for row in range(GRID_ROWS):
                    rect, text = self.grid_objects[row][col]
                    self.delete(rect)
                    self.delete(text)
                    del self.grid_objects[row][col]

        self.pixel_width = new_pixel_width
        self.cell_width = new_cell_width
        self.redraw()

    def cut(self):
        self.copy()
        self.cursor.clear()

    def copy(self):
        selection = self.cursor.read()
        self.clipboard_clear()
        self.clipboard_append("\n".join("".join(row) for row in selection))

    def paste(self):
        try:
            inputs = self.clipboard_get()
        except tk.TclError:
            # Clipboard cannot be accessed
            return
        block = [list(line) for line in inputs.split("\n")]
        self.cursor.paste(block)

    def insert_frames(self):
        InsertFramesDialog(self, self.cursor)

    def on_click(self, event, keep_selection=False):
        self.focus_set()
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE - 2
        if 0 <= row < INTENT_COUNT and 0 <= col:
            self.cursor.set(row, col + self.current_col, keep_selection)

    def on_drag(self, event):
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE - 2
        if 0 <= row < INTENT_COUNT and 0 <= col:
            self.cursor.set(row, col + self.current_col, True)

    def on_right_click(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_key(self, event):
        if event.char:
            self.cursor.write(event.char)

    def on_scroll(self, command, *args):
        if command == tk.MOVETO:
            f = max(0, min(1, float(args[0])))
            col = int(f * len(self.inputs))
            self.current_col = col
        elif command == tk.SCROLL:
            direction, size = args
            direction = int(direction)
            if size == tk.UNITS:
                self.current_col += direction
            elif size == tk.PAGES:
                self.current_col += direction * (self.cell_width - 1)
            self.current_col = max(0, min(len(self.inputs), self.current_col))
        self.redraw()

    def on_cursor_move(self):
        row, col = self.cursor.position()
        if not (self.current_col <= col < self.current_col + self.cell_width - 1):
            # Scroll so that the cursor is in the middle of the view
            self.current_col = max(0, min(len(self.inputs), col - self.cell_width // 2))
        self.redraw()

    def redraw(self, force=False):
        if force:
            self._redraw()
        elif not self.redraw_scheduled:
            self.redraw_scheduled = True
            self.after_idle(self._redraw)

    def _redraw(self):
        self.redraw_scheduled = False

        frame_ticks = 0
        for col in range(self.cell_width):
            true_col = self.current_col + col
            # Draw cells
            for row in range(INTENT_COUNT):
                rect, text = self.grid_objects[row+1][col]
                if self.current_col + col <= len(self.inputs):
                    if true_col == len(self.inputs):
                        value = ""
                    else:
                        value = self.inputs.at(row, true_col)
                    if self.cursor.is_selected(row, true_col):
                        fg = "white"
                        bg = "#24b"
                    else:
                        fg = "black"
                        bg = "white"
                    self.itemconfig(rect, state="normal", fill=bg)
                    self.itemconfig(text, state="normal", text=value, fill=fg)
                else:
                    self.itemconfig(rect, state="hidden")
                    self.itemconfig(text, state="hidden")

            # Draw frame cell
            rect, text = self.grid_objects[0][col]
            self.itemconfig(text, text=str(true_col % 10))

            # Draw next frame tick
            if true_col % 10 == 0:
                x = GRID_SIZE * col
                line, text = self.frame_objects[frame_ticks]
                self.coords(line, x, 0, x, (GRID_ROWS + 1) * GRID_SIZE)
                self.coords(text, x + 5, GRID_SIZE // 2)
                self.itemconfig(text, text=str(true_col))
                self.tag_raise(line)
                frame_ticks += 1

        # Hide unused frame ticks
        for frame_tick in range(frame_ticks, len(self.frame_objects)):
            line, text = self.frame_objects[frame_ticks]
            self.coords(line, -1, -1, -1, -1)
            self.itemconfig(text, text="")

        self.update_scrollbar()

    def update_scrollbar(self):
        left = self.current_col
        right = self.current_col + self.cell_width - 1

        length = max(1, len(self.inputs))
        left /= length
        right /= length

        self.scrollbar.set(left, right)


class InputsView(tk.Frame):
    def __init__(self, parent, inputs, cursor):
        super().__init__(parent)

        for row, text in enumerate(["", "Frame", "X", "Y", "Jump", "Dash", "Fall", "Light", "Heavy"]):
            label = tk.Label(self, text=text, padx=5)
            label.grid(row=row, column=0, sticky="e")

        scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        grid = Grid(self, scrollbar, inputs, cursor)
        scrollbar.config(command=grid.on_scroll)

        grid.grid(row=0, rowspan=GRID_ROWS+1, column=1, sticky="ew")
        scrollbar.grid(row=GRID_ROWS+1, column=1, sticky="ew")

        self.grid_columnconfigure(1, weight=1)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        inputs = []
        for _ in range(7):
            inputs.append("".join(random.choice("0123456789ab") for _ in range(random.randint(800, 1000))))
        inputs = Inputs(inputs)
        cursor = Cursor(inputs)

        frame = tk.Frame()
        label = tk.Label(frame, text="HI")
        label.pack(fill=tk.BOTH, expand=1)
        inputs_view = InputsView(frame, inputs, cursor)
        inputs_view.pack(fill=tk.X)
        frame.pack(fill=tk.BOTH)


if __name__ == "__main__":
    App().mainloop()
