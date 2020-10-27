import unittest

from rboclient.network import handling


class Merge(unittest.TestCase):
    def test_UnsupportedFormat(self):
        with self.assertRaises(handling.UnsupportedMerge):
            handling.merge(b"\x00\x00\x00")

    def test_UnsignedByte(self):
        self.assertEqual(handling.merge(b"\x0f"), 15)

    def test_UnsignedLong(self):
        self.assertEqual(handling.merge(b"\xff" * 8), 2 ** 64 - 1)

    def test_SignedByte(self):
        self.assertEqual(handling.merge(b"\x80", signed=True), -128)

    def test_SignedShort(self):
        self.assertEqual(handling.merge(b"\xff\xff", signed=True), -1)


class Decompose(unittest.TestCase):
    def test_Empty(self):
        self.assertEqual(handling.decompose(b""), [])

    def test_TooSmallData(self):
        with self.assertRaises(handling.InvalidFormat):
            handling.decompose(b"\x00\x04\x00")

    def test_TooLargeData(self):
        with self.assertRaises(handling.InvalidFormat):
            handling.decompose(b"\x00\x03\xff\x00")

    def test_SuccessfulDecompose(self):
        frames = [
            handling.Data(b"\x01\x02\x03"),
            handling.Data(b"Hello world!"),
            handling.Data(b"")
        ]

        packet = b"\x00\x05\x01\x02\x03\x00\x0eHello world!\x00\x02"

        self.assertEqual(handling.decompose(packet), frames)


class DataTake(unittest.TestCase):
    def test_Empty(self):
        with self.assertRaises(handling.EmptyBuffer):
            handling.Data(b"").take()

    def test_NotEmpty(self):
        self.assertEqual(handling.Data(b"\x01\x02\x03").take(), 1)


class DataTakeBool(unittest.TestCase):
    def test_Zero(self):
        self.assertFalse(handling.Data(b"\x00").takeBool())

    def test_NonZero(self):
        self.assertTrue(handling.Data(b"\x37").takeBool())


class DataTakeNumeric(unittest.TestCase):
    def setUp(self):
        self.data = handling.Data(b"\x01\x02\x03")

    def test_TooSmall(self):
        with self.assertRaises(handling.EmptyBuffer):
            self.data.takeNumeric(4)

    def test_Larger(self):
        self.assertEqual(self.data.takeNumeric(2), 258)

    def test_SignedAndLarger(self):
        self.assertEqual(handling.Data(b"\xff\x00\x00").takeNumeric(1, signed=True), -1)


class DataTakeString(unittest.TestCase):
    def test_TooSmall(self):
        with self.assertRaises(handling.EmptyBuffer):
            handling.Data(b"\x01").takeString()

    def test_EmptyString(self):
        self.assertEqual(handling.Data(b"\x00\x00").takeString(), "")

    def test_NotEmptyString(self):
        self.assertEqual(handling.Data(b"\x00\x0cHello world!").takeString(), "Hello world!")


def makeTreeLevel(depth: int, sequence: list = []) -> handling.HandlerNode:
    children = {}

    for id in range(4):
        if depth == 0:
            children[id] = lambda _, id=id: sequence + [id]
        else:
            children[id] = makeTreeLevel(depth - 1, sequence + [id])

    return handling.HandlerNode(children)


class HandlerNodeCall(unittest.TestCase):
    def setUp(self):
        self.tree = makeTreeLevel(3)

    def test_UnknownBranch(self):
        with self.assertRaises(handling.UnknownBranch):
            self.tree(handling.Data(b"\x01\x05\x00\x01"))

    def test_EmptyBuffer(self):
        with self.assertRaises(handling.EmptyBuffer):
            self.tree(handling.Data(b"\x00" * 3))

    def test_SuccessfulCall(self):
        data = handling.Data(b"\x03\x01\x02\x00")
        self.assertEqual(self.tree(data), [3, 1, 2, 0])


if __name__ == "__main__":
    unittest.main()
