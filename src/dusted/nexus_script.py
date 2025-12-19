from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass
class NexusScript:
    frames: list[KeyStates]

    def serialize(self) -> str:
        return "\n".join(frame.serialize() for frame in self.frames)


@dataclass
class KeyStates:
    left: DirectionState
    right: DirectionState
    up: DirectionState
    down: DirectionState
    jump: ButtonState
    dash: ButtonState
    light: ButtonState
    heavy: ButtonState
    escape: ButtonState
    taunt: ButtonState

    def serialize(self) -> str:
        return (
            self.left.serialize()
            + self.right.serialize()
            + self.up.serialize()
            + self.down.serialize()
            + self.jump.serialize()
            + self.dash.serialize()
            + self.light.serialize()
            + self.heavy.serialize()
            + self.escape.serialize()
            + self.taunt.serialize()
        )


class DirectionState(Enum):
    RELEASED = 0
    HELD = 1
    DOUBLE_TAPPED = 2

    def serialize(self) -> str:
        return str(self.value)


class ButtonState(Enum):
    RELEASED = 0
    HELD = 1

    def serialize(self) -> str:
        return str(self.value)
