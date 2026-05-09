from dusted.broadcaster import Broadcaster


class Level(Broadcaster):
    def __init__(self, level):
        super().__init__()
        self.level = level

    def set(self, level):
        if level != self.level:
            self.level = level
            self.broadcast()

    def get(self):
        return self.level
