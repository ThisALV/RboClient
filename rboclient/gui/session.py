from kivy.uix.anchorlayout import AnchorLayout
from rboclient.gui import app
from rboclient.network import protocol
from rboclient.network.protocol import RboConnectionInterface as RboCI


class Session(AnchorLayout):
    def __init__(self, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.rboCI = rboCI
        # Cette variable n'est pas "static" à la classe afin d'éviter les problèmes dus à l'import de son énumération
        self.titleBarCtx = app.TitleBarCtx.SESSION

        self.members = members
