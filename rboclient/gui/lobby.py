from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.gui.game import Step

from kivy.app import App
from kivy.event import EventDispatcher
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, StringProperty, BooleanProperty

from math import inf


class ScrollableStack(ScrollView):
    background = ListProperty([0, 0, 0])
    content = ObjectProperty()

    def __init__(self, bg: "list[int]" = background.defaultvalue, **kwargs):
        super().__init__(background=bg, **kwargs)


class LogMessage(Label):
    background = ListProperty([0, 0, 0])

    def __init__(self, msg: str, bg: "list[int]", **kwargs):
        super().__init__(text=msg, background=bg, **kwargs)


class Logs(ScrollableStack):
    backgroundEven = [.1, .1, .1]
    backgroundOdd = [.05, .05, .05]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    def log(self, msg: str) -> None:
        self.content.add_widget(LogMessage(msg, Logs.backgroundEven if self.count % 2 == 0 else Logs.backgroundOdd))
        self.count += 1


class Member(BoxLayout):
    id = NumericProperty()
    name = StringProperty()
    master = BooleanProperty(False)
    ready = BooleanProperty(False)

    def __init__(self, id: int, name: str, **kwargs):
        super().__init__(id=id, name=name, **kwargs)

    def toggleReady(self) -> None:
        pass

    def toggleMaster(self) -> None:
        pass


class Members(ScrollableStack):
    master = NumericProperty()

    def __init__(self, member: Member, **kwargs):
        super().__init__(**kwargs)
        self.members = {member.id: member}
        self.master = member.id
        self.add_widget(member, member.id)

    def refreshMaster(self) -> None:
        master = +inf
        for id in self.members.keys():
            if id < master:
                master = id

        self.members[self.master].master = False
        self.master = master
        self.members[self.master].master = True

    def registered(self, id: int, name: str) -> None:
        if id in self.members.keys():
            raise ValueError("Multiple members with same ID")

        self.members[id] = Member(id, name)
        self.add_widget(self.members[id], id)
        self.refreshMaster()

    def unregistered(self, id: int) -> None:
        if id not in self.members.keys():
            raise ValueError("Unknown member ID")

        self.remove_widget(self.members[id])
        self.members.pop(id)
        self.refreshMaster()


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
        self.logs.log("Member [{id}] request : [b]ready[/b].".format(**args))

    def ready(self, _: EventDispatcher):
        self.rboCI.ready()

    def disconnect(self, _: EventDispatcher):
        self.rboCI.disconnect()
