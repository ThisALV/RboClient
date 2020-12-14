from enum import Enum, auto
from math import nan

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import GameCtxActions, ScrollableStack
from rboclient.network.protocol import RboConnectionInterface as RboCI

INTRODUCTION = 0
ALL_PLAYERS = 255


class SessionCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans la session, à savoir se déconnecter pour revenir à l'accueil."

    actions = ["disconnect"]


class BookMsg(Label):
    "Affiche un message du livre, s'insère dans un Book."

    def __init__(self, msg: str, **kwargs):
        super().__init__(text=msg, **kwargs)


class BookSection(Label):
    "Affiche le titre d'une section, s'insère dans un Book."

    def __init__(self, msg: str, **kwargs):
        super().__init__(text=msg, **kwargs)


class Book(ScrollableStack):
    """Représente le livre du jeu.

    C'est ici que sont écrits l'histoire, les combats et l'historique de tout ce qu'il se passe durant la partie.\n
    Peut être divisé en plusieurs sections en ajoutant un titre avec newSection().\n
    sceneSwitch() appelle newSection() pour le cas d'un changement de scène.
    """

    def print(self, _: EventDispatcher, text: str):
        self.content.add_widget(BookMsg(text))

    def sceneSwitch(self, _: EventDispatcher, scene: int):
        self.newSection("Introduction" if scene == INTRODUCTION else "Page {}".format(scene))

    def newSection(self, text: str) -> None:
        self.content.add_widget(BookSection(text))


class DiceRoll(BoxLayout):
    """Simule un lancé de dés.

    Affiche une animation de lancé de dés avec un message réglable.\n
    Cela permet d'aider à le joueur à comprendre comment les stats ont été tirées.\n
    Émet on_finished lorsque l'action est terminée.
    """

    message = StringProperty()
    dices = NumericProperty()
    bonus = NumericProperty()
    result = NumericProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_finished")
        super().__init__(**kwargs)


class ActionInProgress(Exception):
    def __init__(self):
        super().__init__("The gameplay screen is already into an action")


class Gameplay(FloatLayout):
    """Zone de jeu de la session.

    Initialement, affiche les logs de la partie.\n
    rollDice() permet de déclencher l'écran de lancement de dés jusqu'à l'appel de back() qui retourne aux logs.
    """

    book = ObjectProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_action_finished")
        super().__init__(**kwargs)

        self.currentAction = None

    def back(self, _: EventDispatcher):
        if self.currentAction is None:
            return

        self.remove_widget(self.currentAction)
        self.currentAction = None

        self.dispatch("on_action_finished")

    def action(self, action: EventDispatcher) -> None:
        if self.currentAction is not None:
            raise ActionInProgress()

        self.currentAction = action
        self.currentAction.pos_hint = {"x": 0, "y": 0}
        self.currentAction.size_hint = (1, 1)
        self.currentAction.bind(on_finished=self.back)

        self.add_widget(self.currentAction)

    def rollDice(self, message: str, dices: int, bonus: int, result: int) -> None:
        pass


class StatValue(Label):
    "Paire clé/valuer d'une statistique d'une entité"

    name = StringProperty()
    value = NumericProperty()

    def __init__(self, name: str, value: int, **kwargs):
        super().__init__(name=name, value=value, **kwargs)


class UnknownStat(ValueError):
    def __init__(self, name: str):
        super().__init__("Unknown stat \"{}\"".format(name))


