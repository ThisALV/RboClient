from enum import Enum, auto
from math import nan
from random import randrange

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.input import MotionEvent
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ColorProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.stacklayout import StackLayout
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import DictionnaryView, GameCtxActions, ScrollableStack
from rboclient.network.protocol import RboConnectionInterface as RboCI

INTRODUCTION = 0
ALL_PLAYERS = 255
ACTIVE_PLAYERS = ALL_PLAYERS - 1


class SessionCtxActions(GameCtxActions):
    "Actions contextuelles disponibles dans la session, à savoir se déconnecter pour revenir à l'accueil."

    actions = ["disconnect"]


class GameLog(Label):
    "Classe mère pour afficher un message de log."

    def __init__(self, msg: str, **kwargs):
        super().__init__(text=msg, **kwargs)


class LogsMsg(GameLog):
    "Affiche un message de logs, s'insère dans un Logs."


class LogsTitle(GameLog):
    "Affiche un message de titre, s'insère dans un Logs."


class GameLogs(ScrollableStack):
    """Représente l'historique de la partie.

    C'est ici que sont écrits l'histoire, les combats et tout ce qu'il peut se passer durant une partie.\n
    Il existe 4 types de messages : normaux, importants, titre et note.
    Ils peuvent être écrits en utilisant respectivement : print(), important(), title() et note().\n
    Un autre type de message peut être utilisé pour afficher la mort d'un joueur avec playerDeath().
    Les arguments sont l'ID, le nom du joueur et la raison de sa mort.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        Clock.schedule_once(self.initContent)

    def initContent(self, _: int):
        self.content.spacing = 15

    def print(self, _: EventDispatcher, text: str):
        self.content.add_widget(LogsMsg(text))

    def important(self, _: EventDispatcher, text: str):
        self.content.add_widget(LogsMsg(text, bold=True))

    def title(self, _: EventDispatcher, text: str):
        self.content.add_widget(LogsTitle(text))

    def note(self, _: EventDispatcher, text: str):
        self.content.add_widget(LogsMsg(text, italic=True))

    def playerDeath(self, playerID: int, playerName: str, reason: str) -> None:
        self.content.add_widget(LogsMsg("Le joueur [{}] {} est mort : {}".format(playerID, playerName, reason),
                                        italic=True, bold=True, color=[1, .4, .4]))


def diceFace(face: int) -> str:
    "Retourne un caractère unicode \"face de dé\" correspondant à l'argument face."

    return chr(0x2680 + face - 1)


def randomFace() -> str:
    "Retourne un caractère unicode \"face de dé\" au hasard."

    return diceFace(randrange(1, 7))


class Dices(Label):
    """Anime un ou plusieurs dés qui seront lancés.

    La propriété dices permet de renseigner combien de dés sont à jouer.\n
    Lors que roll() est appelée avec le résultat de chacun des dés, l'animation de roulement des dés ralentit jusqu'à s'arrêter.
    Après l'appel à roll(), les dés sont organisés pour reproduire le résultat du tirage reçu.
    """

    lastRollingDelayMs = 750

    dices = NumericProperty()

    rollingDices = StringProperty()
    rollingDelayMs = NumericProperty(100)
    rolled = BooleanProperty(False)
    rollFinished = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.skipped = False
        self.result = None

        App.get_running_app().runTask("game_dices_roll")
        self.rolling()

    def rolling(self, _: int = None):
        client = App.get_running_app()
        if self.rollFinished:
            self.text = " ".join([diceFace(dice) for dice in self.result])
            client.stopTask("game_dices_roll")
        else:
            self.text = " ".join([randomFace() for i in range(self.dices)])

            if self.skipped:
                self.rollingDelayMs = Dices.lastRollingDelayMs
                self.rolling()
            else:
                if self.rolled:
                    self.rollingDelayMs *= 1.2

                if self.rollFinished:
                    self.rolling()
                elif client.isRunning("game_dices_roll"):
                    Clock.schedule_once(self.rolling, self.rollingDelayMs / 1000)

    def roll(self, result: "list[int]", skip: bool = False) -> None:
        self.result = result
        self.rolled = True
        self.skipped = skip


class DiceRoll(BoxLayout):
    """Simule un lancé de dés.

    Affiche une animation de lancé de dés avec un message réglable.\n
    Cela permet d'aider à le joueur à comprendre comment les stats ont été tirées.\n
    Émet on_finished lorsque l'action est terminée.
    """

    message = StringProperty()
    dices = NumericProperty()
    bonus = NumericProperty()
    result = ListProperty()
    total = NumericProperty()

    rollAnimation = ObjectProperty()

    def __init__(self, ctx: "Session", **kwargs):
        self.register_event_type("on_finished")
        super().__init__(**kwargs)

        self.context = ctx

    def on_finished(self):
        Logger.debug("Gameplay : Dice roll finished")
        self.context.rboCI.confirm()

    def next(self, skip: bool = False) -> None:
        if self.rollAnimation.rolled:
            self.dispatch("on_finished")
        else:
            self.rollAnimation.roll(self.result, skip)


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

    def on_action_finished(self):
        pass

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

    def rollDice(self, ctx: "Session", message: str, dices: int, bonus: int, result: "list[int]") -> None:
        self.action(DiceRoll(ctx, message=message, dices=dices, bonus=bonus, result=result))


class RequestReplied(Enum):
    WAITING = auto(),
    NO = auto(),
    YES = auto()


class Player(BoxLayout):
    """Apperçu des informations d'un joueur.

    Affiche les informations basiques (identifiant, nom et stats principales) à propos d'un joueur.\n
    Indique également lors d'une requête s'il a déjà répondu à celle-ci ou non.\n
    Peut être sélectionné ou désélectionné (propriété selected), foreground/background color s'inversent en conséquence.\n
    Une propriété dead permet de mettre à jour le style du texte lorsque le joueur meurt.
    """

    playerID = NumericProperty()
    name = StringProperty()
    isSelf = BooleanProperty()
    isLeader = BooleanProperty(False)
    hasReplied = ObjectProperty(RequestReplied.WAITING)
    dead = BooleanProperty(False)

    selected = BooleanProperty(False)
    foreground = ColorProperty()

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

    def on_touch_down(self, touch: MotionEvent):
        if self.collide_point(*touch.pos):
            self.selected = not self.selected


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
    Enfin permet de désigner un leader parmis les joueurs avec leader(playerID).\n
    Un joueur mort peut être signalé avec la méthode dead() prenant aussi l'ID en argument.
    """

    def __init__(self, **kwargs):
        for event in ["enable", "disable"]:
            self.register_event_type("on_" + event)
        super().__init__(**kwargs)

        self.players = {}
        self.leader = None
        self.selected = None
        self.playerSwitch = False

    def selection(self, player: Player, selected: bool):
        if selected:
            self.dispatch("on_enable", player.playerID)

            if self.selected is not None:
                self.playerSwitch = True
                self.players[self.selected].selected = False

            self.selected = player.playerID
        else:
            if self.playerSwitch:
                self.playerSwitch = False
            else:
                self.dispatch("on_disable")
                self.selected = None

    def on_enable(self, playerID: int):
        Logger.debug("Players : Selected [{}]".format(playerID))

    def on_disable(self):
        Logger.debug("Players : Player unselected")

    def checkPlayerID(self, id: int) -> None:
        if id not in self.players:
            raise PlayerNotFound(id)

    def addPlayer(self, id: int, name: str, isSelf: bool) -> None:
        player = Player(id, name, isSelf)

        self.players[id] = player
        self.content.add_widget(player)
        player.bind(selected=self.selection)

    def removePlayer(self, id: int) -> None:
        self.checkPlayerID(id)

        if self.selected == id:
            self.players[id].selected = False

        self.content.remove_widget(self.players[id])
        self.players.pop(id)

    def refreshMainStats(self, id: int, stats: "dict[str, int]") -> None:
        self.checkPlayerID(id)

        self.players[id].stats.refresh(stats)

    def beginRequest(self, target: int) -> None:
        if target == ALL_PLAYERS:
            targets = self.players.values()
        elif target == ACTIVE_PLAYERS:
            targets = [p for p in self.players.values() if not p.dead]
        else:
            targets = [self.players[target]]

        for player in targets:
            player.hasReplied = RequestReplied.NO

    def replied(self, id: int) -> None:
        self.players[id].hasReplied = RequestReplied.YES

    def endRequest(self) -> None:
        for player in self.players.values():
            player.hasReplied = RequestReplied.WAITING

    def leaderSwitch(self, id: int) -> None:
        if self.leader in self.players:
            self.players[self.leader].isLeader = False

        self.leader = id
        self.players[self.leader].isLeader = True

    def getName(self, id: int) -> None:
        self.checkPlayerID(id)

        return self.players[id].name

    def alive(self, id: int) -> bool:
        return not self.players[id].dead

    def dead(self, id: int) -> None:
        self.checkPlayerID(id)

        self.players[id].dead = True


