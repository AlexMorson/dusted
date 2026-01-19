import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Collection

from dusted.broadcaster import Broadcaster
from dusted.inputs import Inputs, Intents


class GridIntent(ABC):
    @staticmethod
    @abstractmethod
    def set_value(intents: Intents, value: str) -> Intents: ...

    @staticmethod
    @abstractmethod
    def get_value(intents: Intents) -> str: ...


class XGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "012":
            return intents
        return dataclasses.replace(intents, x=int(value) - 1)

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.x + 1)


class YGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "012":
            return intents
        return dataclasses.replace(intents, y=int(value) - 1)

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.y + 1)


class JumpGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "012":
            return intents
        return dataclasses.replace(intents, jump=int(value))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.jump)


class DashGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "01":
            return intents
        return dataclasses.replace(intents, dash=int(value))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.dash)


class FallGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "01":
            return intents
        return dataclasses.replace(intents, fall=int(value))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.fall)


class LightGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "0123456789ab":
            return intents
        return dataclasses.replace(intents, light=int(value, 16))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return hex(intents.light)[2:]


class HeavyGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "0123456789ab":
            return intents
        return dataclasses.replace(intents, heavy=int(value, 16))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return hex(intents.heavy)[2:]


class TauntGridIntent(GridIntent):
    @staticmethod
    def set_value(intents: Intents, value: str) -> Intents:
        if value not in "012":
            return intents
        return dataclasses.replace(intents, taunt=int(value))

    @staticmethod
    def get_value(intents: Intents) -> str:
        return str(intents.taunt)


GRID_INTENTS: list[GridIntent] = [
    XGridIntent(),
    YGridIntent(),
    JumpGridIntent(),
    DashGridIntent(),
    FallGridIntent(),
    LightGridIntent(),
    HeavyGridIntent(),
    TauntGridIntent(),
]


class InputsGrid(Broadcaster):
    """Wrapper that represents inputs as a grid of characters."""

    def __init__(self, inputs: Inputs) -> None:
        super().__init__()

        self._inputs = inputs
        self._inputs.subscribe(self.broadcast)

    def __len__(self) -> int:
        """Return the number of frames that the inputs cover."""
        return len(self._inputs)

    def _get_cell(self, row: int, col: int) -> str:
        assert 0 <= row < len(GRID_INTENTS) and 0 <= col < len(self._inputs)
        return GRID_INTENTS[row].get_value(self._inputs[col])

    def _set_cell(self, row: int, col: int, value: str) -> None:
        assert 0 <= row < len(GRID_INTENTS) and 0 <= col < len(self._inputs)
        self._inputs[col] = GRID_INTENTS[row].set_value(self._inputs[col], value)

    def set(self, inputs: Collection[Collection[str]]) -> None:
        """Load a (not necessarily rectangular) grid of inputs."""
        with self._inputs.batch():
            self._inputs[:] = [
                Intents.default() for _ in range(max(len(row) for row in inputs))
            ]
            for intent, row in zip(GRID_INTENTS, inputs):
                for frame, value in enumerate(row):
                    self._inputs[frame] = intent.set_value(self._inputs[frame], value)

    def write(self, position: tuple[int, int], block: list[list[str]]) -> None:
        """Paste a block of inputs into the grid, only writing valid intents."""
        top, left = position
        assert (
            top >= 0
            and left >= 0
            and top + len(block) <= len(GRID_INTENTS)
            and left + len(block[0]) <= len(self._inputs)
        )
        with self._inputs.batch():
            for row, line in enumerate(block, start=top):
                for col, char in enumerate(line, start=left):
                    self._set_cell(row, col, char)

    def fill(self, selection: tuple[int, int, int, int], char: str) -> None:
        """Fill a block of the grid with the same input."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom <= len(GRID_INTENTS) and 0 <= left <= right
        with self._inputs.batch():
            for row in range(top, bottom + 1):
                for col in range(left, min(right + 1, len(self._inputs))):
                    self._set_cell(row, col, char)

    def clear(self, selection: tuple[int, int, int, int]) -> None:
        """Reset a block of the grid to the default inputs."""
        top, left, bottom, right = selection
        assert 0 <= top <= bottom < len(GRID_INTENTS) and 0 <= left <= right
        with self._inputs.batch():
            for row in range(top, bottom + 1):
                char = GRID_INTENTS[row].get_value(Intents.default())
                for col in range(left, min(right + 1, len(self._inputs))):
                    self._set_cell(row, col, char)

    def get(self) -> list[list[str]]:
        """Return all inputs."""
        return [
            [intent.get_value(intents) for intents in self._inputs]
            for intent in GRID_INTENTS
        ]

    def read(self, selection: tuple[int, int, int, int]) -> list[list[str]]:
        """Return a block of the grid."""
        top, left, bottom, right = selection
        assert 0 <= top and bottom < len(GRID_INTENTS) and 0 <= left <= right
        return [
            [self._get_cell(row, col) for col in range(left, right + 1)]
            for row in range(top, bottom + 1)
        ]

    def at(self, row: int, col: int) -> str:
        """Return a single cell of the grid."""
        return self._get_cell(row, col)

    def delete_frames(self, start: int, count: int) -> None:
        """Delete some frames."""
        assert 0 <= start and count >= 0
        del self._inputs[start : start + count]

    def insert_frames(self, start: int, count: int) -> None:
        """Insert default-initialised frames."""
        assert 0 <= start <= len(self._inputs) and count >= 0
        self._inputs[start:start] = [Intents.default() for _ in range(count)]
