from dusted.inputs import INTENT_COUNT


class Command:
    def __init__(self, name):
        self.name = name

    def undo(self, inputs, cursor):
        raise NotImplementedError

    def redo(self, inputs, cursor):
        raise NotImplementedError


class CommandSequence(Command):
    def __init__(self, name, *commands):
        super().__init__(name)
        self.commands = commands

    def redo(self, inputs, cursor):
        for command in self.commands:
            command.redo(inputs, cursor)

    def undo(self, inputs, cursor):
        for command in reversed(self.commands):
            command.undo(inputs, cursor)


class SetInputsCommand(Command):
    def __init__(self, position, new_inputs):
        super().__init__("Set inputs")
        self.position = position
        self.new_inputs = new_inputs
        self.old_inputs = None
        self.old_selection = None

    def redo(self, inputs, cursor):
        if self.old_inputs is None or self.old_selection is None:
            assert self.old_inputs is None and self.old_selection is None
            end = (
                self.position[0] + len(self.new_inputs) - 1,
                self.position[1] + len(self.new_inputs[0]) - 1,
            )
            self.old_inputs = inputs.read((*self.position, *end))
            self.old_selection = cursor.selection

        inputs.write(self.position, self.new_inputs)
        cursor.select(self.old_selection)

    def undo(self, inputs, cursor):
        inputs.write(self.position, self.old_inputs)
        cursor.select(self.old_selection)


class FillInputsCommand(Command):
    def __init__(self, selection, char):
        super().__init__("Fill selection")
        self.selection = selection
        self.char = char
        self.old_inputs = None

    def redo(self, inputs, cursor):
        if self.old_inputs is None:
            self.old_inputs = inputs.read(self.selection)
        inputs.fill(self.selection, self.char)
        cursor.select(self.selection)

    def undo(self, inputs, cursor):
        inputs.write(self.selection[:2], self.old_inputs)
        cursor.select(self.selection)


class ClearInputsCommand(Command):
    def __init__(self, selection):
        super().__init__("Clear selection")
        self.selection = selection
        self.old_inputs = None

    def redo(self, inputs, cursor):
        if self.old_inputs is None:
            self.old_inputs = inputs.read(self.selection)
        inputs.clear(self.selection)
        cursor.select(self.selection)

    def undo(self, inputs, cursor):
        inputs.write(self.selection[:2], self.old_inputs)
        cursor.select(self.selection)


class InsertFramesCommand(Command):
    def __init__(self, start, count):
        super().__init__(f"Insert {count} frame(s)")
        self.start = start
        self.count = count
        self.old_selection_start = None

    def redo(self, inputs, cursor):
        if self.old_selection_start is None:
            self.old_selection_start = cursor.selection_start

        inputs.insert_frames(self.start, self.count)
        cursor.set(*self.old_selection_start)

    def undo(self, inputs, cursor):
        inputs.delete_frames(self.start, self.count)
        cursor.set(*self.old_selection_start)


class DeleteFramesCommand(Command):
    def __init__(self, start, count):
        super().__init__(f"Delete {count} frame(s)")
        self.start = start
        self.count = count
        self.old_inputs = None
        self.old_selection_start = None

    def redo(self, inputs, cursor):
        if self.old_inputs is None or self.old_selection_start is None:
            assert self.old_inputs is None and self.old_selection_start is None
            self.old_inputs = inputs.read(
                (0, self.start, INTENT_COUNT - 1, self.start + self.count - 1)
            )
            self.old_selection_start = cursor.selection_start

        inputs.delete_frames(self.start, self.count)
        cursor.set(*self.old_selection_start)

    def undo(self, inputs, cursor):
        inputs.insert_frames(self.start, self.count)
        inputs.write((0, self.start), self.old_inputs)
        cursor.select((0, self.start, INTENT_COUNT - 1, self.start + self.count - 1))
