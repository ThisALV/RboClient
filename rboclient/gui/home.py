from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.event import EventDispatcher
from kivy.logger import Logger


class HomeInput(TextInput):
    def on_text_validate(self):
        self.parent.dispatch("on_validate")


class HomeInputRow(BoxLayout):
    def __init__(self, **kwargs):
        self.register_event_type("on_validate")
        super().__init__(**kwargs)

    def on_validate(self):
        pass


class HomeOption(BoxLayout):
    label = StringProperty()
    enabled = BooleanProperty(False)


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

    def insert_text(self, substr: str, from_undo: bool = False):
        if len(self.text) + len(substr) > self.digits:
            return

        for c in substr:
            if c not in "0123456789":
                return

        return super().insert_text(substr, from_undo)


class Home(AnchorLayout):
    hostInput = ObjectProperty()
    playerInput = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        for inputRow in [self.hostInput, self.playerInput]:
            inputRow.bind(on_validate=self.login)

    def login(self, _: EventDispatcher = None):
        Logger.debug("Home : Connexion...")
