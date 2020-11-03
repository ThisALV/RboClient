from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput


class HomeInput(TextInput):
    pass


class LocalhostOption(BoxLayout):
    pass


class PortInput(HomeInput):
    def insert_text(self, substr: str, from_undo: bool = False):
        if len(self.text) + len(substr) > 5:
            return

        for c in substr:
            if c not in "0123456789":
                return

        return super().insert_text(substr, from_undo)


class Home(AnchorLayout):
    pass
