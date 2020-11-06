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
        Logger.info("Connection: Connexion établie avec " + str(self.transport.getPeer()))

        self.mode = Mode.REGISTERING
        self.interface.dispatch("on_connected")

        self.transport.write(self.interface.id.to_bytes(1, "big") + self.interface.name.encode())

    def connectionLost(self, reason: twisted.python.failure.Failure):
        Logger.info("Connection: Déconnexion : " + reason.getErrorMessage())

        self.interface.dispatch("on_disconnected", reason)

    def dataReceived(self, data: bytes):
        for frame in handling.decompose(data):
            event = self.interface.handlers[self.mode](frame)
            self.interface.dispatch("on_" + event.name, **event.args)

    def send(self, data: bytes):
        self.transport.write(data)


def listLeaves(tree: dict) -> list:
    "Liste les feuilles d'un arbre de HanlderNodes."

    leaves = []

    for branch in tree.values():
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


class HandlerLeaf(object):
    "Feuille de l'arbre pouvant être appelée pour retourner les données à utiliser lors du dispatch de l'event."

    @staticmethod
    def nothing(_: handling.Data) -> dict:
        return {}

    def __init__(self, name: str, handler=nothing):
        self.name = name
        self.handler = handler

    def __call__(self, data: handling.Data, tags: list) -> Event:
        return Event("_".join(tags + [self.name]), self.handler(data))


class RboConnectionInterface(protocol.Factory, EventDispatcher):
    "Interface permettant d'interagir avec l'activité réseau et d'utiliser la connexion établie."

    def __init__(self, id: int, name: str, handlers: dict[Mode, handling.HandlerNode]):
        for event in listLeaves(handlers):
            realName = "on_" + event.name

            self.add_custom_event(realName)

            def defaultHandler(self, **_):
                RboConnectionInterface.trace(realName)

            setattr(self, realName, defaultHandler)

        for event in ["connected", "disconnected"]:
            self.add_custom_event("on_" + event)

        super().__init__()

        self.id = id
        self.name = name
        self.handlers = handlers

    @staticmethod
    def debug(msg: str) -> None:
        Logger.debug("ConnectionInterface : " + msg)

    def buildProtocol(self, host: twisted.internet.address.IAddress):
        RboConnectionInterface.debug("Construction du protocole pour une connexion avec " + str(host))

        self.connection = RboConnection(self)
        return self.connection

    def switchMode(self, mode: Mode) -> None:
        self.connection.mode = mode

    def on_connected(self):
        RboConnectionInterface.debug("Connecté")

    def on_disconnected(self, reason: twisted.python.failure.Failure):
        RboConnectionInterface.debug("Déconnecté : " + reason.getErrorMessage())

    def register(self, id: int, name: str) -> None:
        self.connection.send(id.to_bytes(1, "big", signed=False) + name.encode())

    def reply(self, reply: int) -> None:
        self.connection.send(reply.to_bytes(1, "big", signed=False))
