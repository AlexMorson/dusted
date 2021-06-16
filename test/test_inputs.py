from unittest import TestCase, mock

from dusted.inputs import Inputs


class TestInputs(TestCase):
    def setUp(self):
        self.default = Inputs()
        self.custom = Inputs(["".join(str((row + col) % 2) for col in range(100)) for row in range(7)])

        self.callback = mock.Mock()
        self.default.subscribe(self.callback)
        self.custom.subscribe(self.callback)

    def test_length(self):
        self.assertEqual(len(self.default), 55)
        self.assertEqual(len(self.custom), 100)

    def test_get(self):
        self.assertEqual(self.default.get(), [list(c * 55) for c in "1100000"])

    def test_reset(self):
        self.custom.reset()
        self.callback.assert_called()
        self.assertEqual(self.custom.get(), [list(c * 55) for c in "1100000"])

    def test_insert_frames(self):
        self.custom.insert_frames(1, 2)
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0111"))
        self.assertEqual(inputs[1][:4], list("1110"))
        self.assertEqual(inputs[2][:4], list("0001"))
        self.assertEqual(inputs[3][:4], list("1000"))
        self.assertEqual(inputs[4][:4], list("0001"))
        self.assertEqual(inputs[5][:4], list("1000"))
        self.assertEqual(inputs[6][:4], list("0001"))
        self.assertEqual(len(inputs[0]), 102)

    def test_delete_frames(self):
        self.custom.delete_frames(1, 3)
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0010"))
        self.assertEqual(inputs[1][:4], list("1101"))
        self.assertEqual(inputs[2][:4], list("0010"))
        self.assertEqual(inputs[3][:4], list("1101"))
        self.assertEqual(inputs[4][:4], list("0010"))
        self.assertEqual(inputs[5][:4], list("1101"))
        self.assertEqual(inputs[6][:4], list("0010"))
        self.assertEqual(len(inputs[0]), 97)

    def test_write(self):
        self.custom.write((2, 1), [list("01"), list("10")])
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0101"))
        self.assertEqual(inputs[1][:4], list("1010"))
        self.assertEqual(inputs[2][:4], list("0011"))
        self.assertEqual(inputs[3][:4], list("1100"))
        self.assertEqual(inputs[4][:4], list("0101"))
        self.assertEqual(inputs[5][:4], list("1010"))
        self.assertEqual(inputs[6][:4], list("0101"))

    def test_invalid_write(self):
        self.custom.write((0, 1), [["3"], ["a"], ["3"], ["a"], ["z"], ["$"]])
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0101"))
        self.assertEqual(inputs[1][:4], list("1010"))
        self.assertEqual(inputs[2][:4], list("0101"))
        self.assertEqual(inputs[3][:4], list("1010"))
        self.assertEqual(inputs[4][:4], list("0101"))
        self.assertEqual(inputs[5][:4], list("1010"))
        self.assertEqual(inputs[6][:4], list("0101"))

    def test_fill(self):
        self.custom.fill((1, 1, 5, 2), "2")
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0101"))
        self.assertEqual(inputs[1][:4], list("1220"))
        self.assertEqual(inputs[2][:4], list("0221"))
        self.assertEqual(inputs[3][:4], list("1010"))
        self.assertEqual(inputs[4][:4], list("0101"))
        self.assertEqual(inputs[5][:4], list("1220"))
        self.assertEqual(inputs[6][:4], list("0101"))

    def test_clear(self):
        self.custom.clear((1, 1, 5, 2))
        self.callback.assert_called()

        inputs = self.custom.get()
        self.assertEqual(inputs[0][:4], list("0101"))
        self.assertEqual(inputs[1][:4], list("1110"))
        self.assertEqual(inputs[2][:4], list("0001"))
        self.assertEqual(inputs[3][:4], list("1000"))
        self.assertEqual(inputs[4][:4], list("0001"))
        self.assertEqual(inputs[5][:4], list("1000"))
        self.assertEqual(inputs[6][:4], list("0101"))

    def test_read(self):
        self.assertEqual(self.custom.read((1, 1, 3, 3)), [list("010"), list("101"), list("010")])

    def test_at(self):
        self.assertEqual(self.default.at(2, 1), "0")
        self.assertEqual(self.default.at(1, 2), "1")
