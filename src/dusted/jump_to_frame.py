from dusted.dialog import SimpleDialog


class JumpToFrameDialog(SimpleDialog):
    def __init__(self, parent, cursor):
        super().__init__(parent, "Frame:", "Go")
        self.cursor = cursor

    def ok(self, text):
        try:
            frame = int(text)
        except ValueError:
            return False
        self.cursor.set(self.cursor.position[0], frame)
        return True
