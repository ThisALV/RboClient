from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.logger import Logger
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from rboclient.gui.widgets import *
from rboclient.misc import toBool


def retrieveText(node: Widget, path: "list[str]") -> str:
    if len(path) == 0:
        return node

    next = path[0]
    return retrieveText(getattr(node, next), path[1:])


class Section:
    """Section de configuration.

    Chaque section est identifiée par un nom, et possède pour l'affichage un titre.\n
    Une propriété input correspond au widget qui est le panneau de configuration des options de cette section.\n
    La valeur de chaque option au moment de l'enregistrement est déterminé par un "chemin de propriétés" (inputs).
    Ex : ["foo", "bar"] -> la propriété bar de la propriété foo de self.input.
    """

    def __init__(self, name: str, title: str, input: Widget, inputs: "dict[str, list[str]]"):
        self.name = name
        self.title = title
        self.input = input
        self.inputs = inputs

    def retrieveConfig(self) -> "dict[str, str]":
        config = {}
        for (option, input) in self.inputs.items():
            config[option] = retrieveText(self.input, input)

        return config


class Tab(AnchorLayout):
    "Onglet contenant le titre de la section. Il signale qu'il a été sélectionné avec son identifiant lorsqu'il est cliqué."

    title = StringProperty()
    name = StringProperty()

    isSelected = BooleanProperty(False)

    def __init__(self, name: str, title: str, **kwargs):
        self.register_event_type("on_selected")
        super().__init__(name=name, title=title, **kwargs)

    def on_touch_down(self, touch: MotionEvent):
        if not super().collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.dispatch("on_selected", self.name)
        return True

    def on_selected(self, _: str):
        self.isSelected = True

    def on_isSelected(self, _, selected: bool):
        pass


class Tabs(StackLayout):
    "Ensemble des onglets de chaque section de configuration, retransmet le signal des onglets sélectionnés."

    def __init__(self, **kwargs):
        self.register_event_type("on_enable")
        super().__init__(**kwargs)

        self.sections = {}
        self.selected = None

    def registerSection(self, section: Section) -> None:
        tab = Tab(section.name, section.title)
        if len(self.sections) == 0:
            tab.isSelected = True
            self.selected = section.name

        self.sections[section.name] = tab

        tab.bind(on_selected=self.enable)
        self.add_widget(tab)

    def enable(self, _: EventDispatcher, name: str):
        self.sections[self.selected].isSelected = False
        self.selected = name

        self.dispatch("on_enable", name)

    def on_enable(self, name: str):
        Logger.debug("CfgTabs : Active tab : " + name)


class Pannel(BoxLayout):
    """Panneau de configuration principal de la popup de config.

    Ce panneau écoute les sélections d'onglets en vu de changement le panneau de configuration de la section actuelle.\n
    Il reçoit la liste des sections seulement près l'initialisation dans le but de pouvoir est appelé dans un fichier .kv directement.\n
    Il appelle également chaque onglet à lui retourner les options de sa section de configuration, afin de rendre la configuration générale.
    """

    tabs = ObjectProperty()
    input = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sections = {}
        Clock.schedule_once(self.listenTabs)

    def listenTabs(self, _: int):
        self.tabs.bind(on_enable=self.enable)

    def initSections(self, sections: "list[Section]") -> None:
        self.current = sections[0].input
        self.input.add_widget(self.current)

        for section in sections:
            self.tabs.registerSection(section)
            self.sections[section.name] = section

    def enable(self, _: EventDispatcher, name: str):
        if self.sections[name].input is self.current:
            return

        self.input.remove_widget(self.current)
        self.current = self.sections[name].input
        self.input.add_widget(self.current)

    def retrieveConfig(self) -> "dict[str, dict[str, str]]":
        config = {}

        for (name, section) in self.sections.items():
            config[name] = section.retrieveConfig()

        return config


class SaveCfgError(RuntimeError):
    "Détermine une erreur quelconque lors de la sauvegarde de la configuration."

    def __init__(self, msg: str):
        super().__init__(msg)


class Content(BoxLayout):
    """Conteneur principal (racine) de la popup de configuration.

    Contient le panneau de configuration principal (avec les onglets des sections).\n
    Possède aussi deux boutons pour annuler tout changement ou au contraire les sauvegarder directement depuis le ConfigParser de ClientApp,
    qui est réservé aux propriétés de RboClient (rbocfg).\n
    Les deux boutons signalent une fermeture de la popup.
    """

    pannel = ObjectProperty()
    save = ObjectProperty()
    cancel = ObjectProperty()

    def __init__(self, sections: "list[Section]", **kwargs):
        self.register_event_type("on_close")
        super().__init__(**kwargs)

        self.pannel.initSections(sections)
        self.cancel.bind(on_press=lambda _: self.dispatch("on_close"))
        self.save.bind(on_press=self.saveCfg)

    def saveCfg(self, _: EventDispatcher):
        config = App.get_running_app().rbocfg

        for (name, section) in self.pannel.retrieveConfig().items():
            for (option, value) in section.items():
                config.set(name, option, value)

        self.dispatch("on_close")

        if not config.write():
            raise SaveCfgError("Configuration not saved.")

    def on_close(self):
        pass


class ConfigPopup(Popup):
    "Popup affichant le panneau de configuration et les boutons d'actions, elle réagit à ceux-ci pour se fermer."

    def __init__(self, sections: "list[Section]", **kwargs):
        super().__init__(content=Content(sections), **kwargs)
        self.content.bind(on_close=lambda _: self.dismiss())


class FieldsCfg(BoxLayout):
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


class GraphicsCfg(BoxLayout):
    "Panneau de configuration pour renseigner des paramètres graphiques comme la résolution de la fenêtre."

    paths = {
        "width": ["windowWidth", "text"],
        "height": ["windowHeight", "text"],
        "maximized": ["maximizedOption", "enabled"]
    }

    windowWidth = ObjectProperty()
    windowHeight = ObjectProperty()
    maximizedOption = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        config = App.get_running_app().rbocfg

        self.windowWidth.text = config.get("graphics", "width")
        self.windowHeight.text = config.get("graphics", "height")

        if toBool(config.get("graphics", "maximized")):
            self.maximizedOption.toggle()
