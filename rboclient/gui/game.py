from rboclient.network.protocol import RboConnectionInterface as RboCI
from rboclient.network.protocol import Mode

from kivy.app import App
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty

from twisted.python.failure import Failure


class Step(EventDispatcher):
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
    "Conteneur de l'écran de la partie."

    membersStr = StringProperty()

    def __init__(self, rboCI: RboCI, members: "dict[int, tuple[str, bool]]", **kwargs):
        self.register_event_type("on_close")
        super().__init__(**kwargs)

        Logger.debug("Game : Creating game with " + str(members))
        self.membersStr = str(members)

        self.rboCI = rboCI

        self.step = Lobby(self.rboCI)
        self.step.bind(on_stop=self.close)

    def close(self, _: EventDispatcher, error: Failure):
        self.dispatch("on_close", error=error)

    def on_close(self, error: Failure):
        Logger.info("Game : Closed : " + error.getErrorMessage())

    def switch(self, step: Step):
        self.remove_widget(self.step)
        self.step = step
        self.add_widget(self.step)

        self.step.bind(on_stop=self.close)
