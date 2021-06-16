from unittest import TestCase, mock

from dusted.cursor import Cursor
from dusted.inputs import Inputs


class TestCursor(TestCase):
    def setUp(self):
        inputs = Inputs()
        self.cursor = Cursor(inputs)

        self.callback = mock.Mock()
        self.cursor.subscribe(self.callback)

    def test_initial_position(self):
        self.assertEqual(self.cursor.selection, (0, 0, 0, 0))

    def test_position(self):
        # Set cursor position
        self.cursor.set(2, 2)
        self.callback.assert_called()
        self.callback.reset_mock()
        self.assertEqual(self.cursor.selection, (2, 2, 2, 2))
        self.assertEqual(self.cursor.position, (2, 2))

        # Set position and keep selection
        self.cursor.set(3, 3, True)
        self.callback.assert_called()
        self.callback.reset_mock()
        self.assertEqual(self.cursor.selection, (2, 2, 3, 3))
        self.assertEqual(self.cursor.position, (3, 3))

        # Move cursor
        self.cursor.move(-1, 1)
        self.callback.assert_called()
        self.callback.reset_mock()
        self.assertEqual(self.cursor.selection, (2, 4, 2, 4))
        self.assertEqual(self.cursor.position, (2, 4))

        # Move and keep selection
        self.cursor.move(1, -1, True)
        self.callback.assert_called()
        self.callback.reset_mock()
        self.assertEqual(self.cursor.selection, (2, 3, 3, 4))
        self.assertEqual(self.cursor.position, (3, 3))

    def test_reverse_selection(self):
        self.cursor.select((3, 3, 2, 2))
        self.callback.assert_called()
        self.assertEqual(self.cursor.selection, (2, 2, 3, 3))

    def test_clamp_position(self):
        # Top
        self.cursor.set(-10, 2)
        self.assertEqual(self.cursor.selection, (0, 2, 0, 2))

        # Bottom
        self.cursor.set(10, 2)
        self.assertEqual(self.cursor.selection, (6, 2, 6, 2))

        # Left
        self.cursor.set(2, -10)
        self.assertEqual(self.cursor.selection, (2, 0, 2, 0))

        # Right
        self.cursor.set(2, 100)
        self.assertEqual(self.cursor.selection, (2, 55, 2, 55))

    def test_selection_dimensions(self):
        self.cursor.select((2, 2, 5, 6))
        self.assertEqual(self.cursor.selection_height, 4)
        self.assertEqual(self.cursor.selection_width, 5)

    def test_selection_start_end(self):
        self.cursor.select((2, 2, 3, 3))
        self.assertEqual(self.cursor.selection_start, (2, 2))
        self.assertEqual(self.cursor.selection_end, (3, 3))

    def test_is_selected(self):
        self.cursor.select((2, 2, 3, 3))

        self.assertTrue(self.cursor.is_selected(2, 2))
        self.assertTrue(self.cursor.is_selected(2, 3))
        self.assertTrue(self.cursor.is_selected(3, 2))
        self.assertTrue(self.cursor.is_selected(3, 3))

        self.assertFalse(self.cursor.is_selected(1, 2))
        self.assertFalse(self.cursor.is_selected(1, 3))
        self.assertFalse(self.cursor.is_selected(4, 2))
        self.assertFalse(self.cursor.is_selected(2, 1))
        self.assertFalse(self.cursor.is_selected(3, 1))
        self.assertFalse(self.cursor.is_selected(2, 4))
        self.assertFalse(self.cursor.is_selected(3, 4))

    def test_has_selection(self):
        self.assertFalse(self.cursor.has_selection)
        self.cursor.set(1, 1, True)
        self.assertTrue(self.cursor.has_selection)
        self.cursor.set(2, 2)
        self.assertFalse(self.cursor.has_selection)