class Inventory(BoxLayout):
    """Affichage d'un inventaire dans InventoriesView.

    Ce widget affiche le nom de l'inventaire en question.
    Ce nom est cliquable et permet de faire dérouler la DictionnaryView des objets contenus dans l'inventaire.\n
    La DictionnaryView contenant les objets ainsi que leur quantité respective est mise à jour via la méthode refresh() de Inventory.\n
    En plus des objets contenus, à chaque mise à jour un recomptage du nombre d'objets total dans l'inventaire est effectué pour être affiché.
    La capacité de l'inventaire (via capacity) est également affichée.
    """

    name = StringProperty()
    count = NumericProperty(0)
    capacity = NumericProperty(-1)
    shown = BooleanProperty(False)

    title = ObjectProperty()
    itemsView = ObjectProperty()

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.itemsDict = DictionnaryView([.025, .025, .025])

    def on_touch_down(self, touch: MotionEvent):
        if not self.title.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        if self.shown:
            self.itemsView.remove_widget(self.itemsDict)
        else:
            self.itemsView.add_widget(self.itemsDict)

        self.shown = not self.shown
        return True

    def refresh(self, items: "dict[str, int]") -> None:
        self.itemsDict.refresh(items)
        self.count = sum([pair.value for pair in self.itemsDict.pairs.values()])


