from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from rboclient.misc import toBool


class Fields(BoxLayout):
    "Panneau de configuration pour renseigner les valeurs par défauts des zones de saisie de la page d'accueil."

    paths = {
        "address": ["hostInput", "address"],
        "port": ["hostInput", "port"],
        "localhost": ["localhostOption", "enabled"],
        "playerID": ["playerInput", "playerID"],
        "name": ["playerInput", "name"],
        "master": ["masterOption", "enabled"]
    }

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


class Graphics(BoxLayout):
    "Panneau de configuration pour renseigner des paramètres graphiques comme la résolution de la fenêtre."

    paths = {
        "width": ["windowWidth", "text"],
        "height": ["windowHeight", "text"],
        "fullscreen": ["fullscreenOption", "enabled"]
    }

    windowWidth = ObjectProperty()
    windowHeight = ObjectProperty()
    fullscreenOption = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config = App.get_running_app().rbocfg

        self.windowWidth.text = config.get("graphics", "width")
        self.windowHeight.text = config.get("graphics", "height")

        if toBool(config.get("graphics", "fullscreen")):
            self.fullscreenOption.toggle()
