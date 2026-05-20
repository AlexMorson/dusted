from typing import Generic, TypeVar

from dusted.broadcaster import Broadcaster

T = TypeVar("T")


class Value(Broadcaster, Generic[T]):
    def __init__(self, value: T) -> None:
        super().__init__()
        self._value = value

    def set(self, value: T) -> None:
        if value != self._value:
            self._value = value
            self.broadcast()

    def get(self) -> T:
        return self._value
