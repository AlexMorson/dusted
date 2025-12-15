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
