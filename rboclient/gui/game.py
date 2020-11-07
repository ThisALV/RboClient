from rboclient.network.protocol import RboConnectionInterface as RboCI

from kivy.uix.floatlayout import FloatLayout


class Lobby(FloatLayout):
    pass


class Game(FloatLayout):
    def __init__(self, rboCI: RboCI, **kwargs):
        super().__init__(**kwargs)
        self.step = Lobby()
        self.rboCI = rboCI
