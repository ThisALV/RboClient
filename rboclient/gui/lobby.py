from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.gui.game import Step

from kivy.app import App
from kivy.event import EventDispatcher
from kivy.uix.floatlayout import FloatLayout


class Lobby(Step, FloatLayout):
    "Écran du lobby d'une session."

    def __init__(self, rboCI: RboCI, **kwargs):
        super().__init__(**kwargs)
        self.rboCI = rboCI
        self.link(rboCI)

        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=self.disconnect, on_ready=self.ready)

        self.rboCI.switchMode(Mode.LOBBY)

    def ready(self, _: EventDispatcher):
        self.rboCI.ready()

    def disconnect(self, _: EventDispatcher):
        self.rboCI.disconnect()
