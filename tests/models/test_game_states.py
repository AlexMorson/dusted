import dataclasses
from unittest import TestCase

from dustmaker.replay import Character

from dusted.dustforce.event import LevelStartEvent, State, StepEvent
from dusted.models.game_states import GameStates
from dusted.models.inputs import Intents


class TestGameStates(TestCase):
    def test_game_states(self):
        game_states = GameStates()
        right_intents = dataclasses.replace(Intents.default(), x=1)
        down_intents = dataclasses.replace(Intents.default(), y=1)

        game_states.on_event(
            LevelStartEvent(
                id="0-0",
                level="Cyber-Complex-3-10000",
                character=Character.DUSTGIRL,
                state=State(x=0, y=0),
            )
        )
        root = game_states.current

        game_states.on_event(
            StepEvent(
                id="1-0",
                prev_id="0-0",
                intents=right_intents,
                state=State(x=10, y=0),
            )
        )
        right_1 = game_states.current

        game_states.on_event(
            StepEvent(
                id="0-1",
                prev_id="0-0",
                intents=down_intents,
                state=State(x=0, y=10),
            )
        )
        down = game_states.current

        game_states.on_event(
            StepEvent(
                id="2-0",
                prev_id="1-0",
                intents=right_intents,
                state=State(x=20, y=0),
            )
        )
        right_2 = game_states.current

        self.assertEqual(game_states.level, "Cyber-Complex-3-10000")

        self.assertEqual(root.parent, None)
        self.assertEqual(root.frame, 0)
        self.assertEqual(root.state, State(x=0, y=0))
        self.assertEqual(root.after(right_intents), right_1)
        self.assertEqual(root.after(down_intents), down)

        self.assertEqual(right_1.parent, root)
        self.assertEqual(right_1.frame, 1)
        self.assertEqual(right_1.state, State(x=10, y=0))
        self.assertEqual(right_1.after(right_intents), right_2)
        self.assertEqual(right_1.after(down_intents), None)

        self.assertEqual(right_2.parent, right_1)
        self.assertEqual(right_2.frame, 2)
        self.assertEqual(right_2.state, State(x=20, y=0))
        self.assertEqual(right_2.after(right_intents), None)
        self.assertEqual(right_2.after(down_intents), None)

        self.assertEqual(down.parent, root)
        self.assertEqual(down.frame, 1)
        self.assertEqual(down.state, State(x=0, y=10))
        self.assertEqual(down.after(right_intents), None)
        self.assertEqual(down.after(down_intents), None)

        # Test common ancestors
        self.assertEqual(root.common_ancestor(root), root)
        self.assertEqual(root.common_ancestor(right_1), root)
        self.assertEqual(root.common_ancestor(right_2), root)
        self.assertEqual(root.common_ancestor(down), root)

        self.assertEqual(right_1.common_ancestor(root), root)
        self.assertEqual(right_1.common_ancestor(right_1), right_1)
        self.assertEqual(right_1.common_ancestor(right_2), right_1)
        self.assertEqual(right_1.common_ancestor(down), root)

        self.assertEqual(right_2.common_ancestor(root), root)
        self.assertEqual(right_2.common_ancestor(right_1), right_1)
        self.assertEqual(right_2.common_ancestor(right_2), right_2)
        self.assertEqual(right_2.common_ancestor(down), root)

        self.assertEqual(down.common_ancestor(root), root)
        self.assertEqual(down.common_ancestor(right_1), root)
        self.assertEqual(down.common_ancestor(right_2), root)
        self.assertEqual(down.common_ancestor(down), down)
