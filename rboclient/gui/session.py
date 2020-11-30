from kivy.app import App
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import GameCtxActions
from rboclient.network import protocol
from rboclient.network.protocol import RboConnectionInterface as RboCI


class SessionCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans la session, à savoir se déconnecter pour revenir à l'accueil."

    actions = ["disconnect"]


class Session(Step, AnchorLayout):
    def __init__(self, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init(rboCI, app.TitleBarCtx.SESSION)

        self.members = members

        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())
