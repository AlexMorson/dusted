from dusted.broadcaster import Broadcaster


class UndoStack(Broadcaster):
    def __init__(self, inputs, cursor):
        super().__init__()

        self.inputs = inputs
        self.cursor = cursor
        self.stack = []
        self.index = 0
        self.unmodified_index = -1

    def clear(self):
        self.stack = []
        self.index = 0
        self.unmodified_index = -1

        self.broadcast()

    def execute(self, command):
        del self.stack[self.index :]
        if self.unmodified_index > self.index:
            self.unmodified_index = -1

        command.redo(self.inputs, self.cursor)
        self.stack.append(command)
        self.index += 1

        self.broadcast()

    @property
    def can_undo(self):
        return self.index > 0

    @property
    def can_redo(self):
        return self.index < len(self.stack)

    @property
    def is_modified(self):
        return self.index != self.unmodified_index

    def set_unmodified(self):
        self.unmodified_index = self.index
        self.broadcast()

    def undo_text(self):
        if not self.can_undo:
            return ""
        return self.stack[self.index - 1].name

    def redo_text(self):
        if not self.can_redo:
            return ""
        return self.stack[self.index].name

    def undo(self):
        if not self.can_undo:
            return

        self.index -= 1
        command = self.stack[self.index]
        command.undo(self.inputs, self.cursor)

        self.broadcast()

    def redo(self):
        if not self.can_redo:
            return

        command = self.stack[self.index]
        self.index += 1
        command.redo(self.inputs, self.cursor)

        self.broadcast()
