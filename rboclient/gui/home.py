from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import ObjectProperty
from kivy.uix.anchorlayout import AnchorLayout
from rboclient.gui import config
from rboclient.gui.config import ConfigPopup, FieldsCfg, GraphicsCfg
from rboclient.misc import toBool

cfgSections = [
    ("fields", "Champs", FieldsCfg),
    ("graphics", "Graphismes", GraphicsCfg)
]


def showConfig(_: EventDispatcher):
    sections = [config.Section(name, title, input(), input.paths) for (name, title, input) in cfgSections]
    ConfigPopup(sections).open()


class HomeCtxActions(AnchorLayout):
    "Actions contextuelles disponibles sur l'écran d'accueil, à savoir uniquement l'accès aux Préférences."

    button = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.initBtn)

    def initBtn(self, _: int):
        self.button.bind(on_press=showConfig)


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
