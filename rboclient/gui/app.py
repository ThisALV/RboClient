import rboclient
from rboclient.gui.home import Home
from rboclient.gui.game import Game
from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.network import handlerstree

import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.lang.builder import Builder
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.properties import StringProperty

from twisted.internet import protocol, endpoints, reactor
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

from functools import partial

kivy.require("2.0.0")


class ErrorMessage(AnchorLayout):
    text = StringProperty()


class ErrorPopup(Popup):
    "Popup permettant de signaler une erreur n'étant pas critique."

    def __init__(self, title: str, msg: str):
        super().__init__(title=title, content=ErrorMessage(text=msg))

    def on_touch_down(self, _: EventDispatcher):
        self.dismiss()
        return True


class Main(FloatLayout):
    "Conteneur principal de l'application."

    handlers = {
        Mode.REGISTERING: handlerstree.registering,
        Mode.LOBBY: handlerstree.lobby,
        Mode.SESSION: handlerstree.session
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.content = None
        Clock.schedule_once(self.home)

    def home(self, _: EventDispatcher = None, error: Failure = None) -> None:
        if error is None or type(error.value) == ConnectionDone:
            Logger.info("Main : Back to Home.")
        else:
            Logger.error("Main : Back to Home : " + error.getErrorMessage())
            ErrorPopup(type(error.value).__name__, error.getErrorMessage()).open()

        home = Home()
        if self.content is not None:
            self.remove_widget(self.content)

        self.content = home
        self.content.bind(on_login=self.login)

        self.add_widget(self.content)

    def ioError(self, reason: Failure) -> None:
        Logger.error("Main : " + reason.getErrorMessage())
        ErrorPopup(type(reason.value).__name__, reason.getErrorMessage()).open()

        self.connection = None

    def registrationError(self, _: EventDispatcher) -> None:
        Logger.error("Main : Registration failed")
        ErrorPopup("Inscription échouée", "L'inscription à la session a échoué.").open()

    def login(self, _: EventDispatcher, host: "tuple[str, int]", player: "tuple[int, str]") -> None:
        server = endpoints.TCP4ClientEndpoint(reactor, *host)
        self.connection = RboCI(*player, Main.handlers)

        connecting = server.connect(self.connection)
        connecting.addCallbacks(self.registering, self.ioError)

    def registering(self, _: rboclient.network.protocol.RboConnection) -> None:
        self.connection.bind(on_registered=self.game,
                             on_invalid_request=self.registrationError,
                             on_unavailable_id=self.registrationError,
                             on_unavailable_name=self.registrationError,
                             on_unavailable_session=self.registrationError)

    def game(self, _: EventDispatcher, members: "dict[int, tuple[str, bool]]") -> None:
        Logger.debug("Main : Game !")

        game = Game(self.connection, members)
        game.bind(on_close=self.home)
        self.connection = None

        self.remove_widget(self.content)
        self.content = game
        self.add_widget(self.content)


class ClientApp(App):
    "Application du client."

    def build(self):
        for kv in ["home", "lobby", "config"]:
            Builder.load_file(kv + ".kv")

        return Builder.load_file("app.kv")
