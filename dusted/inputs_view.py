import tkinter as tk

from .commands import SetInputsCommand, CommandSequence, InsertFramesCommand, DeleteFramesCommand, FillInputsCommand, \
    ClearInputsCommand
from .dialog import SimpleDialog
from .inputs import INTENT_COUNT
from .undo_stack import UndoStack

GRID_ROWS = INTENT_COUNT + 1
GRID_SIZE = 20


class InsertFramesDialog(SimpleDialog):
    def __init__(self, grid):
        super().__init__(grid, "Number of frames: ", "Insert")
        self.grid = grid

    def ok(self, text):
        try:
            n = int(text)
        except ValueError:
            return False
        if n >= 0:
            self.grid.insert_frames(n)
            return True
        return False


class GridCell:
    def __init__(self, canvas, rect, text):
        self.canvas = canvas
        self.rect_object = rect
        self.text_object = text

        self.state = None
        self.fg = None
        self.bg = None
        self.text = None

    def delete(self):
        self.canvas.delete(self.rect_object)
        self.canvas.delete(self.text_object)

    def config(self, /, state=None, fg=None, bg=None, text=None):
        rect_kwargs = {}
        text_kwargs = {}
        if state is not None and state != self.state:
            rect_kwargs["state"] = state
            text_kwargs["state"] = state
            self.state = state
        if fg is not None and fg != self.fg:
            text_kwargs["fill"] = fg
            self.fg = fg
        if bg is not None and bg != self.bg:
            rect_kwargs["fill"] = bg
            self.bg = bg
        if text is not None and text != self.text:
            text_kwargs["text"] = text
            self.text = text

        if rect_kwargs:
            self.canvas.itemconfig(self.rect_object, **rect_kwargs)
        if text_kwargs:
            self.canvas.itemconfig(self.text_object, **text_kwargs)


