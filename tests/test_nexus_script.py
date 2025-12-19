from unittest import TestCase

from dusted.nexus_script import ButtonState, DirectionState, KeyStates, NexusScript


class TestNexusScript(TestCase):
    def test_serialize(self):
        """Test that nexus scripts are serialized correctly."""

        nexus_script = NexusScript(
            frames=[
                KeyStates(
                    left=DirectionState.HELD,
                    right=DirectionState.DOUBLE_TAPPED,
                    up=DirectionState.RELEASED,
                    down=DirectionState.HELD,
                    jump=ButtonState.HELD,
                    dash=ButtonState.RELEASED,
                    light=ButtonState.HELD,
                    heavy=ButtonState.RELEASED,
                    escape=ButtonState.HELD,
                    taunt=ButtonState.RELEASED,
                ),
                KeyStates(
                    left=DirectionState.RELEASED,
                    right=DirectionState.HELD,
                    up=DirectionState.DOUBLE_TAPPED,
                    down=DirectionState.RELEASED,
                    jump=ButtonState.RELEASED,
                    dash=ButtonState.HELD,
                    light=ButtonState.HELD,
                    heavy=ButtonState.RELEASED,
                    escape=ButtonState.RELEASED,
                    taunt=ButtonState.HELD,
                ),
                KeyStates(
                    left=DirectionState.DOUBLE_TAPPED,
                    right=DirectionState.RELEASED,
                    up=DirectionState.HELD,
                    down=DirectionState.DOUBLE_TAPPED,
                    jump=ButtonState.RELEASED,
                    dash=ButtonState.RELEASED,
                    light=ButtonState.RELEASED,
                    heavy=ButtonState.HELD,
                    escape=ButtonState.HELD,
                    taunt=ButtonState.HELD,
                ),
            ]
        )

        self.assertEqual(
            nexus_script.serialize(),
            """\
1201101010
0120011001
2012000111""",
        )
