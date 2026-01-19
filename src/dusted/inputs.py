from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import overload

from dusted.broadcaster import Broadcaster


class Inputs(Broadcaster):
    def __init__(self, inputs: list[Intents] | None = None) -> None:
        super().__init__()
        self._frames = inputs if inputs is not None else []

    def __len__(self) -> int:
        return len(self._frames)

    def __iter__(self) -> Iterator[Intents]:
        return iter(self._frames)

    @overload
    def __getitem__(self, index: int) -> Intents: ...
    @overload
    def __getitem__(self, index: slice) -> list[Intents]: ...
    def __getitem__(self, index: int | slice) -> Intents | list[Intents]:
        return self._frames[index]

    @overload
    def __setitem__(self, index: int, value: Intents) -> None: ...
    @overload
    def __setitem__(self, index: slice, value: Iterable[Intents]) -> None: ...
    def __setitem__(
        self, index: int | slice, value: Intents | Iterable[Intents]
    ) -> None:
        if isinstance(index, int):
            assert isinstance(value, Intents)
            self._frames[index] = value
        else:
            assert isinstance(value, Iterable)
            self._frames[index] = value
        self.broadcast()

    @overload
    def __delitem__(self, index: int) -> None: ...
    @overload
    def __delitem__(self, index: slice) -> None: ...
    def __delitem__(self, index: int | slice) -> None:
        del self._frames[index]
        self.broadcast()


@dataclass(frozen=True, slots=True)
class Intents:
    x: int
    y: int
    jump: int
    dash: int
    fall: int
    light: int
    heavy: int
    taunt: int

    @classmethod
    def default(cls) -> Intents:
        return cls(0, 0, 0, 0, 0, 0, 0, 0)
