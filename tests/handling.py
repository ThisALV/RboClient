import unittest

from rboclient.network import handling


class Merge(unittest.TestCase):
    def test_UnsupportedFormat(self):
        with self.assertRaises(handling.UnsupportedMerge):
            handling.merge(b"\x00\x00\x00")

    def test_Byte(self):
        self.assertEqual(handling.merge(b"\x0f"), 15)

    def test_Long(self):
        self.assertEqual(handling.merge(b"\xff" * 8), 2 ** 64 - 1)


class DataTake(unittest.TestCase):
    def test_Empty(self):
        with self.assertRaises(handling.EmptyBuffer):
            handling.Data(b"").take()

    def test_NotEmpty(self):
        self.assertEqual(handling.Data(b"\x01\x02\x03").take(), 1)


class DataTakeNumeric(unittest.TestCase):
    def setUp(self):
        self.data = handling.Data(b"\x01\x02\x03")

    def test_TooSmall(self):
        with self.assertRaises(handling.EmptyBuffer):
            self.data.takeNumeric(4)

    def test_Larger(self):
        self.assertEqual(self.data.takeNumeric(2), 258)


class DataTakeString(unittest.TestCase):
    def test_TooSmall(self):
        with self.assertRaises(handling.EmptyBuffer):
            handling.Data(b"\x01").takeString()

    def test_EmptyString(self):
        self.assertEqual(handling.Data(b"\x00\x00").takeString(), "")

    def test_NotEmptyString(self):
        self.assertEqual(handling.Data(b"\x00\x0cHello world!").takeString(), "Hello world!")


if __name__ == "__main__":
    unittest.main()
