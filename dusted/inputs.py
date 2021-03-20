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

    def fill_block(self, top, left, bottom, right, char):
        """Fill a block of the grid with a single character, appending columns if needed."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right
        # Extend the grid if needed
        if right > self.length:
            self.insert_cols(self.length, right - self.length)
        # Fill in the block
        for row in range(max(0, top), min(INTENT_COUNT, bottom)):
            if char in VALID_INPUTS[row]:
                for col in range(left, right):
                    self.inputs[row][col] = char
        self.broadcast()

    def set_block(self, top, left, block):
        """Paste a block of inputs into the grid, appending columns if needed."""
        assert 0 <= top and 0 <= left and top + len(block) <= INTENT_COUNT
        # Extend the grid if needed
        block_right = left + max(len(row) for row in block)
        if block_right > self.length:
            self.insert_cols(self.length, block_right - self.length)
        # Copy over the new block
        for row, line in enumerate(block, start=top):
            for col, char in enumerate(line, start=left):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def delete_cols(self, left, right):
        """Delete some columns of the grid."""
        assert 0 <= left <= right <= self.length
        for row in range(0, INTENT_COUNT):
            del self.inputs[row][left:right]
        self.length -= right - left
        self.broadcast()

    def insert_cols(self, col, n):
        """Insert default-initialised columns into the grid."""
        assert 0 <= col <= self.length
        for row in range(0, INTENT_COUNT):
            self.inputs[row][col:col] = [DEFAULT_INPUTS[row]] * n
        self.length += n
        self.broadcast()

    def clear_block(self, top, left, bottom, right):
        """Reset a block of the grid to the default inputs."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right <= self.length
        for row in range(top, bottom):
            char = DEFAULT_INPUTS[row]
            for col in range(left, right):
                self.inputs[row][col] = char
        self.broadcast()

    def get(self):
        """Return all inputs."""
        return self.inputs

    def get_block(self, top, left, bottom, right):
        """Return a block of the grid."""
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right <= self.length
        return [list(self.inputs[row][left:right]) for row in range(top, bottom)]

    def at(self, row, col):
        """Return a single cell of the grid."""
        assert 0 <= row < INTENT_COUNT and 0 <= col < self.length
        return self.inputs[row][col]
