from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.properties import NumericProperty, StringProperty, BooleanProperty


class HomeInput(TextInput):
    pass


class HomeInputRow(BoxLayout):
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
    pass
