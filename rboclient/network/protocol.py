from enum import Enum, auto
from rboclient.network import handling

import kivy
import kivy.support
from kivy.logger import Logger, LOG_LEVELS
from kivy.event import EventDispatcher

kivy.support.install_twisted_reactor()

import twisted  # noqa E402
from twisted.internet import protocol  # noqa E402


class Mode(Enum):
    "Status de la partie."

    LOGGING = auto(),
    REGISTERING = auto(),
    LOBBY = auto(),
    SESSION = auto(),
    DISCONNECTED = auto()


class RboConnection(protocol.Protocol):
    "Connexion à un Lobby ou à une Session et protocole de communication pour Rbo."

    def __init__(self, interface: "RboConnectionInterface"):
        super().__init__()

        self.interface = interface
        self.mode = Mode.LOGGING

    def connectionMade(self):
        Logger.debug("Connection : Connection establish with " + str(self.transport.getPeer()))

        self.mode = Mode.REGISTERING
        self.interface.dispatch("on_connected")

        self.transport.write(self.interface.id.to_bytes(1, "big") + self.interface.name.encode())

    def connectionLost(self, reason: twisted.python.failure.Failure):
        Logger.debug("Connection : Disconnecting : " + reason.getErrorMessage())

        self.mode = Mode.DISCONNECTED
        self.interface.dispatch("on_disconnected", reason)

    def dataReceived(self, data: bytes):
        for frame in handling.decompose(data):
            event = self.interface.handlers[self.mode](frame)
            self.interface.dispatch("on_" + event.name, **event.args)

    def send(self, data: bytes) -> None:
        self.transport.write(data)


def listLeaves(tree: handling.HandlerNode) -> list:
    "Liste les feuilles d'un arbre de HanlderNodes."

    leaves = []

    for branch in tree.children.values():
        if type(branch) == handling.HandlerNode:
            leaves += listLeaves(branch)
        else:
            leaves.append(branch)

    return leaves


class Event(object):
    "Évènement à déclencher, avec ses paramètres."

    def __init__(self, name, **args):
        self.name = name
        self.args = args


def ignore(_: handling.Data) -> dict:
    return {}


class HandlerLeaf(object):
    "Feuille de l'arbre pouvant être appelée pour retourner les données à utiliser lors du dispatch de l'event."

    def __init__(self, name: str, handler=ignore):
        self.name = name
        self.handler = handler

    def __call__(self, data: handling.Data, tags: list) -> Event:
        return Event("_".join(tags + [self.name]), **self.handler(data))


class DefaultHandler:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, **args) -> None:
        Logger.debug("RboCI : {} -> {}".format(self.name, args))


class RboConnectionInterface(protocol.Factory, EventDispatcher):
    "Interface permettant d'interagir avec l'activité réseau et d'utiliser la connexion établie."

    def __init__(self, id: int, name: str, handlers: "dict[Mode, handling.HandlerNode]"):
        for tree in handlers.values():
            for event in listLeaves(tree):
                realName = "on_" + event.name

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

    def switchMode(self, mode: Mode) -> None:
        self.connection.mode = mode

    def on_connected(self):
        Logger.info("RboCI : Connected")

    def on_disconnected(self, reason: twisted.python.failure.Failure):
        Logger.info("RboCI : Disconnected : " + reason.getErrorMessage())

    def reply(self, reply: int) -> None:
        self.connection.send(reply.to_bytes(1, "big", signed=False))

    def ready(self) -> None:
        self.connection.send("\x00")

    def disconnect(self) -> None:
        self.connection.send("\x01")
