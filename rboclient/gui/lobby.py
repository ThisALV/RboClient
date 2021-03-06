from enum import Enum, auto
from math import nan, isnan

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import ErrorPopup, GameCtxActions, ScrollableStack, TextInputPopup, YesNoPopup
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


class LobbyCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans le lobby, à savoir se signaler (non) prêt et se déconnecter pour revenir à l'accueil."

    actions = ["disconnect", "ready"]
    open = BooleanProperty(True)


class LogMessage(Label):
    "Message dans l'historique."

    background = ColorProperty([0, 0, 0])

    def __init__(self, msg: str, bg: "list[float]", **kwargs):
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
    CHECKING_PARTICIPANTS = auto(),
    REVISING_SESSION = auto()


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
        MemberStatus.CHECKING_PARTICIPANTS: ("Vérifie les joueurs...", [1, 1, 0]),
        MemberStatus.REVISING_SESSION: ("Corrige les paramètres...", [1, 1, 0])
    }

    def __init__(self, id: int, name: str, me: bool, **kwargs):
        super().__init__(id=id, name=name, me=me, **kwargs)


class MemberNotFound(ValueError):
    def __init__(self, id: int):
        super().__init__("Member [{}] doesn't exist".format(id))


class Members(ScrollableStack):
    """Liste des membres.

    Cette liste scrollable fait l'inventaire de tous les membres présents.\n
    Elle affiche également leur statut : identifiant, pseudo et ce qu'ils sont en train de faire.
    """

    previousMaster = nan
    master = NumericProperty(nan)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.members = {}

        Clock.schedule_once(self.initContent)

    def initContent(self, _: int):
        self.content.padding = 5
        self.content.spacing = 5

    def checkMember(self, id: int) -> None:
        if id not in self.members:
            raise MemberNotFound(id)

    def on_master(self, _: EventDispatcher, newMasterID: int):
        masterDisconnected = self.previousMaster not in self.members
        firstMaster = isnan(self.previousMaster)

        if not firstMaster and not masterDisconnected:
            self.members[self.previousMaster].master = False

        if not isnan(newMasterID):
            self.checkMember(newMasterID)
            self.members[newMasterID].master = True

        self.previousMaster = newMasterID

    def registered(self, id: int, name: str, me: bool = False) -> None:
        if id in self.members:
            raise ValueError("Multiple members with same ID")

        self.members[id] = Member(id, name, me)
        self.content.add_widget(self.members[id])

    def unregistered(self, id: int) -> None:
        self.checkMember(id)

        self.content.remove_widget(self.members[id])
        self.members.pop(id)

    def toggleReady(self, id: int) -> None:
        self.checkMember(id)

        member = self.members[id]
        member.status = MemberStatus.WAITING if member.status == MemberStatus.READY else MemberStatus.READY

    def selectingCheckpoint(self) -> None:
        self.members[self.master].status = MemberStatus.CHECKPT

    def checkingPlayers(self) -> None:
        self.members[self.master].status = MemberStatus.CHECKING_PARTICIPANTS

    def revisingSession(self) -> None:
        self.members[self.master].status = MemberStatus.REVISING_SESSION

    def prepareSession(self) -> None:
        for member in self.members.values():
            member.status = MemberStatus.PARTICIPANT

    def lobbyOpened(self) -> None:
        for member in self.members.values():
            member.status = MemberStatus.WAITING

    def name(self, id: int) -> str:
        self.checkMember(id)
        return self.members[id].name

    def ready(self, id: int) -> bool:
        self.checkMember(id)
        return self.members[id].status == MemberStatus.READY


