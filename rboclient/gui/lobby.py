from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode
from rboclient.gui.game import Step

from kivy.app import App
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, StringProperty, BooleanProperty

from math import inf


class LobbyCtxAction(AnchorLayout):
    button = ObjectProperty()
    text = StringProperty()


class LobbyCtxActions(BoxLayout):
    "Actions contextuelles disponibles dans le lobby, à savoir se signaler (non) prêt et se déconnecter pour revenir à l'accueil."

    actions = ["disconnect", "ready"]

    def __init__(self, **kwargs):
        for event in LobbyCtxActions.actions:
            self.register_event_type("on_" + event)

        super().__init__(**kwargs)

        self.grabbing = None

    def on_touch_down(self, touch: MotionEvent):
        for action in LobbyCtxActions.actions:
            button = self.ids[action].button

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
        Logger.debug("TitleBar : Ready requested.")

    def on_disconnect(self):
        Logger.debug("TitleBar : Logout requested.")


class ScrollableStack(ScrollView):
    "Classe mère pour créer un StackLayout (pile d'éléments) qui soit scrollable verticalement."

    background = ListProperty([0, 0, 0])
    content = ObjectProperty()

    def __init__(self, bg: "list[int]" = background.defaultvalue, **kwargs):
        super().__init__(background=bg, **kwargs)


class LogMessage(Label):
    "Message dans l'historique."

    background = ListProperty([0, 0, 0])

    def __init__(self, msg: str, bg: "list[int]", **kwargs):
        super().__init__(text=msg, background=bg, **kwargs)


class Logs(ScrollableStack):
    "Historique scrollable des actions ayant eu lieu dans le Lobby."

    backgroundEven = [.1, .1, .1]
    backgroundOdd = [.05, .05, .05]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0

    def log(self, msg: str) -> None:
        self.content.add_widget(LogMessage(msg, Logs.backgroundEven if self.count % 2 == 0 else Logs.backgroundOdd))
        self.count += 1


class Member(BoxLayout):
    "Affiche un membre et les informations associées avec."

    id = NumericProperty()
    name = StringProperty()
    master = BooleanProperty(False)
    ready = BooleanProperty(False)
    me = BooleanProperty(False)

    status = {
        False: ("En attente", [1, 0, 0]),
        True: ("Prêt", [0, 1, 0])
    }

    def __init__(self, id: int, name: str, me: bool, **kwargs):
        super().__init__(id=id, name=name, me=me, **kwargs)

    def on_ready(self, _: EventDispatcher, ready: bool):
        pass

    def on_master(self, _: EventDispatcher, master: bool):
        pass


class Members(ScrollableStack):
    """Liste des membres.

    Cette liste scrollable fait l'inventaire de tous les membres présents.\n
    Elle affiche également leur statut : identifiant, pseudo et ce qu'ils sont en train de faire.
    """

    master = NumericProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.members = {}
        self.master = +inf

        Clock.schedule_once(self.initContent)

    def initContent(self, _: int):
        self.content.padding = 5
        self.content.spacing = 5

    def refreshMaster(self) -> None:
        master = +inf
        for id in self.members.keys():
            if id < master:
                master = id

        if self.master in self.members:
            self.members[self.master].master = False

        self.master = master
        self.members[self.master].master = True

    def registered(self, id: int, name: str, me: bool = False) -> None:
        if id in self.members.keys():
            raise ValueError("Multiple members with same ID")

        self.members[id] = Member(id, name, me)
        self.content.add_widget(self.members[id])
        self.refreshMaster()

    def unregistered(self, id: int) -> None:
        if id not in self.members.keys():
            raise ValueError("Unknown member ID")

        self.content.remove_widget(self.members[id])
        self.members.pop(id)
        self.refreshMaster()

    def toggleReady(self, id: int) -> None:
        self.members[id].ready = not self.members[id].ready


class Lobby(Step, BoxLayout):
    """Lobby d'une partie.

    Gère tous les évènements d'un lobby (liste de membres, lancement de session, logs...).
    """

    logs = ObjectProperty()
    members = ObjectProperty()

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", **kwargs):
        super().__init__(**kwargs)
        self.rboCI = rboCI
        self.link(rboCI)

        self.members.registered(self.rboCI.id, self.rboCI.name, me=True)

        for (id, member) in members.items():
            self.members.registered(id, member[0])
            if member[1]:
                self.members.toggleReady()

        self.rboCI.bind(on_member_registered=self.memberRegistered,
                        on_member_ready=self.readyMember,
                        on_member_disconnected=self.memberUnregistered,
                        on_member_crashed=self.memberUnregistered)

        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=self.disconnect, on_ready=self.ready)

        self.rboCI.switchMode(Mode.LOBBY)

    def memberRegistered(self, _: EventDispatcher, **args):
        self.members.registered(**args)

    def memberUnregistered(self, _: EventDispatcher, **args):
        self.members.unregistered(**args)

    def readyMember(self, _: EventDispatcher, **args):
        self.logs.log("Member [{id}] request : [b]ready[/b].".format(**args))
        self.members.toggleReady(args["id"])

    def ready(self, _: EventDispatcher):
        self.rboCI.ready()

    def disconnect(self, _: EventDispatcher):
        self.rboCI.disconnect()
