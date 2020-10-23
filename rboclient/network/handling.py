from __future__ import annotations  # L'appelle à un HandleNode retourne un autre HandleNode

import struct

supportedMerges = {
    1: "B",
    2: "H",
    4: "I",
    8: "Q"
}


class UnsupportedMerge(ValueError):
    def __init__(self, size: int):
        super().__init__("Merge n'est pas supporté pour " + str(size) + " octets")


class EmptyBuffer(BufferError):
    def __init__(self, size: int):
        super().__init__("Il reste moins de " + str(size) + " octets dans le buffer")


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
        if len(self.buffer) == 0:
            raise EmptyBuffer(1)

        byte, self.buffer = self.buffer[0], self.buffer[1:]
        return byte

    def takeNumeric(self, size: int) -> int:
        if len(self.buffer) < size:
            raise EmptyBuffer(size)

        numeric, self.buffer = merge(self.buffer[:size]), self.buffer[size:]
        return numeric

    def takeString(self) -> str:
        size = self.takeNumeric(2)  # Vérification qu'il reste au moins 2 octets lors de la lecture te la taille
        raw, self.buffer = self.buffer[:size], self.buffer[size:]

        return raw.decode()


class HandleNode(object):
    "Nœud dans l'arbre de résolution d'un paquet."

    def __init__(self, children: dict):
        self.children = children

    def __call__(self, data: Data) -> HandleNode:
        return self.children[data.take()](data)
