from rboclient.gui import config
from rboclient.gui.config import ConfigPopup

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ObjectProperty, DictProperty
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.app import App

from math import inf


class GraphicsCfg(BoxLayout):
    "Panneau de configuration pour renseigner des paramètres graphiques comme la résolution de la fenêtre."

    windowWidth = ObjectProperty()
    windowHeight = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config = App.get_running_app().rbocfg
        self.windowWidth.text = config.get("graphics", "width")
        self.windowHeight.text = config.get("graphics", "height")


class FieldsCfg(BoxLayout):
    "Panneau de configuration pour renseigner les valeurs par défauts des zones de saisie de la page d'accueil."

    hostInput = ObjectProperty()
    playerInput = ObjectProperty()
    localhostOption = ObjectProperty()
    masterOption = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config = App.get_running_app().rbocfg
        self.hostInput.fill(config)
        self.playerInput.fill(config)

        for (checkbox, option) in [(self.localhostOption, "localhost"), (self.masterOption, "master")]:
            if toBool(config.get("fields", option)):
                checkbox.toggle()


cfgFieldsPaths = {
    "address": ["hostInput", "address"],
    "port": ["hostInput", "port"],
    "localhost": ["localhostOption", "enabled"],
    "playerID": ["playerInput", "playerID"],
    "name": ["playerInput", "name"],
    "master": ["masterOption", "enabled"]
}

cfgGraphicsPaths = {
    "width": ["windowWidth", "text"],
    "height": ["windowHeight", "text"]
}

cfgSections = [
    ("fields", "Champs", FieldsCfg, cfgFieldsPaths),
    ("graphics", "Graphismes", GraphicsCfg, cfgGraphicsPaths)
]


def showConfig(_: EventDispatcher):
    sections = [config.Section(name, title, input(), inputs) for (name, title, input, inputs) in cfgSections]
    ConfigPopup(sections).open()


class HomeCtxActions(AnchorLayout):
    "Actions contextuelles disponibles sur l'écran d'accueil, à savoir uniquement l'accès aux Préférences."

    button = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.initBtn)

    def initBtn(self, _: int):
        self.button.bind(on_press=showConfig)


class HomeInput(TextInput):
    "Zone de saisie dans un formulaire de connexion ou de configuration, conforme au thème de l'appliction."

    defaultBackground = [.05, .05, .05, 1]

    defaultForeground = [1, 1, 1, 1]
    invalidForeground = [1, 0, 0, 1]

    defaultHint = [.7, .7, .7, 1]
    invalidHint = [.5, 0, 0, 1]

    disabledForeground = [.6, .6, .6, 1]
    disabledBackground = [.1, .1, .1, 1]

    def __init__(self, **kwargs):
        super().__init__(background_color=HomeInput.defaultBackground,
                         foreground_color=HomeInput.defaultForeground,
                         hint_text_color=HomeInput.defaultHint,
                         **kwargs)

    def valid(self) -> bool:
        return len(self.text) != 0

    def on_text_validate(self):
        self.parent.dispatch("on_validate")

    def on_is_focusable(self, _: EventDispatcher, focusable: bool):
        if focusable:
            self.foreground_color = HomeInput.defaultForeground
            self.background_color = HomeInput.defaultBackground
        else:
            self.foreground_color = HomeInput.disabledForeground
            self.background_color = HomeInput.disabledBackground


class HomeInputRow(BoxLayout):
    "Ligne de formulaire à hauteur fixe pouvant accueillir plusieurs zones de saisie."

    def __init__(self, **kwargs):
        self.register_event_type("on_validate")
        super().__init__(**kwargs)

    def makeInvalid(self, id: str) -> None:
        target = self.ids[id]

        def disable(_: EventDispatcher, __: str):
            target.foreground_color = HomeInput.defaultForeground
            target.hint_text_color = HomeInput.defaultHint

        target.foreground_color = HomeInput.invalidForeground
        target.hint_text_color = HomeInput.invalidHint

        target.bind(text=disable)

    def fill(self, filled: ConfigParser) -> None:
        for (id, value) in filled["fields"].items():
            if id in self.ids:
                self.ids[id].text = value

    def check(self, id: str) -> bool:
        valid = self.ids[id].valid()
        if not valid:
            self.makeInvalid(id)

        return valid

    def on_validate(self):
        pass


class HomeOption(BoxLayout):
    "Case à cocher accompagner d'un label et liée avec une zone de saisie qu'elle (dés)active pour un insérer un texte prédéfini."

    label = StringProperty()
    input = ObjectProperty()
    field = StringProperty()
    fill = StringProperty()

    ckeckbox = ObjectProperty()
    enabled = BooleanProperty(False)

    def on_enabled(self, _: EventDispatcher, enabled: bool):
        target = self.input.ids[self.field]

        if enabled:
            self.previousText = target.text
            target.is_focusable = False
            target.text = self.fill
        else:
            target.text = self.previousText
            target.is_focusable = True

    def toggle(self) -> None:
        self.checkbox.active = True


class HostInput(HomeInputRow):
    "Une ligne pour saisir un hôte cible sous la forme address:port avec deux zones de saisie."

    address = StringProperty()
    port = StringProperty()


class PlayerInput(HomeInputRow):
    "Une ligne avec deux zones de saisie : une pour l'ID du joueur et l'autre pour son nom."

    playerID = StringProperty()
    name = StringProperty()


class NumericHomeInput(HomeInput):
    "N'autorise que l'entrée de chiffres, est invalide s'il contient autre chose."

    digits = NumericProperty()
    max = NumericProperty(+inf)

    def valid(self) -> bool:
        try:
            return super().valid() and int(self.text) <= self.max
        except ValueError:
            return False

    def insert_text(self, substr: str, from_undo: bool = False):
        if len(self.text) + len(substr) > self.digits:
            return

        for c in substr:
            if c not in "0123456789":
                return

        return super().insert_text(substr, from_undo)


def toBool(str: str) -> bool:
    return str == "True" or str == "1"


class Home(AnchorLayout):
    "Écran d'accueil proposant un formulaire de connexion afin de rejoindre un lobby."

    hostInput = ObjectProperty()
    playerInput = ObjectProperty()
    localhostOption = ObjectProperty()
    masterOption = ObjectProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_login")
        super().__init__(**kwargs)

        config = App.get_running_app().rbocfg
        self.hostInput.fill(config)
        self.playerInput.fill(config)

        for (checkbox, option) in [(self.localhostOption, "localhost"), (self.masterOption, "master")]:
            if toBool(config.get("fields", option)):
                checkbox.toggle()

        for inputRow in [self.hostInput, self.playerInput]:
            inputRow.bind(on_validate=self.login)

    def login(self, _: EventDispatcher = None):
        valid = True

        for (row, inputs) in [(self.hostInput, ["address", "port"]), (self.playerInput, ["playerid", "name"])]:
            for field in inputs:
                valid = row.check(field) and valid

        if valid:
            self.dispatch("on_login",
                          host=(self.hostInput.address, int(self.hostInput.port)),
                          player=(int(self.playerInput.playerID), self.playerInput.name))

    def on_login(self, **_):
        Logger.debug("Home : Connecting...")
