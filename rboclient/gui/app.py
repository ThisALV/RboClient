import kivy
from kivy.app import App
from kivy.lang.builder import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import ObjectProperty, StringProperty

kivy.require("2.0.0")


class HomeCtxOptions(AnchorLayout):
    prefsButton = ObjectProperty()


class LobbyCtxOptions(AnchorLayout):
    readyButton = ObjectProperty()


class TitleBar(AnchorLayout):
    title = StringProperty("Rbo - Connexion")
    ctxOptions = ObjectProperty(TitleBar.contexts["home"])

    contexts = {
        "home": HomeCtxOptions(),
        "lobby": LobbyCtxOptions(),
        "session": kivy.uix.floatlayout.FloatLayout()
    }


class Main(BoxLayout):
    titleBar = ObjectProperty()
    content = ObjectProperty()


class ClientApp(App):
    def build(self):
        return Builder.load_file("app.kv")
