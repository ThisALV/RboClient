from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.gui.game import Step

from kivy.app import App
from kivy.event import EventDispatcher
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.properties import ListProperty, ObjectProperty


class LogMessage(Label):
    background = ListProperty([0, 0, 0])

    def __init__(self, msg: str, bg: "list[int]", **kwargs):
        super().__init__(text=msg, background=bg, **kwargs)


class Logs(ScrollView):
    backgroundEven = [.3, .3, .3]
    backgroundOdd = [.6, .6, .6]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    def log(self, msg: str) -> None:
        self.ids["logs"].add_widget(LogMessage(msg, Logs.backgroundEven if self.count % 2 == 0 else Logs.backgroundOdd))
        self.count += 1


class Lobby(Step, BoxLayout):
    "Écran du lobby d'une session."

    logs = ObjectProperty()

    def __init__(self, rboCI: RboCI, **kwargs):
        super().__init__(**kwargs)
        self.rboCI = rboCI
        self.link(rboCI)

        self.rboCI.bind(on_member_ready=self.readyMember)

        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=self.disconnect, on_ready=self.ready)

        self.rboCI.switchMode(Mode.LOBBY)

    def readyMember(self, _: EventDispatcher, **args):
        self.logs.log("Member [{id}] request : ready.".format(**args))

    def ready(self, _: EventDispatcher):
        self.rboCI.ready()

    def disconnect(self, _: EventDispatcher):
        self.rboCI.disconnect()