class Grid(tk.Canvas):
    def __init__(self, parent, scrollbar, inputs, cursor, undo_stack):
        super().__init__(parent, height=GRID_SIZE * (GRID_ROWS + 1), borderwidth=0, highlightthickness=0)

        self.scrollbar = scrollbar
        self.inputs = inputs
        self.cursor = cursor
        self.undo_stack = undo_stack

        self.pixel_width = 0  # view width
        self.cell_width = 0  # number of cells in view
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
        self.context_menu.add_command(label="Insert frames", command=lambda: InsertFramesDialog(self))
        self.context_menu.add_command(label="Delete frames", command=self.delete_frames)

        self.bind("<Configure>", lambda e: self.resize())

        self.bind("<Button-1>", self.on_click)
        self.bind("<Shift-Button-1>", lambda e: self.on_click(e, True))
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-3>", self.on_right_click)
        self.bind("<Button-4>", lambda e: self.on_scroll(tk.SCROLL, -1, tk.UNITS))
        self.bind("<Button-5>", lambda e: self.on_scroll(tk.SCROLL, 1, tk.UNITS))
        self.bind("<MouseWheel>", lambda e: self.on_scroll(tk.SCROLL, -e.delta // 120, tk.UNITS))

        self.bind("<Control-KeyPress-x>", lambda e: self.cut())
        self.bind("<Control-KeyPress-c>", lambda e: self.copy())
        self.bind("<Control-KeyPress-v>", lambda e: self.paste())

        self.bind("<Control-KeyPress-z>", lambda e: self.undo_stack.undo())
        self.bind("<Control-Shift-KeyPress-Z>", lambda e: self.undo_stack.redo())

        self.bind("<Delete>", lambda e: self.clear_selection())
        self.bind("<BackSpace>", lambda e: self.clear_selection())

        self.bind("<KeyPress-Left>", lambda e: self.cursor.move(0, -1))
        self.bind("<KeyPress-Right>", lambda e: self.cursor.move(0, 1))
        self.bind("<KeyPress-Up>", lambda e: self.cursor.move(-1, 0))
        self.bind("<KeyPress-Down>", lambda e: self.cursor.move(1, 0))
        self.bind("<KeyPress-Prior>", lambda e: self.cursor.move(0, -self.cell_width))
        self.bind("<KeyPress-Next>", lambda e: self.cursor.move(0, self.cell_width))
        self.bind("<KeyPress-Home>", lambda e: self.cursor.set(self.cursor.position[0], 0))
        self.bind("<KeyPress-End>", lambda e: self.cursor.set(self.cursor.position[0], len(self.inputs) - 1))

        self.bind("<Shift-KeyPress-Left>", lambda e: self.cursor.move(0, -1, True))
        self.bind("<Shift-KeyPress-Right>", lambda e: self.cursor.move(0, 1, True))
        self.bind("<Shift-KeyPress-Up>", lambda e: self.cursor.move(-1, 0, True))
        self.bind("<Shift-KeyPress-Down>", lambda e: self.cursor.move(1, 0, True))
        self.bind("<Shift-KeyPress-Prior>", lambda e: self.cursor.move(0, -self.cell_width, True))
        self.bind("<Shift-KeyPress-Next>", lambda e: self.cursor.move(0, self.cell_width, True))
        self.bind("<Shift-KeyPress-Home>", lambda e: self.cursor.set(self.cursor.position[0], 0, True))
        self.bind("<Shift-KeyPress-End>",
                  lambda e: self.cursor.set(self.cursor.position[0], len(self.inputs) - 1, True))

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
                    self.grid_objects[row].append(GridCell(self, rect, text))
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
                    self.grid_objects[row][col].delete()
                    del self.grid_objects[row][col]

        self.pixel_width = new_pixel_width
        self.cell_width = new_cell_width
        self.redraw()

    def cut(self):
        self.copy()
        self.clear_selection()

    def copy(self):
        selection = self.inputs.read(self.cursor.selection)
        self.clipboard_clear()
        self.clipboard_append("\n".join("".join(row) for row in selection))

    def paste(self):
        try:
            inputs = self.clipboard_get()
        except tk.TclError:
            # Clipboard cannot be accessed
            return

        # Convert the clipboard contents into a block of inputs
        block = [list(line) for line in inputs.split("\n")]

        # Ensure that the pasted block lies within the grid
        if self.cursor.selection_top + len(block) > INTENT_COUNT:
            return

        # Check if the input grid needs to be resized
        extra_frames = max(0, self.cursor.selection_left + len(block[0]) - self.inputs.length)

        self.undo_stack.execute(CommandSequence(
            "Paste inputs",
            InsertFramesCommand(self.inputs.length, extra_frames),
            SetInputsCommand(self.cursor.selection_start, block)
        ))

    def clear_selection(self):
        self.undo_stack.execute(ClearInputsCommand(self.cursor.selection))

    def insert_frames(self, count):
        self.undo_stack.execute(InsertFramesCommand(self.cursor.selection_left, count))

    def delete_frames(self):
        self.undo_stack.execute(DeleteFramesCommand(self.cursor.selection_left, self.cursor.selection_width))

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
        # Ignore special characters and anything with held modifiers
        if not event.char or event.state != 0:
            return

        if fill := self.cursor.has_selection:
            command = FillInputsCommand(self.cursor.selection, event.char.lower())
        else:
            command = SetInputsCommand(self.cursor.position, [[event.char.lower()]])

        if self.cursor.selection_right == len(self.inputs):
            self.undo_stack.execute(CommandSequence(
                "Fill selection" if fill else "Set inputs",
                InsertFramesCommand(self.cursor.current_col, 1),
                command
            ))
        else:
            self.undo_stack.execute(command)

    def on_scroll(self, command, *args):
        if command == tk.MOVETO:
            f = max(0.0, min(1.0, float(args[0])))
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
        _, col = self.cursor.position
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
                cell = self.grid_objects[row + 1][col]
                if true_col <= len(self.inputs):
                    if true_col == len(self.inputs):
                        value = ""
                    else:
                        value = self.inputs.at(row, true_col)

                    if self.cursor.is_selected(row, true_col):
                        fg = "white"
                        bg = "#24b"
                    elif row == 4 and value == "1" and self.inputs.at(1, true_col) != "2":
                        # Fastfall without a down input
                        fg = "black"
                        bg = "#d22"
                    elif true_col <= 55:
                        # Inputs before the player has control
                        fg = "black"
                        bg = "#dfd"
                    elif true_col >= len(self.inputs) - 14:
                        # Inputs that are not early-exit safe
                        fg = "black"
                        bg = "#feb"
                    else:
                        fg = "black"
                        bg = "white"

                    cell.config(state="normal", bg=bg, fg=fg, text=value)
                else:
                    cell.config(state="hidden")

            # Draw frame cell
            self.grid_objects[0][col].config(text=str(true_col % 10))

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
            line, text = self.frame_objects[frame_tick]
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
    def __init__(self, parent, inputs, cursor, undo_stack):
        super().__init__(parent)

        for row, text in enumerate(["", "Frame", "X (L/R)", "Y (U/D)", "Jump", "Dash", "Fall", "Light", "Heavy"]):
            label = tk.Label(self, text=text, padx=5)
            label.grid(row=row, column=0, sticky="e")

        scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        grid = Grid(self, scrollbar, inputs, cursor, undo_stack)
        scrollbar.config(command=grid.on_scroll)

        grid.grid(row=0, rowspan=GRID_ROWS + 1, column=1, sticky="ew")
        scrollbar.grid(row=GRID_ROWS + 1, column=1, sticky="ew")

        self.grid_columnconfigure(1, weight=1)


if __name__ == "__main__":
    import random

    from .cursor import Cursor
    from .inputs import Inputs


    class App(tk.Tk):
        def __init__(self):
            super().__init__()

            inputs = []
            for _ in range(7):
                inputs.append("".join(random.choice("0123456789ab") for _ in range(random.randint(800, 1000))))
            inputs = Inputs(inputs)
            cursor = Cursor(inputs)
            undo_stack = UndoStack(inputs, cursor)

            frame = tk.Frame()
            label = tk.Label(frame, text="HI")
            label.pack(fill=tk.BOTH, expand=1)
            inputs_view = InputsView(frame, inputs, cursor, undo_stack)
            inputs_view.pack(fill=tk.X)
            frame.pack(fill=tk.BOTH)


    App().mainloop()
