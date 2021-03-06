from enum import Enum, auto

import kivy.input
import rboclient
from kivy.app import App
from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.core.window import Keyboard, Window
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.lang.builder import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from rboclient.gui.game import Game
from rboclient.gui.home import Home, HomeCtxActions
from rboclient.gui.lobby import LobbyCtxActions
from rboclient.gui.session import SessionCtxActions
from rboclient.gui.widgets import ErrorPopup
from rboclient.misc import toBool
from rboclient.network import handlerstree
from rboclient.network.protocol import Mode
from rboclient.network.protocol import RboConnectionInterface as RboCI
from twisted.internet import endpoints, reactor
from twisted.internet.error import ConnectionDone
from twisted.python.failure import Failure

kivy.require("2.0.0")


def setTitle(title: str) -> None:
    App.get_running_app().titleBar.title = "Rbo - " + title


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


class InvalidWindowState(ValueError):
    """Levée si la fenêtre n'est pas dans un état "plein écran" ou non."""

    def __init__(self, state):
        super().__init__("This window state isn't valid :", state)


class FullscreenButton(WindowButton):
    "Bouton de la barre de titre agrandissant ou restaurant la fenêtre. Le texte contenu change en conséquence."

    enabled = BooleanProperty();

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Window.bind(fullscreen=self.updateState)
        self.updateState(None, Window.fullscreen)

    @staticmethod
    def checkWindowState(fullscreen) -> None:
        if fullscreen == True or fullscreen == "fake":  # noqa E712, Window.fullscreen n'est pas obligatoirement un booléen
            raise InvalidWindowState(fullscreen)

    def on_press(self):
        self.checkWindowState(Window.fullscreen)
        toggleFullscreen()

    def updateState(self, _: EventDispatcher, fullscreen):
        self.checkWindowState(fullscreen)
        self.enabled = fullscreen == "auto"


class TitleBarCtx(Enum):
    HOME = auto(),
    LOBBY = auto(),
    SESSION = auto()


class TitleBar(BoxLayout):
    "Barre de titre sur-mesure adaptant ses actions contextuelles au contexte (accueil, lobby ou session)."

    contexts = {
        TitleBarCtx.HOME: HomeCtxActions,
        TitleBarCtx.LOBBY: LobbyCtxActions,
        TitleBarCtx.SESSION: SessionCtxActions
    }

    title = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.actionsCtx = None
        self.switch(TitleBarCtx.HOME)

    def switch(self, context: TitleBarCtx) -> None:
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

        self.titleBar.switch(TitleBarCtx.HOME)
        setTitle("Connexion")

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

    def login(self, _: EventDispatcher, host: "tuple[str, int]", player: "tuple[int, str]") -> None:
        server = endpoints.TCP4ClientEndpoint(reactor, *host)
        self.connection = RboCI(*player, Main.handlers)

        connecting = server.connect(self.connection)
        connecting.addCallbacks(self.registering, self.ioError)

    def registering(self, _: rboclient.network.protocol.RboConnection) -> None:
        class RegistrationError:
            def __init__(self, reason: str):
                self.reason = reason

            def __call__(self, _: EventDispatcher) -> None:
                Logger.error("Main : Registration failed")
                ErrorPopup("Inscription échouée", self.reason).open()

        self.connection.bind(on_registered=self.game,
                             on_invalid_request=RegistrationError("Requête d'inscription invalide."),
                             on_unavailable_id=RegistrationError("L'identifiant {} n'est pas disponible.".format(self.connection.id)),
                             on_unavailable_name=RegistrationError("Le nom \"{}\" n'est pas disponible".format(self.connection.name)),
                             on_unavailable_session=RegistrationError("La session est déjà en préparation."),
                             on_reserved_id=RegistrationError("L'identifiant \"{}\" est réservé pour un usage spécifique par le serveur.".format(self.connection.id)))

    def game(self, _: EventDispatcher, members: "dict[int, tuple[str, bool]]") -> None:
        game = Game(self.connection, members)
        game.bind(on_close=self.home)
        self.connection = None

        self.remove_widget(self.content)
        self.content = game
        self.add_widget(self.content)


def moveWindow(x, y):
    Window.left += x
    Window.top -= y


def toggleFullscreen():
    Window.fullscreen = "auto" if Window.fullscreen == False else False  # noqa E712, Window.fullscreen n'est pas obligatoirement un booléen


class TaskAlreadyRunning(Exception):
    def __init__(self, taskName: str):
        super().__init__(taskName + " is already running in ClientApp")


class TaskNotFound(KeyError):
    def __init__(self, taskName: str):
        super().__init__(taskName + " doesn't exist")


class ClientApp(App):
    "Application du client."

    titleBar = ObjectProperty()

    def __init__(self, cfg: ConfigParser, defaultSize: "tuple[int, int]", **kwargs):
        super().__init__(**kwargs)
        self.rbocfg = cfg

        try:
            Window.size = tuple([int(self.rbocfg.get("graphics", option)) for option in ["width", "height"]])
        except ValueError:
            Window.size = defaultSize
            Logger.warn("ClientApp : Invalid window size values, default size applied.")

        if toBool(self.rbocfg.get("graphics", "fullscreen")):
            Clock.schedule_once(lambda _: toggleFullscreen())

        Window.bind(on_key_down=self.keyboardPressed)

        self.runningTasks = []

    def keyboardPressed(self, _: EventDispatcher, key: str, *__) -> bool:
        if Keyboard.keycodes["f11"] == key:
            toggleFullscreen()
        elif Keyboard.keycodes["f1"] == key:
            return True

        return False

    def build(self):
        for kv in ["home", "lobby", "session", "config", "cfgsections", "widgets"]:
            Builder.load_file(kv + ".kv")

        return Builder.load_file("app.kv")

    def on_start(self):
        super().on_start()

        self.titleBar = self.root.titleBar

    def runTask(self, name: str) -> None:
        if name in self.runningTasks:
            raise TaskAlreadyRunning(name)

        self.runningTasks.append(name)

    def isRunning(self, name: str) -> bool:
        return name in self.runningTasks

    def stopTask(self, name: str) -> None:
        if name not in self.runningTasks:
            raise TaskNotFound(name)

        self.runningTasks.remove(name)
