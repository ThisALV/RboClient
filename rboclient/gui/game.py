from kivy.app import App
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.uix.floatlayout import FloatLayout
from rboclient.gui import app
from rboclient.network.protocol import RboConnectionInterface as RboCI
from twisted.python.failure import Failure


class Step:
    """Classe mère pour les étapes d'une partie (lobby et session)

    La méthode init() permet d'initialiser l'interface RboCI et le contexte TitleBar sans forcer une signature pour l'héritage multiple.\n
    listen() est appelée par la classe fille pour stocker et binder tous les handlers fournis.\n
    stopListen() est appelée au niveau de l'interface afin d'unbinder tous les handlers gardés en mémoire avec listen().
    """

    def init(self, rboCI: RboCI, titleBarCtx: "app.TitleBarCtx") -> None:
        self.rboCI = rboCI
        self.titleBarCtx = titleBarCtx

        self.handlers = {}

    def listen(self, **kwargs):
        self.rboCI.bind(**kwargs)
        self.handlers = kwargs

    def stopListen(self):
        self.rboCI.unbind(**self.handlers)


# Pour éviter les problèmes de partals imports
from rboclient.gui.lobby import Lobby  # noqa E402
from rboclient.gui.session import Session  # noqa E402


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
        class PreparationErrorHandler:
            ctx = self

            def __init__(self, name: str):
                self.name = name

            def __call__(self, _: EventDispatcher):
                self.ctx.sessionPreparationError(self.name)

        self.rboCI.bind(on_session_prepared=lambda _: self.session(),
                        on_result_done=lambda _: self.lobby(),
                        on_result_crash=self.sessionCrash,
                        on_result_checkpoint_error=PreparationErrorHandler("Impossible de charge le checkpoint"),
                        on_result_less_members=PreparationErrorHandler("Des joueurs sont manquants"),
                        on_result_unknown_players=PreparationErrorHandler("Des joueurs sont en trop"))

    def session(self) -> None:
        # step.members est le widget Members possédant le membre dict members
        self.switch(Session(self.rboCI, dict((id, member.name) for (id, member) in self.step.members.members.items())))

    def lobby(self, preparing: bool = False) -> None:
        self.switch(Lobby(self.rboCI, dict((id, (name, False)) for (id, name) in self.step.members.items()), selfIncluded=True, preparing=preparing))

    def sessionCrash(self, _: EventDispatcher):
        self.lobby()
        self.step.logs.log("[b]La session a crashé.[/b]")

    def sessionPreparationError(self, error: str):
        self.lobby(preparing=True)
        self.step.logs.log("La préparation de la session a échouée : [b]{}[/b]".format(error))

    def close(self, _: EventDispatcher, error: Failure):
        self.dispatch("on_close", error=error)

    def on_close(self, error: Failure):
        Logger.info("Game : Closed : " + error.getErrorMessage())

    def switch(self, step: Step):
        App.get_running_app().titleBar.switch(step.titleBarCtx)
        app.setTitle("Rbo - " + type(step).__name__)

        if self.step is not None:
            self.remove_widget(self.step)
            self.step.stopListen()

        self.step = step
        self.add_widget(self.step)
