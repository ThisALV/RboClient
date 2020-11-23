import rboclient
from rboclient.gui.home import Home, HomeCtxActions
from rboclient.gui.game import Game
from rboclient.gui.lobby import LobbyCtxActions
from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.network import handlerstree

import kivy
import kivy.input
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.logger import Logger
from kivy.lang.builder import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty

from twisted.internet import protocol, endpoints, reactor
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

kivy.require("2.0.0")

Window.size = (900, 650)


class ErrorMessage(AnchorLayout):
    text = StringProperty()


class ErrorPopup(Popup):
    "Popup d'affichant une erreur dans le thème de l'application avec un message d'erreur."

    def __init__(self, title: str, msg: str):
        super().__init__(title=title, content=ErrorMessage(text=msg))

    def on_touch_down(self, _):
        self.dismiss()
        return True


class WindowButton(Label):
    "Classe mère pour la création d'un bouton dans la barre de titre, c'est un label simulant le fonctionnement d'un bouton en émettant on_press."

    def __init__(self, **kwargs):
        self.register_event_type("on_press")
        super().__init__(**kwargs)

    def on_touch_down(self, touch: MotionEvent):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.dispatch("on_press")
        return True

    def on_press(self):
        pass


class SizeButton(WindowButton):
    "Bouton de la barre de titre agrandissant ou restaurant la fenêtre. Le texte contenu change en conséquence."

    maximized = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        class Setter:
            def __init__(self, btn: SizeButton, value: bool):
                self.btn = btn
                self.value = value

            def __call__(self, _: EventDispatcher) -> None:
                self.btn.maximized = self.value

        Window.bind(on_restore=Setter(self, False), on_maximize=Setter(self, True))

    def on_maximized(self, _: EventDispatcher, maximized: bool):
        if maximized:
            Window.maximize()
        else:
            Window.restore()


class TitleBar(BoxLayout):
    "Barre de titre sur-mesure adaptant ses actions contextuels au contexte (accueil, lobby ou session)."

    contexts = {
        "home": HomeCtxActions,
        "lobby": LobbyCtxActions,
        "session": FloatLayout
    }

    title = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.actionsCtx = None
        self.switch("home")

    def switch(self, context: str) -> None:
        if self.actionsCtx is not None:
            self.remove_widget(self.actionsCtx)

        self.actionsCtx = TitleBar.contexts[context]()
        self.add_widget(self.actionsCtx, 2)


class Main(BoxLayout):
    """Conteneur principal (racine) de l'application.

    Possède une TitleBar personnalisé et un contenu.\n
    Les deux s'adaptent au contexte et changent pour proposer différentes actions.
    """

    titleBar = ObjectProperty()
    handlers = {
        Mode.REGISTERING: handlerstree.registering,
        Mode.LOBBY: handlerstree.lobby,
        Mode.SESSION: handlerstree.session
    }

    def __init__(self, **kwargs):
        self.register_event_type("on_move")
        super().__init__(**kwargs)

        self.content = None
        Clock.schedule_once(self.home)

    def on_touch_down(self, touch: MotionEvent):
        if super().on_touch_down(touch):
            return True

        touch.grab(self)

        self.moving = True
        self.initPos = touch.pos
        self.lastDiff = [0] * 2

        return True

    def on_move(self, **direction):
        pass

    def on_touch_move(self, touch: MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        for i in range(2):
            self.lastDiff[i] = touch.pos[i] - (self.initPos[i] - self.lastDiff[i])

        self.initPos = touch.pos
        moveWindow(*self.lastDiff)

        return True

    def on_touch_up(self, touch: MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        self.moving = False
        self.initPos = None
        self.lastDiff = None

        touch.ungrab(self)
        return True

    def home(self, _: EventDispatcher = None, error: Failure = None) -> None:
        if error is None or type(error.value) == ConnectionDone:
            Logger.info("Main : Back to Home.")
        else:
            Logger.error("Main : Back to Home : " + error.getErrorMessage())
            ErrorPopup(type(error.value).__name__, error.getErrorMessage()).open()

        self.titleBar.switch("home")
        self.titleBar.title = "Rbo - Connexion"

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
        self.titleBar.switch("lobby")
        self.titleBar.title = "Rbo - Lobby"

        game = Game(self.connection, members)
        game.bind(on_close=self.home)
        self.connection = None

        self.remove_widget(self.content)
        self.content = game
        self.add_widget(self.content)


def moveWindow(x, y):
    Window.left += x
    Window.top -= y


class ClientApp(App):
    "Application du client."

    titleBar = ObjectProperty()

    def __init__(self, cfg: ConfigParser, **kwargs):
        super().__init__(**kwargs)
        self.rbocfg = cfg

    def build(self):
        for kv in ["home", "lobby", "config"]:
            Builder.load_file(kv + ".kv")

        return Builder.load_file("app.kv")

    def on_start(self):
        super().on_start()

        self.titleBar = self.root.titleBar
