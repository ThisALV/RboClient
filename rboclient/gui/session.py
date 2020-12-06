from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.gui.widgets import GameCtxActions, ScrollableStack
from rboclient.network.protocol import RboConnectionInterface as RboCI

INTRODUCTION = 0


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
        self.newSection("Introduction" if scene == INTRODUCTION else "Scène {}".format(scene))

    def newSection(self, text: str) -> None:
        self.content.add_widget(BookSection(text))


class StatValue(Label):
    "Paire clé/valuer d'une statistique d'une entité"

    name = StringProperty()
    value = NumericProperty()

    def __init__(self, name: str, value: int, **kwargs):
        super().__init__(name=name, value=value, **kwargs)


class StatsView(ScrollableStack):
    """Apperçu des statistiques d'une entité.

    Liste les statistiques d'une entitée sous la forme de labels "nom de stat : valeur" réparties dans deux colonnes.\n
    Propose un refresh des données avec refresh(stats). Seuls les stats ayant des valeurs dans l'argument stats seront rafraîchies.\n
    Les stats qui n'étaient pas encore présentes seront rajoutées.\n
    Il est impossible de "masquer" une stat que l'on a décidé d'afficher au moins une fois."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.content.orientation = "tb-lr"
        self.stats = {}

    def refresh(self, stats: "dict[str, StatValue]") -> None:
        for (stat, value) in stats.items():
            if stat in self.stats:
                self.stats[stat].value = value
            else:
                self.stats[stat] = StatValue(stat, value)
                self.add_widget(self.stats[stat])


class Players(ScrollableStack):
    pass


class Session(Step, BoxLayout):
    """Session d'une partie.

    Gère tous les évènements qui peuvent avoir lieu au cours d'une partie (session).\n
    Actualise l'affichage en conséquence et propose un bouton "Confirmer" ainsi qu'une popup afin de répondre aux requêtes reçues."""

    name = StringProperty()

    book = ObjectProperty()
    confirm = ObjectProperty()

    currentRequest = ObjectProperty()

    def __init__(self, gameName: str, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init("Session on " + gameName, rboCI, app.TitleBarCtx.SESSION)

        self.name = gameName
        self.members = members

        self.listen(on_text=self.book.print,
                    on_scene_switch=self.book.sceneSwitch,
                    on_request_confirm=self.waitConfirm)

        Clock.schedule_once(lambda _: self.confirm.bind(on_release=self.confirmed))
        Clock.schedule_once(self.bindTitleBar)

    def bindTitleBar(self, _: int):
        App.get_running_app().titleBar.actionsCtx.bind(on_disconnect=lambda _: self.rboCI.close())

    def waitConfirm(self, _: EventDispatcher):
        self.confirm.disabled = False

    def confirmed(self, _: EventDispatcher):
        self.confirm.disabled = True
        self.rboCI.confirm()
