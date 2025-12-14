from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager


class Broadcaster:
    def __init__(self) -> None:
        self._callbacks: list[Callable[[], None]] = []

        self._batching = False
        self._broadcast_scheduled = False

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """Batch any events until the context manager has closed."""
        try:
            self._batching = True
            yield
        finally:
            self._batching = False
            if self._broadcast_scheduled:
                self.broadcast()

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def broadcast(self) -> None:
        if self._batching:
            self._broadcast_scheduled = True
        else:
            self._broadcast_scheduled = False
            for callback in self._callbacks:
                callback()
