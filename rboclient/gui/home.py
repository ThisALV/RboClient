from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.event import EventDispatcher

from math import inf


class HomeInput(TextInput):
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

    def check(self, id: str) -> bool:
        valid = self.ids[id].valid()
        if not valid:
            self.makeInvalid(id)

        return valid

    def on_validate(self):
        pass


class HomeOption(BoxLayout):
    label = StringProperty()
    input = ObjectProperty()
    field = StringProperty()
    fill = StringProperty()

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


class HostInput(HomeInputRow):
    address = StringProperty()
    port = StringProperty()


class PlayerInput(HomeInputRow):
    playerID = StringProperty()
    name = StringProperty()


class LocalhostOption(BoxLayout):
    pass


class NumericHomeInput(HomeInput):
    digits = NumericProperty()
    max = NumericProperty(+inf)

    def valid(self) -> bool:
        return super().valid() and int(self.text) <= self.max

    def insert_text(self, substr: str, from_undo: bool = False):
        if len(self.text) + len(substr) > self.digits:
            return

        for c in substr:
            if c not in "0123456789":
                return

        return super().insert_text(substr, from_undo)


class Home(AnchorLayout):
    "Conteneur de la page d'accueil."

    hostInput = ObjectProperty()
    playerInput = ObjectProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_login")
        super().__init__(**kwargs)

        for inputRow in [self.hostInput, self.playerInput]:
            inputRow.bind(on_validate=self.login)

    def login(self, _: EventDispatcher = None):
        valid = True

        for (row, inputs) in [(self.hostInput, ["address", "port"]), (self.playerInput, ["playerID", "name"])]:
            for field in inputs:
                valid = row.check(field) and valid

        if valid:
            self.dispatch("on_login",
                          host=(self.hostInput.address, int(self.hostInput.port)),
                          player=(int(self.playerInput.playerID), self.playerInput.name))

    def on_login(self, **_):
        Logger.debug("Home : Connecting...")
