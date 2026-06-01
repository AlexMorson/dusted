from __future__ import annotations

from dataclasses import dataclass

from dustmaker.replay import Character

from dusted.broadcaster import Broadcaster
from dusted.dustforce.event import Event, LevelStartEvent, State, StateId, StepEvent
from dusted.models.inputs import Intents


@dataclass(frozen=True, slots=True)
class Node:
    parent: Node | None
    frame: int
    state: State
    next_states: dict[Intents, Node]

    def after(self, intents: Intents) -> Node | None:
        return self.next_states.get(intents)

    def common_ancestor(self, other: Node) -> Node | None:
        left = self
        right = other

        while left.frame > right.frame:
            assert left.parent is not None
            left = left.parent

        while right.frame > left.frame:
            assert right.parent is not None
            right = right.parent

        while True:
            if left == right:
                return left

            if left.parent is None or right.parent is None:
                return None

            left = left.parent
            right = right.parent


class GameStates(Broadcaster):
    def __init__(self) -> None:
        super().__init__()

        self._level: str | None = None
        self._character: Character | None = None

        self._states: dict[StateId, Node] = {}
        self._current: Node | None = None

    @property
    def level(self) -> str | None:
        return self._level

    @property
    def current(self) -> Node | None:
        return self._current

    def on_event(self, event: Event) -> None:
        if isinstance(event, LevelStartEvent):
            self._on_level_start(event)
        elif isinstance(event, StepEvent):
            self._on_step(event)

    def _on_level_start(self, event: LevelStartEvent) -> None:
        if event.level == self._level and event.character == self._character:
            return

        new_node = Node(
            parent=None,
            frame=0,
            state=event.state,
            next_states={},
        )
        self._level = event.level
        self._states = {event.id: new_node}
        self._current = new_node

        self.broadcast()

    def _on_step(self, event: StepEvent) -> None:
        if prev_node := self._states.get(event.prev_id):
            if node := prev_node.after(event.intents):
                self._current = node
            else:
                node = Node(
                    parent=prev_node,
                    frame=prev_node.frame + 1,
                    state=event.state,
                    next_states={},
                )
                prev_node.next_states[event.intents] = node
                self._states[event.id] = node
                self._current = node
        else:
            self._current = None

        self.broadcast()
