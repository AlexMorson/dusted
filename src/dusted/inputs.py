from collections.abc import Collection

from dustmaker.replay import IntentStream

from dusted.broadcaster import Broadcaster

INTENT_COUNT = 8

DEFAULT_INPUTS = "11000000"
VALID_INPUTS = [
    "012",
    "012",
    "012",
    "01",
    "01",
    "0123456789ab",
    "0123456789ab",
    "012",
]
INPUT_TO_TEXT = [
    lambda x: str(x + 1),
    lambda x: str(x + 1),
    lambda x: str(x),
    lambda x: str(x),
    lambda x: str(x),
    lambda x: hex(x)[2:],
    lambda x: hex(x)[2:],
    lambda x: str(x),
]
TEXT_TO_INPUT = [
    lambda x: int(x) - 1,
    lambda x: int(x) - 1,
    lambda x: int(x),
    lambda x: int(x),
    lambda x: int(x),
    lambda x: int(x, 16),
    lambda x: int(x, 16),
    lambda x: int(x),
]


class Inputs(Broadcaster):
    """Stores a rectangular grid of inputs."""

    def __init__(self, inputs: Collection[Collection[str]] | None = None) -> None:
        super().__init__()
        self.length = 0
        self.inputs: list[list[str]] = []
        if inputs is not None:
            self.set(inputs)
        else:
            self.reset()

    def __len__(self) -> int:
        """Return the number of frames that the inputs cover."""
        return self.length

    def set_intents(self, intents: dict[IntentStream, list[int]]) -> None:
        inputs = []
        for intent, input_to_text in enumerate(INPUT_TO_TEXT):
            inputs.append(
                [input_to_text(x) for x in intents.get(IntentStream(intent), [])]
            )
        self.set(inputs)

    def get_intents(self) -> dict[IntentStream, list[int]]:
        intents = {}
        for intent, text_to_input in enumerate(TEXT_TO_INPUT):
            intents[IntentStream(intent)] = [
                text_to_input(c) for c in self.inputs[intent]
            ]
        return intents

    def reset(self) -> None:
        """Reset to default inputs."""
        self.set(list(zip(*[DEFAULT_INPUTS for _ in range(55)])))

    def set(self, inputs: Collection[Collection[str]]) -> None:
        """Load a (not necessarily rectangular) grid of inputs."""
        self.length = max(len(line) for line in inputs)
        self.inputs = []
        for line, default in zip(inputs, DEFAULT_INPUTS):
            # Pad rows to the same length
            self.inputs.append(list(line) + [default] * (self.length - len(line)))
        self.broadcast()

    def write(self, position: tuple[int, int], block: list[list[str]]) -> None:
        """Paste a block of inputs into the grid, validating intents."""
        top, left = position
        assert (
            top >= 0
            and left >= 0
            and top + len(block) <= INTENT_COUNT
            and left + len(block[0]) <= self.length
        )
        for row, line in enumerate(block, start=top):
            for col, char in enumerate(line, start=left):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def fill(self, selection: tuple[int, int, int, int], char: str) -> None:
        """Fill a block of the grid with the same input."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom <= INTENT_COUNT and 0 <= left <= right
        for row in range(top, bottom + 1):
            for col in range(left, min(right + 1, self.length)):
                if char in VALID_INPUTS[row]:
                    self.inputs[row][col] = char
        self.broadcast()

    def clear(self, selection: tuple[int, int, int, int]) -> None:
        """Reset a block of the grid to the default inputs."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom < INTENT_COUNT and 0 <= left <= right
        for row in range(top, bottom + 1):
            char = DEFAULT_INPUTS[row]
            for col in range(left, min(right + 1, self.length)):
                self.inputs[row][col] = char
        self.broadcast()

    def get(self) -> list[list[str]]:
        """Return all inputs."""
        return self.inputs

    def read(self, selection: tuple[int, int, int, int]) -> list[list[str]]:
        """Return a block of the grid."""
        top, left, bottom, right = selection
        assert 0 <= top and bottom < INTENT_COUNT and 0 <= left <= right
        return [
            list(self.inputs[row][left : right + 1]) for row in range(top, bottom + 1)
        ]

    def at(self, row: int, col: int) -> str:
        """Return a single cell of the grid."""
        assert 0 <= row < INTENT_COUNT and 0 <= col < self.length
        return self.inputs[row][col]

    def delete_frames(self, start: int, count: int) -> None:
        """Delete some frames."""
        assert 0 <= start and count >= 0
        for row in range(0, INTENT_COUNT):
            del self.inputs[row][start : start + count]
        self.length -= count
        self.broadcast()

    def insert_frames(self, start: int, count: int) -> None:
        """Insert default-initialised frames."""
        assert 0 <= start <= self.length and count >= 0
        for row in range(0, INTENT_COUNT):
            self.inputs[row][start:start] = [DEFAULT_INPUTS[row]] * count
        self.length += count
        self.broadcast()