class Lobby(Step, BoxLayout):
    """Lobby d'une partie.

    Gère tous les évènements d'un lobby (liste de membres, lancement de session, logs...).\n
    Actualise l'affichage et demande la saisie d'une configuration au membre maître si nécessaire.
    """

    logs = ObjectProperty()
    members = ObjectProperty()
    master = NumericProperty()

    open = BooleanProperty(True)

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", selfIncluded: bool = False, preparing: bool = False, errorMessage: str = None, **kwargs):
        super().__init__(**kwargs)
        self.init("Lobby", rboCI, app.TitleBarCtx.LOBBY)

        # Doit être bind avant d'ajouter les joueurs sinon le nouveau membre master ne sera pas pris en compte
        self.members.bind(master=self.setter("master"))

        # Si le joueur ne vient pas de s'inscrire, alors il sera déjà parmis les membres du serveur
        if not selfIncluded:
            self.members.registered(self.rboCI.id, self.rboCI.name, me=True)

        for (id, member) in members.items():
            self.members.registered(id, member[0], me=(id == self.rboCI.id))
            if member[1]:
                self.members.toggleReady()

        if preparing:
            self.members.prepareSession()

        if errorMessage is None:
            self.errorMessage = None
        else:
            self.errorMessage = ErrorPopup("Erreur lors de la session", errorMessage)

            self.errorMessage.bind(on_dismiss=self.errorMessageDismissed)
            self.errorMessage.open()

        self.listen(on_member_registered=self.memberRegistered,
                    on_member_ready=self.readyMember,
                    on_member_disconnected=self.memberUnregistered,
                    on_member_crashed=self.memberUnregistered,
                    on_master_switch_new=self.masterUpdated,
                    on_master_switch_none=self.masterReset,
                    on_preparing_session=self.preparingSession,
                    on_cancel_preparing=self.cancelPreparing,
                    on_prepare_session=self.prepareSession,
                    on_selecting_checkpoint=lambda _: self.members.selectingCheckpoint(),
                    on_checking_players=lambda _: self.members.checkingPlayers(),
                    on_revising_parameters=lambda _: self.members.revisingSession(),
                    on_ask_checkpoint=self.askCheckpoint,
                    on_ask_yes_no=self.askYesNo,
                    on_master_disconnected=self.masterDisconnected,
                    on_lobby_open=self.opened)

        Clock.schedule_once(lambda _: self.bindTitleBar(preparing))

    def bindTitleBar(self, preparing: bool):
        actionsCtx = App.get_running_app().titleBar.actionsCtx
        actionsCtx.bind(on_disconnect=self.disconnect, on_ready=self.ready)

        if type(actionsCtx) != LobbyCtxActions:
            return  # En cas d'erreur, il est possible que l'on ait déjà quitté le lobby

        self.bind(open=actionsCtx.setter("open"))
        self.open = not preparing

    def errorMessageDismissed(self, _: EventDispatcher):
        self.errorMessage = None

    def afterErrorMessage(self, popup: Popup) -> None:
        if self.errorMessage is None:
            popup.open()
        else:
            self.errorMessage.bind(on_dismiss=lambda _: popup.open())

    def askCheckpoint(self, _: EventDispatcher):
        input = TextInputPopup()

        input.bind(on_validate=lambda _, text_input: self.rboCI.replyCheckpoint(text_input))
        self.afterErrorMessage(input)

    def askYesNo(self, _: EventDispatcher, **args):
        input = YesNoPopup(**args)

        input.bind(on_reply=lambda _, reply: self.rboCI.replyYesNo(reply))
        self.afterErrorMessage(input)

    def memberRegistered(self, _: EventDispatcher, **args):
        self.members.registered(**args)
        self.logs.log("[i]{name} [{id}] vient de rejoindre le lobby.[/i]".format(**args))

    def memberUnregistered(self, _: EventDispatcher, **args):
        args["name"] = self.members.name(**args)
        self.logs.log("[i]{name} [{id}] vient de quitter le lobby.[/i]".format(**args))
        self.members.unregistered(args["id"])

    def masterUpdated(self, _: EventDispatcher, id: int):
        self.members.master = id

    def masterReset(self, _: EventDispatcher):
        self.members.master = nan

    def readyMember(self, _: EventDispatcher, **args):
        self.members.toggleReady(**args)

        ready = self.members.ready(**args)
        self.logs.log("{} [{}] {}.".format(self.members.name(**args), args["id"], "est prêt" if ready else "n'est plus prêt"))

    def preparingSession(self, _: EventDispatcher, **args):
        app.setTitle("Lobby (Préparation)")
        self.logs.log("Préparation de la session dans [b]{delay} ms[/b]...".format(**args))

    def opened(self, _: EventDispatcher = None):
        self.open = True
        self.members.lobbyOpened()

    def masterDisconnected(self, _: EventDispatcher):
        app.setTitle("Lobby")
        self.opened()
        self.logs.log("Membre maître déconnecté, préparation de la session annulée.")

    def cancelPreparing(self, _: EventDispatcher):
        app.setTitle("Lobby")
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
