from .broadcaster import Broadcaster


class UndoStack(Broadcaster):
    def __init__(self, inputs, cursor):
        super().__init__()

        self.inputs = inputs
        self.cursor = cursor
        self.undo_stack = []
        self.redo_stack = []

    def clear(self):
        self.undo_stack = []
        self.redo_stack = []
        self.broadcast()

    def execute(self, command):
        command.redo(self.inputs, self.cursor)
        self.undo_stack.append(command)
        self.redo_stack = []
        self.broadcast()

    @property
    def can_undo(self):
        return bool(self.undo_stack)

    @property
    def can_redo(self):
        return bool(self.redo_stack)

    def undo_text(self):
        if not self.undo_stack:
            return ""
        return self.undo_stack[-1].name

    def redo_text(self):
        if not self.redo_stack:
            return ""
        return self.redo_stack[-1].name

    def undo(self):
        if not self.undo_stack:
            return

        command = self.undo_stack.pop()
        command.undo(self.inputs, self.cursor)
        self.redo_stack.append(command)
        self.broadcast()

    def redo(self):
        if not self.redo_stack:
            return

        command = self.redo_stack.pop()
        command.redo(self.inputs, self.cursor)
        self.undo_stack.append(command)
        self.broadcast()
