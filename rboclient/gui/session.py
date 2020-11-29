from kivy.uix.anchorlayout import AnchorLayout
from rboclient.gui import app
from rboclient.gui.game import Step
from rboclient.network import protocol
from rboclient.network.protocol import RboConnectionInterface as RboCI


class Session(Step, AnchorLayout):
    def __init__(self, rboCI: RboCI, members: "dict[int, str]", **kwargs):
        super().__init__(**kwargs)
        self.init(rboCI, app.TitleBarCtx.SESSION)

        self.members = members