class UnknownInventory(KeyError):
    def __init__(self, name: str):
        super().__init__("Inventory \"{}\" doesn't exist".format(name))


class InventoriesView(ScrollableStack):
    """Affichage des inventaires d'un joueur.

    Ce widget scrollable verticalement contient une liste d'inventaires dont les données peuvent être mises à jour avec la méthode refresh().\n
    refresh() prend en paramètre une dict[str, tuple[int, dict[str, int]]] pour mettre à jour chaque inventaire nommée avec un dict[str, int].
    Ce dict[str, int] met à jour chaque inventaire comme on met à jour une DictionnaryView.
    Le int du tuple lui est utilisé pour mettre à jour la capacité de l'inventaire en question, la valeur None conserve la capacité actuelle.\n
    Les inventaires sont ajoutés après construction à l'aide de la méthode addInventory() renseignant le nom de celui-ci.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.inventories = {}

    def addInventory(self, name: str) -> None:
        self.inventories[name] = Inventory(name)
        self.content.add_widget(self.inventories[name])

    def refresh(self, inventories: "dict[str, tuple[int, dict[str, int]]]") -> None:
        for (name, (capacity, inv)) in inventories.items():
            if name not in self.inventories:
                raise UnknownInventory(name)

            inventory = self.inventories[name]
            inventory.refresh(inv)

            if capacity is not None:
                inventory.capacity = capacity


class DetailsLayout(StackLayout):
    """Layout commun à toutes les zones affichant les caractéristiques de la partie.
    Occupe la moitié de la hauteur disponible (calculée à partir de self.parent.height).
    """


class GameDetails(DetailsLayout):
    "1ère partie du panneau central : caractéristiques générales du jeu."

    gameName = StringProperty()
    leader = NumericProperty(-1)  # Cet ID n'étant pas disponible, il marquera leader comme étant non-initialisée
    mainStats = ObjectProperty()


class GlobalDetails(DetailsLayout):
    "2ème partie du panneau central : toutes les statistiques globales."

    stats = ObjectProperty()


class PlayerDetails(DetailsLayout):
    """2ème partie du panneau central : toutes les caractéristiques d'un joueur.

    Les propriétés id, name et leader permettent de mettre à jour les caractéristiques de base du joueur.\n
    refreshStats() et refreshInventories() permettent de mettre à jour les autres caractéristiaues (stats et inventaires).\n
    Lorsque le bouton Fermer est utilisé, un event on_close est émis.
    """

    id = NumericProperty()
    name = StringProperty()
    leader = BooleanProperty(False)

    stats = ObjectProperty()
    inventories = ObjectProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_close")
        super().__init__(**kwargs)

        self.inventoriesInitialized = False

    def on_close(self):
        Logger.debug("Detais : Player {} closed".format(self.id))

    def refreshStats(self, stats: "dict[str, int]") -> None:
        self.stats.refresh(stats)

    def refreshInventories(self, inventories: "dict[str, tuple[int, dict[str, int]]]") -> None:
        if not self.inventoriesInitialized:
            for name in inventories.keys():
                self.inventories.addInventory(name)

            self.inventoriesInitialized = True

        self.inventories.refresh(inventories)


class Details(StackLayout):
    """Panneau central des caractéristiques du jeu.

    1ère partie consacrée aux caractéristiques générales de la partie : nom du jeu, scène, leader, etc.\n
    2ème partie variable en fonction du joueur sélectionné.
    Cette partie affiche l'entièreté des stats globales si aucun joueur n'est sélectionné.\n
    refreshPlayer() met à jour les caractéristiques d'un joueur. showPlayer() et showGlobal() permettent de basculer d'un affichage à l'autre.\n
    sceneSwitch() et leaderSwitch() permettent de mettre à jour les caractéristiques générales de la partie.\n
    Un joueur déconnecté peut être retiré avec removePlayer() prenant l'ID du joueur en argument.
    """

    GLOBAL = 255

    gameDetails = ObjectProperty()
    specificDetails = ObjectProperty()

    def __init__(self, ctx: "Session", **kwargs):
        super().__init__(**kwargs)

        self.context = ctx
        self.context.players.bind(on_enable=self.showPlayer, on_disable=self.backToGlobal)

        self.details = {Details.GLOBAL: GlobalDetails()}
        self.specificDetails = self.details[Details.GLOBAL]
        self.add_widget(self.specificDetails)

        self.gameDetails.gameName = ctx.name

    def checkPlayerID(self, id: int) -> None:
        if id == Details.GLOBAL or id not in self.details:
            raise PlayerNotFound(id)

    def on_playerdetails_closed(self):
        pass

    def playerClosed(self, _: EventDispatcher) -> None:
        self.context.players.players[self.specificDetails.id].selected = False
        self.backToGlobal()

    def addPlayer(self, id: int, name: str) -> None:
        player = PlayerDetails(id=id, name=name)
        player.bind(on_close=self.playerClosed)

        self.details[id] = player

    def showPlayer(self, _: EventDispatcher, id: int) -> None:
        self.remove_widget(self.specificDetails)
        self.specificDetails = self.details[id]
        self.add_widget(self.specificDetails)

    def backToGlobal(self, _: EventDispatcher = None) -> None:
        self.showPlayer(None, Details.GLOBAL)

    def refreshMainGlobalStats(self, stats: "dict[str, int]") -> None:
        self.gameDetails.mainStats.refresh(stats)

    def refreshGlobalStats(self, stats: "dict[str, int]") -> None:
        self.details[Details.GLOBAL].stats.refresh(stats)

    def refreshPlayer(self, id: int, stats: "dict[str, int]", inventories: "dict[str, tuple[int, dict[str, int]]]") -> None:
        if id == Details.GLOBAL or id not in self.details:
            raise PlayerNotFound(id)

        player = self.details[id]
        player.refreshStats(stats)
        player.refreshInventories(inventories)

    def removePlayer(self, id: int) -> None:
        self.checkPlayerID(id)
        self.details.pop(id)  # Le joueur est sensé avoir été préalablement déselectionné

    def leaderSwitch(self, leader: int) -> None:
        if self.gameDetails.leader != -1 and self.gameDetails.leader in self.details:
            self.details[self.gameDetails.leader].leader = False

        self.gameDetails.leader = leader
        self.details[self.gameDetails.leader].leader = True


class Request(Enum):
    CONFIRM = auto(),
    DICE_ROLL = auto()


class NoCurrentRequest(Exception):
    def __init__(self):
        super().__init__("There isn't any active request")


class Session(Step, BoxLayout):
    """Session d'une partie.

    Gère tous les évènements qui peuvent avoir lieu au cours d'une partie (session).\n
    Actualise l'affichage en conséquence et propose un bouton "Confirmer" ainsi qu'une popup afin de répondre aux requêtes reçues.
    """

    requests = {
        Request.CONFIRM: "askConfirm",
        Request.DICE_ROLL: "askDiceRoll"
    }

    name = StringProperty()

    gameplay = ObjectProperty()
    logs = ObjectProperty()

    confirm = ObjectProperty()

    detailsScreen = ObjectProperty()
    players = ObjectProperty()

    def __init__(self, selfID: int, initialLeader: int, gameName: str, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init("Session sur \"{}\"".format(gameName), rboCI, app.TitleBarCtx.SESSION)

        self.name = gameName
        self.members = members

        self.details = Details(self)
        self.detailsScreen.add_widget(self.details)

        for (id, name) in self.members.items():
            self.details.addPlayer(id, name)
            self.players.addPlayer(id, name, id == selfID)

        self.players.leaderSwitch(initialLeader)
        self.details.leaderSwitch(initialLeader)

        class RequestHandler:
            context = self

            def __init__(self, requestType: Request):
                self.requestType = requestType

            def __call__(self, _: EventDispatcher, **args):
                session = self.context
                session.players.beginRequest(args["target"])

                self.context.currentRequest = self.requestType
                # Appel de la méthode en fonction du nom associé au type de la requête (voir Session.requests)
                getattr(self.context, Session.requests[self.requestType])(**args)

        self.listen(on_text_normal=self.logs.print,
                    on_text_important=self.logs.important,
                    on_text_title=self.logs.title,
                    on_text_note=self.logs.note,
                    on_scene_switch=self.switchScene,
                    on_leader_switch=self.switchLeader,
                    on_request_confirm=RequestHandler(Request.CONFIRM),
                    on_request_dice_roll=RequestHandler(Request.DICE_ROLL),
                    on_finish_request=self.finishRequest,
                    on_player_reply=self.playerReplied,
                    on_player_update=self.updatePlayer,
                    on_global_stat_update=self.updateGlobalStat)

        self.currentRequest = None

        Clock.schedule_once(lambda _: self.confirm.bind(on_release=lambda _: self.rboCI.confirm()))
        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())

    def isTargetted(self, target: int) -> bool:
        return target == ALL_PLAYERS or (target == ACTIVE_PLAYERS and self.players.alive(self.rboCI.id)) or target == self.rboCI.id

    def switchScene(self, _: EventDispatcher, scene: int):
        Logger.info("Session : Go to scene {}".format(scene))

    def switchLeader(self, _: EventDispatcher, id: int):
        self.players.leaderSwitch(id)
        self.details.leaderSwitch(id)

    def askConfirm(self, target: int) -> None:
        if self.isTargetted(target):
            self.confirm.disabled = False

    def askDiceRoll(self, target: int, message: str, dices: int, bonus: int, results: "dict[int, list[int]]") -> None:
        if self.isTargetted(target):
            self.gameplay.rollDice(self, message, dices, bonus, results[self.rboCI.id])

    def playerReplied(self, _: EventDispatcher, **args):
        if self.currentRequest is None:
            raise NoCurrentRequest()

        if args["id"] == self.rboCI.id:
            if self.currentRequest == Request.CONFIRM:
                self.confirm.disabled = True

        self.players.replied(args["id"])

    def finishRequest(self, _: EventDispatcher):
        self.players.endRequest()
        self.confirm.disabled = True

    def playerDie(self, _: EventDispatcher, id: int, reason: str):
        name = self.players.getName(id)

        self.players.dead(id)
        self.logs.playerDeath(id, name, reason)

    def updateGlobalStat(self, _: EventDispatcher, **args):
        name = args["name"]
        hidden = args["hidden"]
        value = args["value"]

        mainStats = {}
        allStats = {}
        if args["main"]:
            mainStats[name] = None if hidden else value
        else:
            mainStats[name] = None

        if hidden:
            allStats[name] = None
        else:
            allStats[name] = value

        self.details.refreshMainGlobalStats(mainStats)
        self.details.refreshGlobalStats(allStats)

    def updatePlayer(self, _: EventDispatcher, **args):
        (id, update) = args.values()

        death = update["death"]
        if death is not None:
            self.players.dead(id)
            self.logs.playerDeath(id, self.players.getName(id), death)

        statsUpdate = update["stats"]

        mainStats = {}
        allStats = {}
        for (name, stat) in statsUpdate.items():
            main = stat["main"]
            hidden = stat["hidden"]
            value = stat["value"]

            if main:
                mainStats[name] = None if hidden else value
            else:
                mainStats[name] = None

            if hidden:
                allStats[name] = None
            else:
                allStats[name] = value

        itemsUpdate = update["inventories"]
        capacitiesUpdate = update["capacities"]

        inventories = {}

        for (name, inv) in itemsUpdate.items():
            inventories[name] = (None, inv)

        for (name, capacity) in capacitiesUpdate.items():
            if name in inventories:
                inventories[name] = (capacity, inventories[name][1])
            else:
                inventories[name] = (capacity, {})

        self.players.refreshMainStats(id, mainStats)
        self.details.refreshPlayer(id, allStats, inventories)