class StatsView(ScrollableStack):
    """Apperçu des statistiques d'une entité.

    Liste les statistiques d'une entitée sous la forme de labels "nom de stat : valeur" réparties dans deux colonnes.\n
    Propose un refresh des données avec refresh(stats). Seuls les stats ayant des valeurs dans l'argument stats seront rafraîchies.\n
    Les stats qui n'étaient pas encore présentes seront rajoutées.\n
    Pour masquer une stat, il faut lui affecter la valeur None en argument de refresh(stats). Si la stat n'est pas déjà présente, rien ne se passe.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.stats = {}
        Clock.schedule_once(self.initContent)

    def initContent(self, _: int):
        self.content.padding = 15
        self.content.spacing = 5

    def refresh(self, stats: "dict[str, int]") -> None:
        for (stat, value) in stats.items():
            hideStat = value is None

            if stat in self.stats:
                if hideStat:
                    self.content.remove_widget(self.stats[stat])
                    self.stats.pop(stat)
                else:
                    self.stats[stat].value = value
            else:
                if not hideStat:
                    self.stats[stat] = StatValue(stat, value)
                    self.content.add_widget(self.stats[stat])


class RequestReplied(Enum):
    WAITING = auto(),
    NO = auto(),
    YES = auto()


class Player(BoxLayout):
    """Apperçu des informations d'un joueur.

    Affiche les informations basiques (identifiant, nom et stats principales) à propos d'un joueur.\n
    Indique également lors d'une requête s'il a déjà répondu à celle-ci ou non.\n
    Peut être sélectionné ou désélectionné (propriété selected), foreground/background color s'inversent en conséquence.
    """

    playerID = NumericProperty()
    name = StringProperty()
    isSelf = BooleanProperty()
    isLeader = BooleanProperty(False)
    hasReplied = ObjectProperty(RequestReplied.WAITING)

    requestStatus = {
        RequestReplied.WAITING: ("", [0, 0, 0]),
        RequestReplied.NO: ("\u00d7", [1, .3, .3]),
        RequestReplied.YES: ("\u2713", [.3, 1, .3])
    }

    stats = ObjectProperty()

    def __init__(self, id: int, name: str, isSelf: bool, **kwargs):
        super().__init__(playerID=id, name=name, isSelf=isSelf, **kwargs)

    def on_hasReplied(self, _: EventDispatcher, hasReplied: RequestReplied):
        Logger.debug("Player {} : Replied ? \"{}\"".format(self.playerID, hasReplied))


class PlayerNotFound(ValueError):
    def __init__(self, id: int):
        super().__init__("Player [{}] doesn't exist".format(id))


class Players(ScrollableStack):
    """Affiche une liste des joueurs présents.

    Chaque joueur possède un apperçu de son état (voir Player). addPlayer(...) permet d'ajouter un joueur et removePlayer(...) d'en supprimer un.\n
    La liste écoute chaque widget enfant Player pour savoir s'il a été sélectionné et émettre on_enable(playerID) en conséquence.\n
    Il est possible de rafraîchir l'apperçu des stats principales d'un joueur avec refreshMainStats(playerID).\n
    Cette liste s'occupe également de gérer les statuts des joueurs pendant une requête (a répondu ou non).
    Pour cela il faut utiliser beginRequest(), replied(playerID) et endRequest().\n
    Enfin permet de désigner un leader parmis les joueurs avec leader(playerID).
    """

    def __init__(self, **kwargs):
        for event in ["enable", "disable"]:
            self.register_event_type("on_" + event)
        super().__init__(**kwargs)

        self.players = {}
        self.leader = None

    def selection(self, player: Player, selected: bool):
        if selected:
            self.dispatch("on_enable", player.playerID)
        else:
            self.dispatch("on_disable")

    def on_enable(self, playerID: int):
        Logger.debug("Players : selected [{}]".format(playerID))

    def on_disable(self):
        Logger.debug("Players : player unselected")

    def checkPlayerID(self, id: int) -> None:
        if id not in self.players:
            raise PlayerNotFound(id)

    def addPlayer(self, id: int, name: str, isSelf: bool) -> None:
        player = Player(id, name, isSelf)

        self.players[id] = player
        self.content.add_widget(player)
        player.bind(on_selected=self.selection)

    def removePlayer(self, id: int) -> None:
        self.checkPlayerID(id)

        self.content.remove_widget(self.players[id])
        self.players.pop(id)

    def refreshMainStats(self, id: int, stats: "dict[str, int]") -> None:
        self.checkPlayerID(id)

        self.players[id].stats.refresh(stats)

    def beginRequest(self, target: int) -> None:
        targets = self.players.values() if target == ALL_PLAYERS else [self.players[target]]

        for player in targets:
            player.hasReplied = RequestReplied.NO

    def replied(self, id: int) -> None:
        self.players[id].hasReplied = RequestReplied.YES

    def endRequest(self) -> None:
        for player in self.players.values():
            player.hasReplied = RequestReplied.WAITING

    def switchLeader(self, id: int) -> None:
        if self.leader is not None:
            self.players[self.leader].isLeader = False

        self.leader = id
        self.players[self.leader].isLeader = True


class Session(Step, BoxLayout):
    """Session d'une partie.

    Gère tous les évènements qui peuvent avoir lieu au cours d'une partie (session).\n
    Actualise l'affichage en conséquence et propose un bouton "Confirmer" ainsi qu'une popup afin de répondre aux requêtes reçues.
    """

    name = StringProperty()

    gameplay = ObjectProperty()
    book = ObjectProperty()

    confirm = ObjectProperty()

    details = ObjectProperty()
    players = ObjectProperty()

    def __init__(self, selfID: int, initialLeader: int, gameName: str, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init("Session on " + gameName, rboCI, app.TitleBarCtx.SESSION)

        self.name = gameName
        self.members = members

        for (id, name) in self.members.items():
            self.players.addPlayer(id, name, id == selfID)
        self.players.switchLeader(initialLeader)

        class RequestHandler:
            context = self

            def __init__(self, replyInput):
                self.replyInput = replyInput

            def __call__(self, _: EventDispatcher, **args):
                session = self.context
                session.players.beginRequest(args["target"])

                self.replyInput(**args)

        self.listen(on_text=self.book.print,
                    on_scene_switch=self.book.sceneSwitch,
                    on_request_confirm=RequestHandler(self.askConfirm),
                    on_finish_request=self.finishRequest,
                    on_player_reply=self.playerReplied,
                    on_player_update=self.updatePlayer)

        Clock.schedule_once(lambda _: self.confirm.bind(on_release=lambda _: self.rboCI.confirm()))
        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())

    def askConfirm(self, target: int):
        if target == ALL_PLAYERS or target == self.rboCI.id:
            self.confirm.disabled = False

    def playerReplied(self, _: EventDispatcher, **args):
        if args["id"] == self.rboCI.id:
            self.confirm.disabled = True

        self.players.replied(args["id"])

    def finishRequest(self, _: EventDispatcher):
        self.players.endRequest()
        self.confirm.disabled = True

    def updatePlayer(self, _: EventDispatcher, **args):
        (id, update) = args.values()

        statsUpdate = update["stats"]
        showStats = {}
        for (name, stat) in statsUpdate.items():
            main = stat["main"]
            hidden = stat["hidden"]

            if main:
                showStats[name] = None if hidden else stat["value"]
            else:
                showStats[name] = None

        self.players.refreshMainStats(id, showStats)
