from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode

from kivy.app import App
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty

from twisted.python.failure import Failure


class Step(EventDispatcher):
    """Étape d'une partie (lobby ou session).

    Émet un event on_stop pour signaler un retour à l'accueil, notamment lorsque le protocol de connexion émet on_disconnect.
    """

    def __init__(self, **kwargs):
        self.register_event_type("on_stop")
        super().__init__(**kwargs)

    def link(self, rboCI: RboCI) -> None:
        rboCI.bind(on_disconnected=self.stop)

    def stop(self, _: EventDispatcher = None, error: Failure = None):
        self.dispatch("on_stop", error=error)

    def on_stop(self, error: Failure):
        Logger.debug("Game : Stop requested : " + error.getErrorMessage())


# Pour car Lobby doit pouvoir hériter de Step
from rboclient.gui.lobby import Lobby  # noqa E402


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
        self.step = None
        self.switch(Lobby(self.rboCI, members))

    def close(self, _: EventDispatcher, error: Failure):
        self.dispatch("on_close", error=error)

    def on_close(self, error: Failure):
        Logger.info("Game : Closed : " + error.getErrorMessage())

    def switch(self, step: Step):
        if self.step is not None:
            self.remove_widget(self.step)

        self.step = step
        self.add_widget(self.step)

        self.step.bind(on_stop=self.close)
