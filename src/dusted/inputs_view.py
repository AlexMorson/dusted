import tkinter as tk

from dusted.commands import (
    ClearInputsCommand,
    CommandSequence,
    DeleteFramesCommand,
    FillInputsCommand,
    InsertFramesCommand,
    SetInputsCommand,
)
from dusted.dialog import SimpleDialog
from dusted.inputs import DEFAULT_INPUTS, INTENT_COUNT
from dusted.jump_to_frame import JumpToFrameDialog
from dusted.replay_diagnostics import ReplayDiagnostics
from dusted.undo_stack import UndoStack
from dusted.utils import modifier_held

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
    def __init__(self, parent, scrollbar, inputs, diagnostics, cursor, undo_stack):
        super().__init__(
            parent,
            height=GRID_SIZE * (GRID_ROWS + 1),
            borderwidth=0,
            highlightthickness=0,
        )

        self.scrollbar = scrollbar
        self.inputs = inputs
        self.diagnostics = diagnostics
        self.cursor = cursor
        self.undo_stack = undo_stack

        self.pixel_width = 0  # view width
        self.cell_width = 0  # number of cells in view
        self.grid_objects = [[] for _ in range(GRID_ROWS)]
        self.frame_objects = []
        self.current_col = 0
        self.redraw_scheduled = False
        self.drag_timer = None
        self.scroll_fraction = 0

        self.inputs.subscribe(self.redraw)
        self.diagnostics.subscribe(self.redraw)
        self.cursor.subscribe(self.on_cursor_move)

        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Cut", command=self.cut)
        self.context_menu.add_command(label="Copy", command=self.copy)
        self.context_menu.add_command(label="Paste", command=self.paste)
        self.context_menu.add_command(
            label="Insert frames", command=lambda: InsertFramesDialog(self)
        )
        self.context_menu.add_command(label="Delete frames", command=self.delete_frames)

        self.bind("<Configure>", lambda e: self.resize())

        self.bind("<Button-1>", self.on_click)
        self.bind("<Shift-Button-1>", lambda e: self.on_click(e, True))
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", lambda e: self.on_release())
        self.bind("<ButtonRelease-3>", self.on_right_click)
        self.bind("<Button-4>", lambda e: self.on_scroll(tk.SCROLL, -1, tk.UNITS))
        self.bind("<Button-5>", lambda e: self.on_scroll(tk.SCROLL, 1, tk.UNITS))
        self.bind(
            "<MouseWheel>",
            lambda e: self.on_scroll(tk.SCROLL, -e.delta // 120, tk.UNITS),
        )

        self.bind("<Control-KeyPress-x>", lambda e: self.cut())
        self.bind("<Control-KeyPress-c>", lambda e: self.copy())
        self.bind("<Control-KeyPress-v>", lambda e: self.paste())

        self.bind("<Control-KeyPress-z>", lambda e: self.undo_stack.undo())
        self.bind("<Control-Shift-KeyPress-Z>", lambda e: self.undo_stack.redo())

        self.bind("<Delete>", lambda e: self.clear_selection())
        self.bind("<BackSpace>", lambda e: self.clear_selection())

        self.bind("<KeyPress-Left>", lambda e: self.move_cursor(0, -1))
        self.bind("<KeyPress-Right>", lambda e: self.move_cursor(0, 1))
        self.bind("<KeyPress-Up>", lambda e: self.move_cursor(-1, 0))
        self.bind("<KeyPress-Down>", lambda e: self.move_cursor(1, 0))
        self.bind(
            "<KeyPress-Prior>", lambda e: self.move_cursor(0, 1 - self.cell_width)
        )
        self.bind("<KeyPress-Next>", lambda e: self.move_cursor(0, self.cell_width - 1))
        self.bind(
            "<KeyPress-Home>", lambda e: self.cursor.set(self.cursor.position[0], 0)
        )
        self.bind(
            "<KeyPress-End>",
            lambda e: self.cursor.set(self.cursor.position[0], len(self.inputs) - 1),
        )

        self.bind("<Shift-KeyPress-Left>", lambda e: self.move_cursor(0, -1, True))
        self.bind("<Shift-KeyPress-Right>", lambda e: self.move_cursor(0, 1, True))
        self.bind("<Shift-KeyPress-Up>", lambda e: self.move_cursor(-1, 0, True))
        self.bind("<Shift-KeyPress-Down>", lambda e: self.move_cursor(1, 0, True))
        self.bind(
            "<Shift-KeyPress-Prior>",
            lambda e: self.move_cursor(0, 1 - self.cell_width, True),
        )
        self.bind(
            "<Shift-KeyPress-Next>",
            lambda e: self.move_cursor(0, self.cell_width - 1, True),
        )
        self.bind(
            "<Shift-KeyPress-Home>",
            lambda e: self.cursor.set(self.cursor.position[0], 0, True),
        )
        self.bind(
            "<Shift-KeyPress-End>",
            lambda e: self.cursor.set(
                self.cursor.position[0], len(self.inputs) - 1, True
            ),
        )
        self.bind(
            "<Control-KeyPress-g>", lambda e: JumpToFrameDialog(self, self.cursor)
        )

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
                    text = self.create_text(
                        x + 5, GRID_SIZE // 2, text=str(col), anchor="w"
                    )
                    self.frame_objects.append((line, text))

                # Create cells
                for row in range(GRID_ROWS):
                    y = GRID_SIZE * (row + 1)
                    rect = self.create_rectangle(
                        x, y, x + GRID_SIZE, y + GRID_SIZE, outline="gray"
                    )
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
        extra_frames = max(
            0, self.cursor.selection_left + len(block[0]) - self.inputs.length
        )

        self.undo_stack.execute(
            CommandSequence(
                "Paste inputs",
                InsertFramesCommand(self.inputs.length, extra_frames),
                SetInputsCommand(self.cursor.selection_start, block),
            )
        )

    def clear_selection(self):
        self.undo_stack.execute(ClearInputsCommand(self.cursor.selection))

    def insert_frames(self, count):
        self.undo_stack.execute(InsertFramesCommand(self.cursor.selection_left, count))

    def delete_frames(self):
        # Protect against deleting the "frame-after-last"
        width = self.cursor.selection_width
        if self.cursor.selection_right == len(self.inputs):
            width -= 1
        if width == 0:
            return
        self.undo_stack.execute(DeleteFramesCommand(self.cursor.selection_left, width))

    def on_click(self, event, keep_selection=False):
        self.focus_set()

        raw_col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        raw_row = (event.y_root - self.winfo_rooty()) // GRID_SIZE - 2

        # Clamp to the bounds of the view.
        col = max(0, min(self.cell_width - 2, raw_col))
        row = max(0, min(INTENT_COUNT - 1, raw_row))

        self.cursor.set(row, col + self.current_col, keep_selection)

        if self.drag_timer is None:
            self.drag_timer = self.after_idle(self.on_drag_tick)

    def on_drag(self, event):
        raw_col = (event.x_root - self.winfo_rootx()) // GRID_SIZE
        raw_row = (event.y_root - self.winfo_rooty()) // GRID_SIZE - 2

        # Clamp to the bounds of the view.
        col = max(0, min(self.cell_width - 2, raw_col))
        row = max(0, min(INTENT_COUNT - 1, raw_row))

        self.cursor.set(row, col + self.current_col, True)

    def on_drag_tick(self) -> None:
        """Called frequently while dragging."""

        # If the mouse is outside the view, scroll in that direction.
        mouse_x = self.winfo_pointerx() - self.winfo_rootx()
        if mouse_x < 0:
            self.scroll_fraction += mouse_x
        elif mouse_x > (self.cell_width - 1) * GRID_SIZE:
            self.scroll_fraction += mouse_x - (self.cell_width - 1) * GRID_SIZE

        col_offset, self.scroll_fraction = divmod(self.scroll_fraction, GRID_SIZE)
        self.move_cursor(0, col_offset, keep_selection=True)

        self.drag_timer = self.after(33, self.on_drag_tick)

    def on_release(self) -> None:
        if self.drag_timer is not None:
            self.after_cancel(self.drag_timer)
            self.drag_timer = None
            self.scroll_fraction = 0

    def on_right_click(self, event):
        # This widget will not see any mouse release events that are sent while
        # the popup window is open, so emulate one now to be safe.
        self.on_release()

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def on_key(self, event):
        # Ignore special characters and anything with held modifiers
        if not event.char or modifier_held(event.state):
            return

        if fill := self.cursor.has_selection:
            command = FillInputsCommand(self.cursor.selection, event.char.lower())
        else:
            command = SetInputsCommand(self.cursor.position, [[event.char.lower()]])

        if self.cursor.selection_right == len(self.inputs):
            self.undo_stack.execute(
                CommandSequence(
                    "Fill selection" if fill else "Set inputs",
                    InsertFramesCommand(self.cursor.current_col, 1),
                    command,
                )
            )
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

    def move_cursor(
        self,
        row_offset: int,
        col_offset: int,
        keep_selection: bool = False,
    ) -> None:
        """Move the cursor, keeping it on-screen."""

        # Delay our cursor move callback from running until we have finished.
        with self.cursor.batch():
            self.cursor.move(row_offset, col_offset, keep_selection)

            # Check if the cursor is now off-screen.
            _, col = self.cursor.position
            if not (self.current_col <= col < self.current_col + self.cell_width - 1):
                # Scroll the view by the same amount.
                self.current_col = max(
                    0, min(len(self.inputs), self.current_col + col_offset)
                )

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

                    fg = "black"
                    if value == DEFAULT_INPUTS[row]:
                        fg = "lightgray"

                    if self.cursor.is_selected(row, true_col):
                        if value == DEFAULT_INPUTS[row]:
                            fg = "#56a"
                        else:
                            fg = "white"
                        bg = "#24b"
                    elif (row, true_col) in self.diagnostics.warnings:
                        fg = "black"
                        bg = "#e82"
                    elif (row, true_col) in self.diagnostics.errors:
                        fg = "black"
                        bg = "#d22"
                    elif true_col < 55:
                        # Inputs before the player has control
                        bg = "#dfd"
                    elif true_col >= len(self.inputs) - 14:
                        # Inputs that are not early-exit safe
                        bg = "#feb"
                    else:
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
    def __init__(self, parent, inputs, diagnostics, cursor, undo_stack):
        super().__init__(parent)

        for row, text in enumerate(
            [
                "",
                "Frame",
                "X (L/R)",
                "Y (U/D)",
                "Jump",
                "Dash",
                "Fall",
                "Light",
                "Heavy",
                "Taunt",
            ]
        ):
            label = tk.Label(self, text=text, padx=5)
            label.grid(row=row, column=0, sticky="e")

        scrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        grid = Grid(self, scrollbar, inputs, diagnostics, cursor, undo_stack)
        scrollbar.config(command=grid.on_scroll)

        grid.grid(row=0, rowspan=GRID_ROWS + 1, column=1, sticky="ew")
        scrollbar.grid(row=GRID_ROWS + 1, column=1, sticky="ew")

        self.grid_columnconfigure(1, weight=1)


if __name__ == "__main__":
    import random

    from dusted.cursor import Cursor
    from dusted.inputs import Inputs

    class App(tk.Tk):
        def __init__(self):
            super().__init__()

            inputs = []
            for _ in range(8):
                inputs.append(
                    "".join(
                        random.choice("0123456789ab")
                        for _ in range(random.randint(800, 1000))
                    )
                )
            inputs = Inputs(inputs)
            diagnostics = ReplayDiagnostics(inputs)
            cursor = Cursor(inputs)
            undo_stack = UndoStack(inputs, cursor)

            frame = tk.Frame()
            label = tk.Label(frame, text="HI")
            label.pack(fill=tk.BOTH, expand=1)
            inputs_view = InputsView(frame, inputs, diagnostics, cursor, undo_stack)
            inputs_view.pack(fill=tk.X)
            frame.pack(fill=tk.BOTH)

    App().mainloop()
