from rboclient.network.protocol import RboConnectionInterface as RboCI

from kivy.uix.floatlayout import FloatLayout


class Lobby(FloatLayout):
    pass


class Game(FloatLayout):
    "Conteneur de l'écran de la partie."

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", **kwargs):
        super().__init__(**kwargs)
        self.step = Lobby()
        self.rboCI = rboCI
