from enum import Enum, auto

import kivy
import kivy.support
from kivy.event import EventDispatcher
from kivy.logger import Logger
from rboclient.network import handling

kivy.support.install_twisted_reactor()

import twisted  # noqa E402
from twisted.internet import protocol  # noqa E402
from twisted.python.failure import Failure  # noqa E402


class Mode(Enum):
    "Status de la partie."

    LOGGING = auto(),
    REGISTERING = auto(),
    LOBBY = auto(),
    SESSION = auto(),
    DISCONNECTED = auto()


class RboConnection(protocol.Protocol):
    """Connexion à une partie.

    Cette connexion encapsule un protocole utilisant un arbre pour déterminer quel évènement l'interface doit émettre à chaque trame Rbo reçue.\n
    L'arbre d'évènements utilisé dépend du mode actuel de la partie (logging, registering, lobby, session...).\n
    Ce mode est automatiquement géré par le protocole.\n
    Il est également possible d'envoyer des trames d'octets.
    """

    def __init__(self, interface: "RboConnectionInterface"):
        super().__init__()

        self.interface = interface
        self.mode = Mode.LOGGING

    def connectionMade(self):
        Logger.debug("Connection : Connection establish with " + str(self.transport.getPeer()))

        self.mode = Mode.REGISTERING
        self.interface.dispatch("on_connected")

        self.transport.write(self.interface.id.to_bytes(1, "big") + self.interface.name.encode())

    def connectionLost(self, reason: Failure):
        Logger.debug("Connection : Disconnecting : " + reason.getErrorMessage())

        self.mode = Mode.DISCONNECTED
        self.interface.dispatch("on_disconnected", reason)

    def dataReceived(self, data: bytes):
        for frame in handling.decompose(data):
            event = self.interface.handlers[self.mode](frame)

            if event.name == "registered" or event.name == "session_stop":
                self.mode = Mode.LOBBY
            elif event.name == "session_prepared":
                self.mode = Mode.SESSION

            self.interface.dispatch("on_" + event.name, **event.args)

    def send(self, data: bytes) -> None:
        self.transport.write(data)

    def shutdown(self) -> None:
        self.transport.loseConnection()


def leavesFullNames(tree: handling.HandlerNode, tags: "list[str]" = None) -> "list[str]":
    "Liste les feuilles d'un arbre de HanlderNodes."

    if tags is None:
        tags = []

    leaves = []

    for branch in tree.children.values():
        if type(branch) == handling.HandlerNode:
            leaves += leavesFullNames(branch, tags + [branch.tag])
        else:
            leaves.append("_".join(tags + [branch.name]))

    return leaves


class Event(object):
    "Évènement à déclencher, avec ses paramètres."

    def __init__(self, tag: str, **args):
        self.name = tag
        self.args = args


def ignore(_: handling.Data) -> dict:
    return {}


class IllegalArgName(ValueError):
    def __init__(self, args: dict):
        super().__init__("An argument has inappropriate name \"tag\" : " + str(args))


class HandlerLeaf(object):
    "Feuille de l'arbre pouvant être appelée pour retourner les données à utiliser lors du dispatch de l'event."

    def __init__(self, name: str, handler=ignore):
        self.name = name
        self.handler = handler

    def __call__(self, data: handling.Data, tags: "list[str]") -> Event:
        args = self.handler(data)
        if "tag" in args:
            raise IllegalArgName(args)

        return Event("_".join(tags + [self.name]), **args)


class DefaultHandler:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, **args) -> None:
        Logger.debug("RboCI : {} -> {}".format(self.name, args))


class RboConnectionInterface(protocol.Factory, EventDispatcher):
    """Interface du protocole Rbo.

    Elle se charge d'émettre les évènements déterminés par celui-ci, en plus de créer le protocole.\n
    Elle permet aussi d'effectuer des envois de données sur la connexion.
    """

    def __init__(self, id: int, name: str, handlers: "dict[Mode, handling.HandlerNode]"):
        for tree in handlers.values():
            for eventName in leavesFullNames(tree):
                realName = "on_" + eventName

                setattr(self, realName, DefaultHandler(realName))
                self.register_event_type(realName)

        for event in ["connected", "disconnected"]:
            self.register_event_type("on_" + event)

        super().__init__()

        self.id = id
        self.name = name
        self.handlers = handlers

    def buildProtocol(self, host: twisted.internet.address.IAddress):
        Logger.debug("RboCI : Building protocol for connection to " + str(host))

        self.connection = RboConnection(self)
        return self.connection

    def on_connected(self):
        Logger.info("RboCI : Connected")

    def on_disconnected(self, reason: twisted.python.failure.Failure):
        Logger.info("RboCI : Disconnected : " + reason.getErrorMessage())

    def confirm(self) -> None:
        self.connection.send(b"\x00")

    def reply(self, reply: int) -> None:
        self.connection.send(reply.to_bytes(1, "big", signed=False))

    def replyCheckpoint(self, name: str) -> None:
        self.connection.send(b"\x00" if len(name) == 0 else name.encode())

    def replyYesNo(self, reply: bool) -> None:
        self.connection.send(b"\x00" if reply else b"\x01")

    def ready(self) -> None:
        self.connection.send(b"\x00")

    def disconnect(self) -> None:
        self.connection.send(b"\x01")
        self.close()

    def close(self) -> None:
        self.connection.shutdown()
