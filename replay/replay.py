class Replay:
    """Data for a replay containing one player."""
    def __init__(self, username, levelname, character, inputs):
        self.username = username
        self.levelname = levelname
        self.character = character
        self.inputs = inputs
