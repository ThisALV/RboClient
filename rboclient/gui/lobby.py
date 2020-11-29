from enum import Enum, auto
from math import inf

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import ScrollableStack, TextInputPopup, YesNoPopup
from rboclient.network import protocol
from rboclient.network.protocol import RboConnectionInterface as RboCI


class LobbyCtxAction(AnchorLayout):
    button = ObjectProperty()
    text = StringProperty()
    enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.register_event_type("on_release")
        super().__init__(**kwargs)

        Clock.schedule_once(self.initReleasedHandler)

    def initReleasedHandler(self, _: int):
        self.button.bind(on_release=lambda _: self.dispatch("on_release"))

    def on_release(self):
        pass


class LobbyCtxActions(BoxLayout):
    "Actions contextuelles disponibles dans le lobby, à savoir se signaler (non) prêt et se déconnecter pour revenir à l'accueil."

    actions = ["disconnect", "ready"]

    open = BooleanProperty(True)

    def __init__(self, **kwargs):
        for event in LobbyCtxActions.actions:  # Les enregistrements des types d'events doivent se faire avant l'appel au constructeur...
            self.register_event_type("on_" + event)

        super().__init__(**kwargs)

        class ReleasedHandlerInitializer:
            def __init__(self, ctxActions: LobbyCtxActions, action: str):
                self.ctx = ctxActions
                self.action = action

            def __call__(self, _: int):
                self.ctx.ids[self.action].bind(on_release=lambda _: self.ctx.dispatch("on_" + self.action))

        for action in LobbyCtxActions.actions:  # ...par conséquent, il y a une deuxième boucle après cet appel.
            Clock.schedule_once(ReleasedHandlerInitializer(self, action))

    def on_ready(self):
        Logger.debug("TitleBar : Ready requested.")

    def on_disconnect(self):
        Logger.debug("TitleBar : Logout requested.")


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


class MemberStatus(Enum):
    WAITING = auto(),
    READY = auto(),
    PARTICIPANT = auto(),
    CHECKPT = auto(),
    CHECKING_PARTICIPANTS = auto()


class Member(BoxLayout):
    "Affiche un membre et les informations associées avec."

    id = NumericProperty()
    name = StringProperty()
    master = BooleanProperty(False)
    status = ObjectProperty(MemberStatus.WAITING)
    me = BooleanProperty(False)

    states = {
        MemberStatus.WAITING: ("En attente", [1, 0, 0]),
        MemberStatus.READY: ("Prêt", [0, 1, 0]),
        MemberStatus.PARTICIPANT: ("Participant", [1, .6, 0]),
        MemberStatus.CHECKPT: ("Choisit le checkpoint...", [1, 1, 0]),
        MemberStatus.CHECKING_PARTICIPANTS: ("Vérifie les joueurs...", [1, 1, 0])
    }

    def __init__(self, id: int, name: str, me: bool, **kwargs):
        super().__init__(id=id, name=name, me=me, **kwargs)


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
        member = self.members[id]
        member.status = MemberStatus.WAITING if member.status == MemberStatus.READY else MemberStatus.READY

    def selectingCheckpoint(self) -> None:
        self.members[self.master].status = MemberStatus.CHECKPT

    def checkingPlayers(self) -> None:
        self.members[self.master].status = MemberStatus.CHECKING_PARTICIPANTS

    def prepareSession(self) -> None:
        for member in self.members.values():
            member.status = MemberStatus.PARTICIPANT

    def name(self, id: int) -> str:
        return self.members[id].name

    def ready(self, id: int) -> bool:
        return self.members[id].status == MemberStatus.READY


class Lobby(Step, BoxLayout):
    """Lobby d'une partie.

    Gère tous les évènements d'un lobby (liste de membres, lancement de session, logs...).
    """

    logs = ObjectProperty()
    members = ObjectProperty()

    open = BooleanProperty(True)

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", selfIncluded: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.init(rboCI, app.TitleBarCtx.LOBBY)

        # Si le joueur ne vient pas de s'inscrire, alors il sera déjà parmis les membres du serveur
        if not selfIncluded:
            self.members.registered(self.rboCI.id, self.rboCI.name, me=True)

        for (id, member) in members.items():
            self.members.registered(id, member[0])
            if member[1]:
                self.members.toggleReady()

        self.listen(on_member_registered=self.memberRegistered,
                    on_member_ready=self.readyMember,
                    on_member_disconnected=self.memberUnregistered,
                    on_member_crashed=self.memberUnregistered,
                    on_preparing_session=self.preparingSession,
                    on_cancel_preparing=self.cancelPreparing,
                    on_prepare_session=self.prepareSession,
                    on_selecting_checkpoint=lambda _: self.members.selectingCheckpoint(),
                    on_checking_players=lambda _: self.members.checkingPlayers(),
                    on_ask_checkpoint=self.askCheckpoint,
                    on_ask_yes_no=self.askYesNo)

        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        actionsCtx = App.get_running_app().titleBar.actionsCtx
        actionsCtx.bind(on_disconnect=self.disconnect, on_ready=self.ready)
        self.bind(open=actionsCtx.setter("open"))

    def askCheckpoint(self, _: EventDispatcher):
        input = TextInputPopup()

        input.bind(on_validate=lambda _, text_input: self.rboCI.replyCheckpoint(text_input))
        input.open()

    def askYesNo(self, _: EventDispatcher, **args):
        input = YesNoPopup(**args)

        input.bind(on_reply=lambda _, reply: self.rboCI.replyYesNo(reply))
        input.open()

    def memberRegistered(self, _: EventDispatcher, **args):
        self.members.registered(**args)
        self.logs.log("[i]{name} [{id}] vient de rejoindre le lobby.[/i]".format(**args))

    def memberUnregistered(self, _: EventDispatcher, **args):
        args["name"] = self.members.name(**args)
        self.logs.log("[i]{name} [{id}] vient de quitter le lobby.[/i]".format(**args))
        self.members.unregistered(args["id"])

    def readyMember(self, _: EventDispatcher, **args):
        self.members.toggleReady(**args)

        ready = self.members.ready(**args)
        self.logs.log("{} [{}] {}.".format(self.members.name(**args), args["id"], "est prêt" if ready else "n'est plus prêt"))

    def preparingSession(self, _: EventDispatcher, **args):
        app.setTitle("Rbo - Lobby (Préparation)")
        self.logs.log("Préparation de la session dans [b]{delay} ms[/b]...".format(**args))

    def cancelPreparing(self, _: EventDispatcher):
        app.setTitle("Rbo - Lobby")
        self.logs.log("Préparation de la session annulée.")

    def prepareSession(self, _: EventDispatcher, id: int):
        self.open = False
        self.members.prepareSession()
        self.logs.log("Préparation de la session, [b]{} [{}] est le membre maître[/b].".format(self.members.name(id), id))

    def ready(self, _: EventDispatcher):
        self.rboCI.ready()

    def disconnect(self, _: EventDispatcher):
        if self.open:
            self.rboCI.disconnect()
        else:
            self.rboCI.close()
