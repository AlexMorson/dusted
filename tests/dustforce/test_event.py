from unittest import TestCase

from dustmaker.replay import Character

from dusted.dustforce.event import LevelStartEvent, State, StepEvent, parse_event
from dusted.models.inputs import Intents


class TestEvent(TestCase):
    def test_level_start_event(self):
        self.assertEqual(
            parse_event(
                '[dusted] level_start 14695981039346656037 "Main Nexus DX" 0 C1900000 3F800000'
            ),
            LevelStartEvent(
                id="14695981039346656037",
                level="Main Nexus DX",
                character=Character.DUSTMAN,
                state=State(
                    x=-18.0,
                    y=1.0,
                ),
            ),
        )

    def test_step_event(self):
        self.assertEqual(
            parse_event(
                "[dusted] step 5184254573656646306 7448687232743006425 1 -1 2 0 0 0 11 0 43A3531D C38C9182"
            ),
            StepEvent(
                id="5184254573656646306",
                prev_id="7448687232743006425",
                intents=Intents(
                    x=1,
                    y=-1,
                    jump=2,
                    dash=0,
                    fall=0,
                    light=0,
                    heavy=11,
                    taunt=0,
                ),
                state=State(
                    x=326.6493225097656,
                    y=-281.13677978515625,
                ),
            ),
        )

    def test_invalid(self):
        for invalid_event in [
            "",
            "Hi there!",
            "[dusted] explode_please",
            "[dusted] level_start The one with the bears",
            '[dusted] level_start 0 "Um, let me just say-',
            "[dusted] step 0 0 1 2 3 4 5 6 7 8 00000000 00000000",
            "[dusted] step 0 0 0 0 0 0 0 0 0 0 WHATISUP DEADBEEF",
        ]:
            self.assertEqual(parse_event(invalid_event), None)
