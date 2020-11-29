from kivy.app import App
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.uix.floatlayout import FloatLayout
from rboclient.gui import app
from rboclient.gui.lobby import Lobby
from rboclient.gui.session import Session
from rboclient.network.protocol import RboConnectionInterface as RboCI
from twisted.python.failure import Failure


class Game(FloatLayout):
    """Partie (session et lobby) de Rbo.

    Ce widget contient une étape (Step) qui peut changer de la phase lobby à la phase session.\n
    Il émet on_close avec une possible erreur à la fermeture d'une connexion, propre ou non.
    """

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", **kwargs):
        self.register_event_type("on_close")
        super().__init__(**kwargs)

        Logger.debug("Game : Creating game with " + str(members))

        self.rboCI = rboCI
        self.rboCI.bind(on_disconnected=self.close)

        self.listenStepSwitch()

        self.step = None
        self.switch(Lobby(self.rboCI, members))

    def listenStepSwitch(self) -> None:
        self.rboCI.bind(on_session_prepared=self.session,
                        on_result_done=self.lobby,
                        on_result_crash=self.sessionCrash)

    def session(self, _: EventDispatcher = None) -> None:
        # step.members est le widget Members possédant le membre dict members
        self.switch(Session(self.rboCI, dict((id, member.name) for (id, member) in self.step.members.members.items())))

    def lobby(self, _: EventDispatcher = None) -> None:
        self.switch(Lobby(self.rboCI, dict((id, (name, False)) for (id, name) in self.step.members.items()), selfIncluded=True))

    def sessionCrash(self, _: EventDispatcher):
        # Logger l'erreur...
        self.lobby()

    def close(self, _: EventDispatcher, error: Failure):
        self.dispatch("on_close", error=error)

    def on_close(self, error: Failure):
        Logger.info("Game : Closed : " + error.getErrorMessage())

    def switch(self, step):
        App.get_running_app().titleBar.switch(step.titleBarCtx)
        app.setTitle("Rbo - " + type(step).__name__)

        if self.step is not None:
            self.remove_widget(self.step)

        self.step = step
        self.add_widget(self.step)
