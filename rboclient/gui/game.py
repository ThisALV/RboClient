from rboclient.network.protocol import RboConnectionInterface as RboCI

from kivy.app import App
from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty


class IGError:
    def __init__(self, short: str, long: str):
        self.short = short
        self.long = long


class Step(EventDispatcher):
    def __init__(self, **kwargs):
        self.register_event_type("on_stop")
        super().__init__(**kwargs)

    def stop(self, error: IGError = None):
        self.dispatch("on_stop", error=error)

    def on_stop(self):
        Logger.debug("Stop requested.")


class Lobby(Step, FloatLayout):
    "Écran du lobby d'une session."

    def __init__(self, rboCI: RboCI, **kwargs):
        super().__init__(**kwargs)
        self.rboCI = rboCI

        App.get_running_app().titleBar.bind(on_disconnect=self.disconnect)

    def ready(self):
        self.rboCI.ready()

    def disconnect(self):
        self.rboCI.disconnect()
        self.stop()


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

    def close(self, error: IGError):
        self.dispatch("on_close", error=error)

    def on_close(self):
        Logger.info("Game : Closed.")

    def switch(self, step: Step):
        self.remove_widget(self.step)
        self.step = step
        self.add_widget(self.step)

        self.step.bind(on_stop=self.close)
