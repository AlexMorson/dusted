from .broadcaster import Broadcaster

INTENT_COUNT = 7

DEFAULT_INPUTS = "1100000"
VALID_INPUTS = [
    "012",
    "012",
    "012",
    "01",
    "01",
    "0123456789ab",
    "0123456789ab"
]


class Inputs(Broadcaster):
    """Stores a rectangular grid of inputs."""

    def __init__(self, inputs=None):
        super().__init__()
        self.length = 0
        self.inputs = []
        if inputs is not None:
            self.set(inputs)
        else:
            self.reset()

    def __len__(self):
        """Return the number of frames that the inputs cover."""
        return self.length

    def reset(self):
        """Reset to default inputs."""
        self.set(list(zip(*[DEFAULT_INPUTS for _ in range(55)])))

    def set(self, inputs):
        """Load a (not necessarily rectangular) grid of inputs."""
        self.length = max(len(line) for line in inputs)
        self.inputs = []
        for line, default in zip(inputs, DEFAULT_INPUTS):
            line_length = len(line)
            # Pad rows to the same length
            self.inputs.append(list(line) + [default] * (self.length - line_length))
        self.broadcast()

    def write(self, position, block):
        """Paste a block of inputs into the grid, validating intents."""
        top, left = position
        assert top >= 0 and left >= 0 and top + len(block) <= INTENT_COUNT and left + len(block[0]) <= self.length
        for row, line in enumerate(block, start=top):
            for col, char in enumerate(line, start=left):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def fill(self, selection, char):
        """Fill a block of the grid with the same input."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right
        for row in range(top, bottom + 1):
            for col in range(left, min(right + 1, self.length)):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def clear(self, selection):
        """Reset a block of the grid to the default inputs."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom < INTENT_COUNT and 0 <= left <= right
        for row in range(top, bottom + 1):
            char = DEFAULT_INPUTS[row]
            for col in range(left, min(right + 1, self.length)):
                self.inputs[row][col] = char
        self.broadcast()

    def get(self):
        """Return all inputs."""
        return self.inputs

    def read(self, selection):
        """Return a block of the grid."""
        top, left, bottom, right = selection
        assert 0 <= top and bottom < INTENT_COUNT and 0 <= left <= right
        return [list(self.inputs[row][left:right + 1]) for row in range(top, bottom + 1)]

    def at(self, row, col):
        """Return a single cell of the grid."""
        assert 0 <= row < INTENT_COUNT and 0 <= col < self.length
        return self.inputs[row][col]

    def delete_frames(self, start, count):
        """Delete some frames."""
        assert 0 <= start and count >= 0
        for row in range(0, INTENT_COUNT):
            del self.inputs[row][start:start + count]
        self.length -= count
        self.broadcast()

    def insert_frames(self, start, count):
        """Insert default-initialised frames."""
        assert 0 <= start <= self.length and count >= 0
        for row in range(0, INTENT_COUNT):
            self.inputs[row][start:start] = [DEFAULT_INPUTS[row]] * count
        self.length += count
        self.broadcast()
