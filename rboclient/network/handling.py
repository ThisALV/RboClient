import struct

supportedMerges = {
    1: "B",
    2: "H",
    4: "I",
    8: "Q"
}

class UnsupportedMerge(ValueError):
    def __init__(self, bytes: int):
        super().__init__("Merge n'est pas supporté pour " + str(bytes) + " octets")


def merge(data: bytes) -> int:
    "Regroupe des octets dans un ordre gros-boutiste pour former un seul entier non-signé."

    try:
        format = supportedMerges[len(data)]
    except KeyError:
        raise UnsupportedMerge(len(data))

    return struct.unpack("!" + format, data)[0]


class Data(object):
    "Encapsule un buffer contenant les données d'un paquet, pouvant être prélevées une par une."

    def __init__(self, buffer: bytes):
        self.buffer = buffer

    def take(self) -> int:
        byte, self.buffer = self.buffer[0], self.buffer[1:]
        return byte

    def takeNumeric(self, size: int):
        numeric, self.buffer = merge(self.buffer[:size]), self.buffer[size:]
        return numeric

    def takeString(self) -> str:
        pass


class HandleNode(object):
    "Nœud dans l'arbre de résolution d'un paquet."

    def __init__(self, children: dict):
        self.children = children

    def __call__(self, data: Data):
        pass
