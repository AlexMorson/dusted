from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from dusted.broadcaster import Broadcaster
from dusted.cursor import Cursor
from dusted.inputs import Inputs, Intents


@dataclass(frozen=True, slots=True)
class Action:
    """
    An action that can be undone and redone.

    :param name: The name of the action
    :param before: The state of the world before the action was performed
    :param after: The state of the world after the action was performed
    """

    name: str
    before: Snapshot
    after: Snapshot


@dataclass(frozen=True, slots=True)
class Snapshot:
    """A snapshot of the application state."""

    inputs: tuple[Intents, ...]
    cursor: tuple[int, int, int, int]


class UndoStack(Broadcaster):
    def __init__(self, inputs: Inputs, cursor: Cursor) -> None:
        super().__init__()

        self._inputs = inputs
        self._cursor = cursor

        self._stack: list[Action] = []
        self._index = 0
        self._unmodified_index = -1

    def clear(self) -> None:
        self._stack = []
        self._index = 0
        self._unmodified_index = -1

        self.broadcast()

    def _snapshot(self) -> Snapshot:
        return Snapshot(
            inputs=tuple(intents for intents in self._inputs),
            cursor=self._cursor.selection,
        )

    @contextmanager
    def execute(self, name: str) -> Generator[None, None, None]:
        before = self._snapshot()
        yield
        after = self._snapshot()

        del self._stack[self._index :]
        if self._unmodified_index > self._index:
            self._unmodified_index = -1

        self._stack.append(
            Action(
                name=name,
                before=before,
                after=after,
            )
        )
        self._index += 1

        self.broadcast()

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._stack)

    @property
    def is_modified(self) -> bool:
        return self._index != self._unmodified_index

    def set_unmodified(self) -> None:
        self._unmodified_index = self._index
        self.broadcast()

    def undo_text(self) -> str:
        if not self.can_undo:
            return ""
        return self._stack[self._index - 1].name

    def redo_text(self) -> str:
        if not self.can_redo:
            return ""
        return self._stack[self._index].name

    def undo(self) -> None:
        if not self.can_undo:
            return

        self._index -= 1

        snapshot = self._stack[self._index].before
        self._inputs[:] = snapshot.inputs
        self._cursor.select(snapshot.cursor)

        self.broadcast()

    def redo(self) -> None:
        if not self.can_redo:
            return

        snapshot = self._stack[self._index].after
        self._inputs[:] = snapshot.inputs
        self._cursor.select(snapshot.cursor)

        self._index += 1

        self.broadcast()
