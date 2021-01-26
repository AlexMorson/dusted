import random
import functools

import tkinter as tk


GRID_SIZE = 20
GRID_ROWS = 7


class Broadcaster:
    def __init__(self):
        self.callbacks = []

    def subscribe(self, callback):
        self.callbacks.append(callback)

    def broadcast(self):
        for callback in self.callbacks:
            callback()


class Inputs(Broadcaster):
    def __init__(self, inputs):
        super().__init__()
        self.load(inputs)

    def load(self, inputs):
        self.inputs = inputs
        self._max_length = max(len(row) for row in inputs)

        self.s_x1 = self.s_y1 = self.s_x2 = self.s_y2 = 0
        self._update_selection_vars()

    def max_length(self):
        return self._max_length

    def length(self, row):
        return len(self.inputs[row])

    def get(self, row, col):
        return self.inputs[row][col]

    def is_selected(self, row, col):
        return self.s_left <= col <= self.s_right and self.s_top <= row <= self.s_bottom

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
        self.broadcast()


class Grid(tk.Canvas):
    def __init__(self, parent, scrollbar, inputs):
        super().__init__(parent, height=GRID_SIZE*(GRID_ROWS+1), borderwidth=0, highlightthickness=0)

        self.scrollbar = scrollbar
        self.inputs = inputs
        self.inputs.subscribe(lambda: self.redraw(True))

        self.pixel_width = 0 # view width
        self.cell_width = 0 # number of cells in view
        self.grid_objects = [[] for _ in range(GRID_ROWS)]
        self.frame_objects = []
        self.current_col = 0
        self.dirty = False

        self.bind("<Configure>", lambda e: self.resize())

        self.bind("<Button-1>", self.on_click)
        self.bind("<Shift-Button-1>", lambda e: self.on_click(e, True))
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Button-4>", lambda e: self.scroll(tk.SCROLL, -1, tk.UNITS))
        self.bind("<Button-5>", lambda e: self.scroll(tk.SCROLL,  1, tk.UNITS))

        self.bind("<KeyPress-Left>" , lambda e: self.inputs.move_cursor( 0, -1))
        self.bind("<KeyPress-Right>", lambda e: self.inputs.move_cursor( 0,  1))
        self.bind("<KeyPress-Up>"   , lambda e: self.inputs.move_cursor(-1,  0))
        self.bind("<KeyPress-Down>" , lambda e: self.inputs.move_cursor( 1,  0))

        self.bind("<Shift-KeyPress-Left>" , lambda e: self.inputs.move_cursor( 0, -1, True))
        self.bind("<Shift-KeyPress-Right>", lambda e: self.inputs.move_cursor( 0,  1, True))
        self.bind("<Shift-KeyPress-Up>"   , lambda e: self.inputs.move_cursor(-1,  0, True))
        self.bind("<Shift-KeyPress-Down>" , lambda e: self.inputs.move_cursor( 1,  0, True))

    def resize(self):
        new_pixel_width = self.winfo_width()
        new_cell_width = new_pixel_width // GRID_SIZE + 1

        if new_cell_width > self.cell_width:
            for col in range(self.cell_width, new_cell_width):
                x = GRID_SIZE * col
                for row in range(GRID_ROWS):
                    # Create cell
                    y = GRID_SIZE * row
                    rect = self.create_rectangle(x, y, x + GRID_SIZE, y + GRID_SIZE, outline="gray")
                    text = self.create_text(x + GRID_SIZE // 2, y + GRID_SIZE // 2)
                    self.grid_objects[row].append((rect, text))

                # Create frame tick
                if col % 10 == 0:
                    y = GRID_SIZE * GRID_ROWS
                    line = self.create_line(x, y, x, y + GRID_SIZE, width=2)
                    text = self.create_text(x + 5, y + GRID_SIZE // 2, text=str(col), anchor="w")
                    self.frame_objects.append((line, text))
        else:
            for col in reversed(range(new_cell_width, self.cell_width)):
                for row in range(GRID_ROWS):
                    # Delete off-screen cell
                    rect, text = self.grid_objects[row][col]
                    self.delete(rect)
                    self.delete(text)
                    del self.grid_objects[row][col]

                # Delete off-screen frame tick
                if col % 10 == 0:
                    line, text = self.frame_objects[col // 10]
                    self.delete(line)
                    self.delete(text)
                    del self.frame_objects[col // 10]

        self.pixel_width = new_pixel_width
        self.cell_width = new_cell_width
        self.redraw()

    def on_click(self, event, keep_selection=False):
        self.focus_set()
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE
        if 0 <= row <= GRID_ROWS and 0 <= col:
            self.inputs.set_cursor(row, col + self.current_col, keep_selection)

    def on_drag(self, event):
        col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        row = (event.y_root - self.winfo_rooty()) // GRID_SIZE
        if 0 <= row <= GRID_ROWS and 0 <= col:
            self.inputs.set_cursor(row, col + self.current_col, True)

    def redraw(self, force=False):
        self.dirty = True
        if force:
            self._redraw()
        else:
            self.after_idle(self._redraw)

    def _redraw(self):
        if not self.dirty: return
        self.dirty = False

        frame_ticks = 0
        for col in range(self.cell_width):
            for row in range(GRID_ROWS):
                # Draw cell
                rect, text = self.grid_objects[row][col]
                if self.current_col + col < self.inputs.length(row):
                    if self.inputs.is_selected(row, self.current_col + col):
                        fg = "white"
                        bg = "#24b"
                    else:
                        fg = "black"
                        bg = "white"
                    self.itemconfig(rect, state="normal", fill=bg)
                    self.itemconfig(text, state="normal", text=self.inputs.get(row, self.current_col + col), fill=fg)
                else:
                    self.itemconfig(rect, state="hidden")
                    self.itemconfig(text, state="hidden")

            # Draw next frame tick
            if (self.current_col + col) % 10 == 0:
                x = GRID_SIZE * col
                y = GRID_SIZE * GRID_ROWS
                line, text = self.frame_objects[frame_ticks]
                self.coords(line, x, 0, x, y + GRID_SIZE)
                self.coords(text, x + 5, y + GRID_SIZE // 2)
                self.itemconfig(text, text=str(self.current_col + col))
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

        for row, text in enumerate(["X", "Y", "Jump", "Dash", "Fall", "Light", "Heavy", "Frame"]):
            label = tk.Label(self, text=text, padx=5)
            label.grid(row=row, column=0, sticky="e")

        scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        grid = Grid(self, scrollbar, inputs)
        scrollbar.config(command=grid.scroll)

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

        frame = tk.Frame()
        label = tk.Label(frame, text="HI")
        label.pack(fill=tk.BOTH, expand=1)
        inputs_view = InputsView(frame, inputs)
        inputs_view.pack(fill=tk.X)
        frame.pack(fill=tk.BOTH)


if __name__ == "__main__":
    App().mainloop()
