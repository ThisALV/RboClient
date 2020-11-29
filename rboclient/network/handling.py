from __future__ import annotations  # Pour le type hint de Data.__eq__

import struct

supportedMerges = {
    1: "B",
    2: "H",
    4: "I",
    8: "Q"
}


class UnsupportedMerge(ValueError):
    def __init__(self, size: int):
        super().__init__("Merge isn't supported for " + str(size) + " bytes")


class EmptyBuffer(BufferError):
    def __init__(self, size: int):
        super().__init__("Buffer data length is less than " + str(size))


class UnknownBranch(KeyError):
    def __init__(self, id: int):
        super().__init__("Unknown branch " + str(id))


class InvalidFormat(EOFError):
    def __init__(self, reason: str):
        super().__init__("Invalid format for protocol : " + reason)


def merge(data: bytes, signed: bool = False) -> int:
    "Regroupe des octets dans un ordre gros-boutiste pour former un seul entier non-signé."

    try:
        format = supportedMerges[len(data)]
    except KeyError:
        raise UnsupportedMerge(len(data))

    if signed:
        format = format.lower()

    return struct.unpack("!" + format, data)[0]


def decompose(packet: bytes) -> list:
    "Décompose un paquets de données en plusieurs trames à l'aide du protocole de Rbo."

    frames = []

    while len(packet) >= 2:
        size = merge(packet[:2])
        if len(packet) < size:
            raise InvalidFormat("Data is missing")

        frames.append(Data(packet[2:size]))

        packet = packet[size:]

    if len(packet) != 0:
        raise InvalidFormat("Too many data")

    return frames


class Data(object):
    """Encapsule un buffer de données.

    Les données peuvent être relevées octet par octet, ou par chaîne de caractères ou encore par entiers de différentes tailles d'octets.\n
    Les données doivent respecter le protocole Rbo.
    """

    def __init__(self, buffer: bytes):
        self.buffer = buffer

    def __eq__(self, rhs: Data) -> bool:
        return self.buffer == rhs.buffer

    def take(self) -> int:
        if len(self.buffer) == 0:
            raise EmptyBuffer(1)

        byte, self.buffer = self.buffer[0], self.buffer[1:]
        return byte

    def takeBool(self) -> bool:
        return self.take() != 0

    def takeNumeric(self, size: int, signed: bool = False) -> int:
        if len(self.buffer) < size:
            raise EmptyBuffer(size)

        numeric, self.buffer = merge(self.buffer[:size], signed), self.buffer[size:]
        return numeric

    def takeString(self) -> str:
        size = self.takeNumeric(2)  # Vérification qu'il reste au moins 2 octets lors de la lecture te la taille
        raw, self.buffer = self.buffer[:size], self.buffer[size:]

        return raw.decode()


class HandlerNode(object):
    "Nœud dans l'arbre de résolution d'un paquet."

    def __init__(self, children: dict, tag: str = ""):
        self.children = children
        self.tag = tag

    def __call__(self, data: Data, tags: "list[str]" = None):
        if tags is None:
            tags = []

        id = data.take()

        nextTags = tags
        if self.tag != "":
            nextTags += [self.tag]

        if id not in self.children:
            raise UnknownBranch(id)

        return self.children[id](data, tags)
