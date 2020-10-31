import kivy
import kivy.input
from kivy.app import App
from kivy.lang.builder import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty

kivy.require("2.0.0")


class HomeCtxActions(AnchorLayout):
    button = ObjectProperty()


class LobbyCtxActions(AnchorLayout):
    button = ObjectProperty()


class QuitButton(Label):
    def on_touch_down(self, touch: kivy.input.MotionEvent):
        if super().collide_point(*touch.pos):
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
        super().__init__(**kwargs)

        self.actionsCtx = None
        self.switch("home")

    def switch(self, context: str) -> None:
        if self.actionsCtx is not None:
            self.remove_widget(self.actionsCtx)

        self.actionsCtx = TitleBar.contexts[context]()
        self.add_widget(self.actionsCtx)


class Home(FloatLayout):
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
        return Builder.load_file("app.kv")

    def on_start(self):
        super().on_start()
        self.root.dispatch("on_start")
