import random
import functools

import tkinter as tk


GRID_SIZE = 20
GRID_ROWS = 7


class Inputs:
    def __init__(self, inputs):
        self.load(inputs)

    def load(self, inputs):
        self.inputs = inputs
        self._max_length = max(len(row) for row in inputs)

        self.s_x1 = self.s_y1 = self.s_x2 = self.s_y2 = -1
        self.s_left = self.s_top = self.s_right = self.s_bottom = -1

    def max_length(self):
        return self._max_length

    def length(self, row):
        return len(self.inputs[row])

    def get(self, row, col):
        return self.inputs[row][col]

    def is_selected(self, row, col):
        return self.s_left <= col <= self.s_right and self.s_top <= row <= self.s_bottom

    def write_selection(self, value):
        pass

    def set_cursor(self, row, col, keep_selection=False):
        if keep_selection:
            self.s_x2 = col
            self.s_y2 = row
        else:
            self.s_x1 = self.s_x2 = col
            self.s_y1 = self.s_y2 = row
        self._update_selection_vars()

    def move_cursor(self, row_offset, col_offset, keep_selection=False):
        if keep_selection:
            self.s_x2 += col_offset
            self.s_y2 += row_offset
        else:
            self.s_x1 = self.s_x2 = self.s_x2 + col_offset
            self.s_y1 = self.s_y2 = self.s_y2 + row_offset
        self._update_selection_vars()

    def _update_selection_vars(self):
        self.s_left = min(self.s_x1, self.s_x2)
        self.s_right = max(self.s_x1, self.s_x2)
        self.s_top = min(self.s_y1, self.s_y2)
        self.s_bottom = max(self.s_y1, self.s_y2)

class GridCell(tk.Frame):
    def __init__(self, parent, row, col):
        super().__init__(parent, width=GRID_SIZE, height=GRID_SIZE)

        self.x = GRID_SIZE * col
        self.y = GRID_SIZE * row

        self.pack_propagate(0)
        self.label = tk.Label(self, text="a", borderwidth=1, relief="raised")
        self.label.pack(fill=tk.BOTH, expand=True)

    def bind(self, event, callback):
        self.label.bind(event, callback)

    def highlight(self, do=True):
        if do: self.label.config(fg="white", bg="#24b")
        else: self.label.config(fg="black", bg="#d9d9d9")

    def set_text(self, text):
        self.label.config(text=text)

    def place(self):
        super().place(x=self.x, y=self.y)

    def hide(self):
        self.place_forget()


class Grid(tk.Frame):
    def __init__(self, parent, scrollbar, inputs):
        super().__init__(parent, height=GRID_SIZE*GRID_ROWS)

        self.scrollbar = scrollbar
        self.inputs = inputs

        self.pixel_width = 0 # canvas width
        self.cell_width = 0 # number of cells
        self.cells = [[] for _ in range(GRID_ROWS)]
        self.current_col = 0
        self.dirty = False

        self.bind("<Configure>", lambda e: self.resize())

        self.bind("<KeyPress-Left>", lambda e: self.on_move_cursor(0, -1))
        self.bind("<KeyPress-Right>", lambda e: self.on_move_cursor(0, 1))
        self.bind("<KeyPress-Up>", lambda e: self.on_move_cursor(-1, 0))
        self.bind("<KeyPress-Down>", lambda e: self.on_move_cursor(1, 0))

        self.bind("<Shift-KeyPress-Left>", lambda e: self.on_move_cursor(0, -1, True))
        self.bind("<Shift-KeyPress-Right>", lambda e: self.on_move_cursor(0, 1, True))
        self.bind("<Shift-KeyPress-Up>", lambda e: self.on_move_cursor(-1, 0, True))
        self.bind("<Shift-KeyPress-Down>", lambda e: self.on_move_cursor(1, 0, True))

    def resize(self):
        new_pixel_width = self.winfo_width()
        new_cell_width = new_pixel_width // GRID_SIZE + 1

        if new_cell_width > self.cell_width:
            for row in range(GRID_ROWS):
                for col in range(self.cell_width, new_cell_width):
                    cell = self.create_cell(row, col)
                    cell.place()
                    self.cells[row].append(cell)
        else:
            for row in range(GRID_ROWS):
                for col in reversed(range(new_cell_width, self.cell_width)):
                    self.cells[row][col].destroy()
                    del self.cells[row][col]

        self.pixel_width = new_pixel_width
        self.cell_width = new_cell_width
        self.redraw()

    def create_cell(self, row, col):
        cell = GridCell(self, row, col)
        cell.bind("<Button-4>", lambda e: self.scroll(tk.SCROLL, -1, tk.UNITS))
        cell.bind("<Button-5>", lambda e: self.scroll(tk.SCROLL, 1, tk.UNITS))
        cell.bind("<Button-1>", self.on_click)
        cell.bind("<B1-Motion>", self.on_drag)

        return cell

    def on_move_cursor(self, row_offset, col_offset, keep_selection=False):
        self.inputs.move_cursor(row_offset, col_offset, keep_selection)
        self.redraw()

    def on_click(self, event):
        self.focus_set()
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE
        if 0 <= row <= GRID_ROWS and 0 <= col:
            self.inputs.set_cursor(row, col + self.current_col)
            self.redraw(True)

    def on_drag(self, event):
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE
        if 0 <= row <= GRID_ROWS and 0 <= col:
            self.inputs.set_cursor(row, col + self.current_col, True)
            self.redraw(True)

    def redraw(self, force=False):
        self.dirty = True
        if force:
            self._redraw()
        else:
            self.after_idle(self._redraw)

    def _redraw(self):
        if not self.dirty: return
        self.dirty = False
        for row in range(GRID_ROWS):
            for col in range(self.cell_width):
                cell = self.cells[row][col]
                if self.current_col + col < self.inputs.length(row):
                    cell.highlight(self.inputs.is_selected(row, self.current_col + col))
                    cell.set_text(self.inputs.get(row, self.current_col + col))
                    cell.place()
                else:
                    cell.hide()
        self.update_scrollbar()

    def update_scrollbar(self):
        left = self.current_col
        right = self.current_col + self.cell_width - 1

        left /= self.inputs.max_length()
        right /= self.inputs.max_length()

        self.scrollbar.set(left, right)

    def scroll(self, command, *args):
        if command == tk.MOVETO:
            f = max(0, min(1, float(args[0])))
            col = int(f * self.inputs.max_length())
            self.current_col = col
        elif command == tk.SCROLL:
            direction, size = args
            direction = int(direction)
            if size == tk.UNITS:
                self.current_col += direction
            elif size == tk.PAGES:
                self.current_col += direction * (self.cell_width - 1)
            self.current_col = max(0, min(self.inputs.max_length(), self.current_col))
        self.redraw()


class InputsView(tk.Frame):
    def __init__(self, parent, inputs):
        super().__init__(parent)

        scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        grid = Grid(self, scrollbar, inputs)
        scrollbar.config(command=grid.scroll)

        grid.pack(fill=tk.X)
        scrollbar.pack(fill=tk.X)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        inputs = []
        for _ in range(7):
            inputs.append("".join(random.choice("0123456789ab") for _ in range(random.randint(800, 1000))))
        inputs = Inputs(inputs)

        frame = tk.Frame()
        label = tk.Label(frame, text="HI")
        label.pack(fill=tk.BOTH, expand=1)
        inputs_view = InputsView(frame, inputs)
        inputs_view.pack(fill=tk.X)
        frame.pack(fill=tk.BOTH)


if __name__ == "__main__":
    App().mainloop()
