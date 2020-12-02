from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import GameCtxActions, ScrollableStack
from rboclient.network.protocol import RboConnectionInterface as RboCI

INTRODUCTION = 0


class SessionCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans la session, à savoir se déconnecter pour revenir à l'accueil."

    actions = ["disconnect"]


class BookMsg(Label):
    def __init__(self, msg: str, **kwargs):
        super().__init__(text=msg, **kwargs)


class BookSection(Label):
    def __init__(self, msg: str, **kwargs):
        super().__init__(text=msg, **kwargs)


class Book(ScrollableStack):
    def print(self, _: EventDispatcher, text: str):
        self.content.add_widget(BookMsg(text))

    def sceneSwitch(self, _: EventDispatcher, scene: int):
        self.newSection("Introduction" if scene == INTRODUCTION else "Scène {}".format(scene))

    def newSection(self, text: str) -> None:
        self.content.add_widget(BookSection(text))


class Players(ScrollableStack):
    pass


class Session(Step, BoxLayout):
    name = StringProperty()
    book = ObjectProperty()

    def __init__(self, gameName: str, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init("Session on " + gameName, rboCI, app.TitleBarCtx.SESSION)

        self.name = gameName
        self.members = members

        self.listen(on_text=self.book.print,
                    on_scene_switch=self.book.sceneSwitch)

        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())
