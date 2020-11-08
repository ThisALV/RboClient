import rboclient
from rboclient.gui.home import Home
from rboclient.gui.game import Game, IGError
from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.network import handlerstree

import kivy
import kivy.input
from kivy.app import App
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.logger import Logger
from kivy.lang.builder import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty

from twisted.internet import protocol, endpoints, reactor
from twisted.python.failure import Failure

kivy.require("2.0.0")

Window.size = (900, 650)


class HomeCtxActions(AnchorLayout):
    button = ObjectProperty()


class LobbyCtxActions(BoxLayout):
    actions = ["disconnect", "ready"]

    def __init__(self, **kwargs):
        for event in LobbyCtxActions.actions:
            self.register_event_type("on_" + event)

        super().__init__(**kwargs)

        self.grabbing = None

    def on_touch_down(self, touch: MotionEvent):
        for action in LobbyCtxActions.actions:
            button = self.ids[action]

            if button.collide_point(*touch.pos):
                button.state = "down"
                touch.grab(self)
                self.grabbing = button

                self.dispatch("on_" + action)

                return True

        return super().on_touch_down(touch)

    def on_touch_up(self, touch: MotionEvent):
        if touch.grab_current is self:
            self.grabbing.state = "normal"
            self.grabbing = None

            touch.ungrab(self)

            return True

        return super().on_touch_up(touch)

    def on_ready(self):
        pass

    def on_disconnect(self):
        pass


class QuitButton(Label):
    def on_touch_down(self, touch: MotionEvent):
        if self.collide_point(*touch.pos):
            App.get_running_app().stop()
            return True

        return super().on_touch_down(touch)


class TitleBar(BoxLayout):
    "Barre de titre sur-mesure."

    contexts = {
        "home": HomeCtxActions,
        "lobby": LobbyCtxActions,
        "session": FloatLayout
    }

    title = StringProperty("Rbo - Connexion")

    def __init__(self, **kwargs):
        self.register_event_type("on_move")
        super().__init__(**kwargs)

        self.moving = False
        self.actionsCtx = None
        self.switch("home")

    def switch(self, context: str) -> None:
        if self.actionsCtx is not None:
            self.remove_widget(self.actionsCtx)

        self.actionsCtx = TitleBar.contexts[context]()
        self.add_widget(self.actionsCtx, 2)

    def on_touch_down(self, touch: MotionEvent):
        if super().on_touch_down(touch) or not self.collide_point(*touch.pos):
            return True

        touch.grab(self)

        self.moving = True
        self.initPos = touch.pos
        self.lastDiff = [0] * 2

        return True

    def on_move(self, **direction):
        Logger.debug("TitleBar : Move -> x:{x} ; x:{y}".format(**direction))

    def on_touch_move(self, touch: MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        Logger.debug("TitleBar : Move = X:{} ; Y:{}".format(*touch.pos))

        for i in range(2):
            self.lastDiff[i] = touch.pos[i] - (self.initPos[i] - self.lastDiff[i])

        self.initPos = touch.pos
        self.dispatch("on_move", x=self.lastDiff[0], y=self.lastDiff[1])

        return True

    def on_touch_up(self, touch: MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        self.moving = False
        self.initPos = None
        self.lastDiff = None

        touch.ungrab(self)
        return True


class Main(BoxLayout):
    "Conteneur principal de l'application."

    titleBar = ObjectProperty()
    handlers = {
        Mode.REGISTERING: handlerstree.registering,
        Mode.LOBBY: handlerstree.lobby,
        Mode.SESSION: handlerstree.session
    }

    def __init__(self, **kwargs):
        self.register_event_type("on_start")
        super().__init__(**kwargs)

        self.content = None

    def on_start(self):
        self.home()

    def home(self, _: EventDispatcher = None, reason: IGError = None) -> None:
        if reason is not None:
            Logger.error("Main : {} - {}".format(reason.short, reason.long))

        home = Home()
        if self.content is not None:
            self.remove_widget(self.content)

        self.content = home
        self.content.bind(on_login=self.login)

        self.add_widget(self.content)

    def ioError(self, reason: Failure) -> None:
        Logger.error("Main : {}".format(reason.getErrorMessage()))
        self.connection = None

    def registrationError(self, _: EventDispatcher) -> None:
        Logger.error("Main : Registration failed")

    def login(self, _: EventDispatcher, host: "tuple[str, int]", player: "tuple[int, str]") -> None:
        server = endpoints.TCP4ClientEndpoint(reactor, *host)
        self.connection = RboCI(*player, Main.handlers)

        connecting = server.connect(self.connection)
        connecting.addErrback(self.ioError)
        connecting.addCallback(self.registering)

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

        self.titleBar.switch("lobby")


class ClientApp(App):
    "Application du client."

    titleBar = ObjectProperty()

    def build(self):
        Window.bind(on_cursor_leave=self.readjustUp, on_cursor_enter=self.stopReadjustment)
        self.readjusting = False

        for kv in ["home", "game"]:
            Builder.load_file(kv + ".kv")

        return Builder.load_file("app.kv")

    def on_start(self):
        super().on_start()
        self.root.dispatch("on_start")

        self.titleBar = self.root.titleBar
        self.titleBar.bind(on_move=self.move)

    def readjustUp(self, _):
        if self.titleBar.moving:
            Logger.debug("ClientApp : Lost window, readjusting...")

            self.readjusting = True
            Clock.schedule_once(self.readjustment, .01)

    def readjustment(self, *_):
        Window.top -= 30

        if self.readjusting:
            Clock.schedule_once(self.readjustment, .01)
        else:
            Logger.debug("ClientApp : Readjusted.")

    def stopReadjustment(self, _):
        self.readjusting = False

    def move(self, _, **direction):
        if direction["y"] > 5:
            direction["y"] *= 2

        Window.left += direction["x"]
        Window.top -= direction["y"]
