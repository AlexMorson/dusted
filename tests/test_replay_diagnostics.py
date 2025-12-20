from unittest import TestCase

from dusted.inputs import Inputs
from dusted.replay_diagnostics import ReplayDiagnostics


class TestReplayDiagnostics(TestCase):
    def setUp(self) -> None:
        self.inputs = Inputs()
        self.diagnostics = ReplayDiagnostics(self.inputs)

    def test_error_fall_without_down(self):
        """Test that a fall intent without down being held errors."""

        self.inputs.set(
            """\
1
1
0
0
1
0
0
0""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 0)})

    def test_error_fall_then_dash(self):
        """Test that a fall into a non-DTD dash errors."""

        # No down double tap.
        self.inputs.set(
            """\
1111
2221
0000
0001
0010
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(3, 3)})

        # Down double tap interrupted by an up tap.
        self.inputs.set(
            """\
1111
2021
0000
0001
0010
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(3, 3)})

        # Down double tap interrupted by a left tap.
        self.inputs.set(
            """\
1101
2121
0000
0001
0010
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(3, 3)})

    def test_valid_fall_then_dash(self):
        """Test that a fall into a DTD dash is valid."""

        self.inputs.set(
            """\
1111
2121
0000
0001
0010
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

    def test_error_dash_then_fall(self):
        """Test that a dash into a non-DTD fall errors."""

        # No right double tap.
        self.inputs.set(
            """\
2221
1112
0000
0010
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 3)})

        # Right double tap interrupted by a left tap.
        self.inputs.set(
            """\
2021
1112
0000
0010
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 3)})

        # Right double tap interrupted by an up tap.
        self.inputs.set(
            """\
2121
1102
0000
0010
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 3)})

    def test_valid_dash_then_fall(self):
        """Test that a dash into a DTD fall is valid."""

        self.inputs.set(
            """\
2121
1112
0000
0010
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

    def test_warn_double_tap_no_dash(self):
        """Test that a DTD dash input without a dash intent warns."""

        # To the left.
        self.inputs.set(
            """\
010
111
000
000
000
000
000
000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, {(3, 2)})
        self.assertEqual(self.diagnostics.errors, set())

        # To the right.
        self.inputs.set(
            """\
212
111
000
000
000
000
000
000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, {(3, 2)})
        self.assertEqual(self.diagnostics.errors, set())

    def test_warn_double_tap_no_fall(self):
        """Test that a DTD fall input without a fall intent warns."""

        self.inputs.set(
            """\
111
212
000
000
000
000
000
000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, {(4, 2)})
        self.assertEqual(self.diagnostics.errors, set())

    def test_double_tap_delay(self):
        """Test that the double tap delay is checked correctly."""

        # Valid double tap.
        self.inputs.set(
            """\
2111111111111121
1111111111111112
0000000000000000
0000000000000010
0000000000000001
0000000000000000
0000000000000000
0000000000000000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

        # First tap held longer, makes no difference.
        self.inputs.set(
            """\
2222222222222121
1111111111111112
0000000000000000
0000000000000010
0000000000000001
0000000000000000
0000000000000000
0000000000000000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

        # Too slow for a double tap.
        self.inputs.set(
            """\
21111111111111121
11111111111111112
00000000000000000
00000000000000010
00000000000000001
00000000000000000
00000000000000000
00000000000000000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 16)})

    def test_valid_fall_then_grounded_downdash(self):
        """Test that a DTD fall into a grounded downdash is valid."""

        self.inputs.set(
            """\
1111
2122
0000
0001
0011
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

    def test_valid_dash_then_grounded_downdash(self):
        """Test that a DTD dash into a grounded downdash is valid."""

        self.inputs.set(
            """\
2121
1112
0000
0011
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

    def test_error_triple_tap_dash(self):
        """Test that another tap after a DTD dash isn't a valid dash."""

        self.inputs.set(
            """\
212121
111112
000000
001010
000001
000000
000000
000000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 5)})

    def test_error_triple_tap_fall(self):
        """Test that another tap after a DTD fall isn't a valid fall."""

        self.inputs.set(
            """\
111111
212121
000000
000001
001010
000000
000000
000000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(3, 5)})

    def test_down_dash_without_fall(self):
        """Test that holding down and dashing without a fall intent is invalid."""

        # Non double tapped dash means the dash key is pressed, so there should
        # be a fall intent.
        self.inputs.set(
            """\
1
2
0
1
0
0
0
0""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, {(4, 0)})

        # But a double tapped dash with down held is fine.
        self.inputs.set(
            """\
1212
2222
0000
0001
0000
0000
0000
0000""".splitlines()
        )
        self.assertEqual(self.diagnostics.warnings, set())
        self.assertEqual(self.diagnostics.errors, set())

    def test_valid_attacks(self):
        """Test that valid attack intents do not error."""

        valid_sequences = [
            "a",
            "0a0",
            "00aabb0",
            "0a900a9800a98700a98765432100",
            "0a9aaa98aaa987aaa987654321a0",
            "0a9b0a98b0a987b0a987654321b0",
        ]
        for intents in valid_sequences:
            # Light intents.
            self.inputs.set(["", "", "", "", "", intents, "", ""])
            self.assertEqual(self.diagnostics.warnings, set())
            self.assertEqual(self.diagnostics.errors, set())

            # Heavy intents.
            self.inputs.set(["", "", "", "", "", "", intents, ""])
            self.assertEqual(self.diagnostics.warnings, set())
            self.assertEqual(self.diagnostics.errors, set())

    def test_invalid_attacks(self):
        """Test that invalid attack intents error."""

        invalid_sequences = [
            ("b", 0),
            ("9", 0),
            ("8", 0),
            ("7", 0),
            ("1", 0),
            ("a8", 1),
            ("a7", 1),
            ("a6", 1),
            ("a1", 1),
            ("0b", 1),
            ("09", 1),
            ("08", 1),
            ("07", 1),
            ("01", 1),
            ("aba", 2),
            ("ab9", 2),
            ("ab8", 2),
            ("ab7", 2),
            ("ab1", 2),
            ("a97", 2),
            ("a96", 2),
            ("a989", 3),
            ("a986", 3),
            ("a985", 3),
            ("a9876545", 7),
            ("a9876542", 7),
            ("a9876541", 7),
            ("a98765434", 8),
            ("a98765431", 8),
            ("a987654323", 9),
        ]
        for intents, frame in invalid_sequences:
            # Light intents.
            self.inputs.set(["", "", "", "", "", intents, "", ""])
            self.assertEqual(self.diagnostics.warnings, set())
            self.assertEqual(self.diagnostics.errors, {(5, frame)})

            # Heavy intents.
            self.inputs.set(["", "", "", "", "", "", intents, ""])
            self.assertEqual(self.diagnostics.warnings, set())
            self.assertEqual(self.diagnostics.errors, {(6, frame)})

    def test_nexus_script(self):
        """Test that nexus scripts are generated correctly."""

        # Double tapped ledge cancel.
        self.inputs.set(
            """\
22222
12121
00000
00001
00010
00000
00000
00000""".splitlines()
        )
        self.assertEqual(
            self.diagnostics.nexus_script.serialize(),
            """\
0100000000
0101000000
0100000000
0102000000
0100010000""",
        )

        # Double tapped dash with a simultaneous downdash.
        self.inputs.set(
            """\
1212
2222
0000
0001
0001
0000
0000
0000""".splitlines()
        )
        self.assertEqual(
            self.diagnostics.nexus_script.serialize(),
            """\
0001000000
0101000000
0001000000
0201010000""",
        )

        # Double tapped dash into grounded downdash.
        self.inputs.set(
            """\
12121
22222
00000
00011
00001
00000
00000
00000""".splitlines()
        )
        self.assertEqual(
            self.diagnostics.nexus_script.serialize(),
            """\
0001000000
0101000000
0001000000
0201000000
0001010000""",
        )

        # Sanity check other intents.
        self.inputs.set(
            """\
0211111111111111
1102111211111111
0000122000000000
0000010000000000
0000000100000000
00000000aa98abb0
000000000aa98abb
0000000000122000""".splitlines()
        )
        self.assertEqual(
            self.diagnostics.nexus_script.serialize(),
            """\
1000000000
0100000000
0010000000
0001000000
0000100000
0000110000
0000100000
0001010000
0000001000
0000001100
0000000101
0000000001
0000001001
0000001100
0000001100
0000000100""",
        )
