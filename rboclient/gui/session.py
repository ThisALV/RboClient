from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import GameCtxActions, ScrollableStack
from rboclient.network.protocol import RboConnectionInterface as RboCI


class SessionCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans la session, à savoir se déconnecter pour revenir à l'accueil."

    actions = ["disconnect"]


class Players(ScrollableStack):
    pass


class Session(Step, BoxLayout):
    name = StringProperty()

    def __init__(self, gameName: str, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init("Session on " + gameName, rboCI, app.TitleBarCtx.SESSION)

        self.name = gameName
        self.members = members

        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())
