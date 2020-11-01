import kivy
import kivy.input
from kivy.app import App
from kivy.core.window import Window
from kivy.logger import Logger
from kivy.lang.builder import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.metrics import mm, cm
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty

kivy.require("2.0.0")


Window.minimum_width = cm(30)
Window.minimum_height = cm(10)


class HomeCtxActions(AnchorLayout):
    button = ObjectProperty()


class LobbyCtxActions(AnchorLayout):
    button = ObjectProperty()


class QuitButton(Label):
    def on_touch_down(self, touch: kivy.input.MotionEvent):
        if self.collide_point(*touch.pos):
            App.get_running_app().stop()
            return True

        return super().on_touch_down(touch)


class TitleBar(BoxLayout):
    contexts = {
        "home": HomeCtxActions,
        "lobby": LobbyCtxActions,
        "session": FloatLayout
    }

    title = StringProperty("Rbo - Connexion")

    def __init__(self, **kwargs):
        self.register_event_type("on_move")
        super().__init__(**kwargs)

        self.actionsCtx = None
        self.switch("home")

    def switch(self, context: str) -> None:
        if self.actionsCtx is not None:
            self.remove_widget(self.actionsCtx)

        self.actionsCtx = TitleBar.contexts[context]()
        self.add_widget(self.actionsCtx)

    def on_touch_down(self, touch: kivy.input.MotionEvent):
        if super().on_touch_down(touch):
            return True

        touch.grab(self)
        self.initPos = touch.pos
        self.lastDiff = [0] * 2

        return True

    def on_move(self, **direction):
        Logger.debug("TitleBar : Move -> x:{x} ; x:{y}".format(**direction))

    def on_touch_move(self, touch: kivy.input.MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        Logger.debug("TitleBar : Move = X:{} ; Y:{}".format(*touch.pos))

        for i in range(2):
            self.lastDiff[i] = touch.pos[i] - (self.initPos[i] - self.lastDiff[i])

        self.initPos = touch.pos
        self.dispatch("on_move", x=self.lastDiff[0], y=self.lastDiff[1])

        return True

    def on_touch_up(self, touch: kivy.input.MotionEvent):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)

        self.initPos = None
        self.lastDiff = None

        touch.ungrab(self)
        return True


class Home(AnchorLayout):
    pass


class Game(BoxLayout):
    pass


class Main(BoxLayout):
    titleBar = ObjectProperty()
    inGame = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.register_event_type("on_start")
        super().__init__(**kwargs)

    def on_start(self):
        self.content = Home()
        self.add_widget(self.content)

    def on_inGame(self, inGame: bool):
        self.remove_widget(self.content)
        self.content = Game() if inGame else Home()
        self.add_widget(self.content)


class ClientApp(App):
    def build(self):
        for kv in ["home"]:
            Builder.load_file(kv + ".kv")

        return Builder.load_file("app.kv")

    def on_start(self):
        super().on_start()
        self.root.dispatch("on_start")

        self.root.titleBar.bind(on_move=self.move)

    def move(self, _, **direction):
        if direction["y"] > mm(2):
            direction["y"] *= 2

        Window.left += direction["x"]
        Window.top -= direction["y"]
