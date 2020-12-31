from math import inf

from kivy.clock import Clock
from kivy.config import ConfigParser
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ColorProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.logger import Logger
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.stacklayout import StackLayout
from kivy.uix.textinput import TextInput
from rboclient.network.handlerstree import YesNoQuestion


class RboInput(TextInput):
    "Zone de saisie dans un formulaire de connexion ou de configuration, conforme au thème de l'appliction."

    defaultBackground = [.05, .05, .05, 1]

    defaultForeground = [1, 1, 1, 1]
    invalidForeground = [1, 0, 0, 1]

    defaultHint = [.7, .7, .7, 1]
    invalidHint = [.5, 0, 0, 1]

    disabledForeground = [.6, .6, .6, 1]
    disabledBackground = [.1, .1, .1, 1]

    def __init__(self, **kwargs):
        super().__init__(background_color=RboInput.defaultBackground,
                         foreground_color=RboInput.defaultForeground,
                         hint_text_color=RboInput.defaultHint,
                         **kwargs)

    def valid(self) -> bool:
        return len(self.text) != 0

    def on_is_focusable(self, _: EventDispatcher, focusable: bool):
        if focusable:
            self.foreground_color = RboInput.defaultForeground
            self.background_color = RboInput.defaultBackground
        else:
            self.foreground_color = RboInput.disabledForeground
            self.background_color = RboInput.disabledBackground


class RboInputRow(BoxLayout):
    """Ligne de formulaire à hauteur fixe pouvant accueillir plusieurs zones de saisie

    Un appui sur Entrée lors du focus d'un des TextInput renseignés par la classe fille émet l'évènement on_validate.
    """

    inputs = ListProperty([])

    def __init__(self, **kwargs):
        self.register_event_type("on_validate")
        super().__init__(**kwargs)

        Clock.schedule_once(self.initValidateListening)

    def initValidateListening(self, _: int) -> None:
        for input in self.inputs:
            getattr(self, input).bind(on_text_validate=lambda _: self.dispatch("on_validate"))

    def makeInvalid(self, id: str) -> None:
        target = self.ids[id]

        def disable(_: EventDispatcher, __: str):
            target.foreground_color = RboInput.defaultForeground
            target.hint_text_color = RboInput.defaultHint

        target.foreground_color = RboInput.invalidForeground
        target.hint_text_color = RboInput.invalidHint

        target.bind(text=disable)

    def fill(self, filled: ConfigParser) -> None:
        for (id, value) in filled["fields"].items():
            if id in self.ids:
                self.ids[id].text = value

    def check(self, id: str) -> bool:
        valid = self.ids[id].valid()
        if not valid:
            self.makeInvalid(id)

        return valid

    def on_validate(self):
        pass


class RboOption(BoxLayout):
    "Case à cocher accompagnée d'un label."

    enabled = BooleanProperty(False)
    label = StringProperty()
    group = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.initGroup)

    def initGroup(self, _: int):
        if self.group is not None:
            self.checkbox.group = self.group

    def toggle(self) -> None:
        self.checkbox.active = True


class RboFillOption(RboOption):
    "Case à cocher accompagnée d'un label et liée avec une zone de saisie qu'elle (dés)active pour un insérer un texte prédéfini."

    input = ObjectProperty()
    field = StringProperty()
    fill = StringProperty()

    ckeckbox = ObjectProperty()

    def on_enabled(self, _: EventDispatcher, enabled: bool):
        target = self.input.ids[self.field]

        if enabled:
            self.previousText = target.text
            target.is_focusable = False
            target.text = self.fill
        else:
            target.text = self.previousText
            target.is_focusable = True


class HostInput(RboInputRow):
    "Une ligne pour saisir un hôte cible sous la forme address:port avec deux zones de saisie."

    addressInput = ObjectProperty()
    portInput = ObjectProperty()
    inputs = ListProperty(["addressInput", "portInput"])

    address = StringProperty()
    port = StringProperty()


class PlayerInput(RboInputRow):
    "Une ligne avec deux zones de saisie : une pour l'ID du joueur et l'autre pour son nom."

    idInput = ObjectProperty()
    nameInput = ObjectProperty()
    inputs = ListProperty(["idInput", "nameInput"])

    playerID = StringProperty()
    name = StringProperty()


class NumericRboInput(RboInput):
    "N'autorise que l'entrée de chiffres, est invalide s'il contient autre chose."

    digits = NumericProperty(+inf)
    min = NumericProperty(0)
    max = NumericProperty(+inf)

    def __init__(self, min: int = None, max: int = None, **kwargs):
        super().__init__(**kwargs)

        if min is not None:
            self.min = min
        if max is not None:
            self.max = max

    def valid(self) -> bool:
        try:
            numericValue = int(self.text)
            return super().valid() and numericValue <= self.max and numericValue >= self.min
        except ValueError:
            return False

    def insert_text(self, substr: str, from_undo: bool = False):
        if len(self.text) + len(substr) > self.digits:
            return

        for c in substr:
            if c not in "0123456789":
                return

        return super().insert_text(substr, from_undo)


class ScrollableStack(ScrollView):
    "Classe mère pour créer un StackLayout (pile d'éléments) qui soit scrollable verticalement."

    background = ColorProperty([0, 0, 0])
    content = ObjectProperty()

    def __init__(self, bg: "list[int]" = background.defaultvalue, **kwargs):
        super().__init__(background=bg, **kwargs)

    def on_background(self, _: EventDispatcher, bg):
        pass


class Pair(StackLayout):
    "Paire clé/valeur d'un tableau"

    key = StringProperty()
    value = NumericProperty()
    color = ColorProperty([1, 1, 1])

    def __init__(self, key: str, value: int, **kwargs):
        super().__init__(key=key, value=value, **kwargs)


class DictionnaryView(ScrollableStack):
    """Classe mère pour afficher un tableau scrollable verticalement de paires sous la forme "<clé> : <valeur>" avec deux colonnes.

    La méthode refresh() permet de mettre à jour les données affichées.\n
    Si une paire clé/valeur est présente, alors la valeur sera mise à jour en fonction de dict passé en argument,
    sinon une nouvelle paire clé/valeur sera ajoutée dans la tableau.\n
    Pour supprimer une paire du tableau, il faut passer la valeur None dans la paire clé/valeur correspondante en argument.
    """

    foreground = ColorProperty([1, 1, 1])

    def __init__(self, bg: "list[int]" = ScrollableStack.background.defaultvalue, **kwargs):
        super().__init__(bg, **kwargs)

        self.pairs = {}
        Clock.schedule_once(self.initContent)

    def initContent(self, _: int):
        self.content.padding = 15
        self.content.spacing = 5

    def refresh(self, pairs: "dict[str, int]") -> None:
        for (key, value) in pairs.items():
            hidePair = value is None

            if key in self.pairs:
                if hidePair:
                    self.content.remove_widget(self.pairs[key])
                    self.pairs.pop(key)
                else:
                    self.pairs[key].value = value
            elif not hidePair:
                self.pairs[key] = Pair(key, value)
                self.bind(foreground=self.pairs[key].setter("color"))
                self.content.add_widget(self.pairs[key])


class InputContent(BoxLayout):
    input = ObjectProperty()
    form = ObjectProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_submit")
        super().__init__(**kwargs)

        self.form.add_widget(self.input)

    def on_submit(self):
        pass


class InputPopup(Popup):
    """Classe mère pour les popups voulant afficher un champ de saisie et un bouton valider afin d'émettre on_validate avec la valeur saisie value.

    La propriété inputType désigne le type qui sera utilisé pour construire le widget du champ de saisie.\n
    La propriété value doit être définie par la classe fille (l'implémentation).
    """

    title = StringProperty("InputPopup")
    inputType = ObjectProperty()
    value = ObjectProperty()

    def __init__(self, *inputArgs, **kwargs):
        self.register_event_type("on_validate")
        super().__init__(**kwargs)

        self.content = InputContent(input=self.inputType(*inputArgs))
        self.content.bind(on_submit=lambda _: self.dispatch("on_validate", self.value))

    def on_validate(self, value: str):
        Logger.debug("InputPopup : Input value \"{}\"".format(value))
        self.dismiss()


class CheckpointInput(RboInput):
    pass


class TextInputPopup(InputPopup):
    "Cette popup affiche une zone de saisie (de texte)."

    title = StringProperty("Choisir un checkpoint")
    value = ObjectProperty("")
    inputType = ObjectProperty(CheckpointInput)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.content.input.bind(text=self.setter("value"))


class YesNoBtn(AnchorLayout):
    yes = BooleanProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_click")
        super().__init__(**kwargs)

    def on_click(self):
        pass


class YesNoContent(BoxLayout):
    "Initialise le contenu d'une YesNoPopup et émet on_choose lorsque le choix est fait."

    questions = {
        YesNoQuestion.MissingParticipants: "Manque-t-il des participants ?",
        YesNoQuestion.RetryCheckpoint: "Choisir un autre checkpoint ?",
        YesNoQuestion.KickUnknownPlayers: "Déconnecter les joueurs en trop ?"
    }

    question = StringProperty()
    yes = ObjectProperty()
    no = ObjectProperty()

    def __init__(self, question, **kwargs):
        self.register_event_type("on_choose")
        super().__init__(**kwargs)

        self.yes.bind(on_click=lambda _: self.dispatch("on_choose", True))
        self.no.bind(on_click=lambda _: self.dispatch("on_choose", False))

        self.question = YesNoContent.questions[question] if type(question) == YesNoQuestion else question

    def on_choose(self, chosen: bool):
        pass


class YesNoPopup(Popup):
    """Cette popup permet de répondre Oui ou Non à une question posée.

    L'évènement on_reply est émit lorsque le choix a été fait.\n
    Si question passé au constructeur est une YesNoQuestion, alors le titre et la question correspondante sera affichée.\n
    Sinon, s'il s'agit d'une str, alors le titre sera "Demande" et la question affichée sera celle passée en argument.
    """

    questions = {
        YesNoQuestion.MissingParticipants: "Participants",
        YesNoQuestion.KickUnknownPlayers: "Participants",
        YesNoQuestion.RetryCheckpoint: "Checkpoint"
    }

    def __init__(self, question, **kwargs):
        self.register_event_type("on_reply")
        super().__init__(title=YesNoPopup.questions[question] if type(question) == YesNoQuestion else "Demande", **kwargs)

        self.content = YesNoContent(question)
        self.content.bind(on_choose=lambda _, chosen: self.dispatch("on_reply", chosen))

    def on_reply(self, reply: bool):
        Logger.debug("YesNoPopup : Chosen reply {}".format(reply))
        self.dismiss()


class GameCtxAction(AnchorLayout):
    """Widget composant une GameCtxActions.

    Il centre un RboBtn qu'il peut activé ou désactivé, et il retransmet les cliques sur ce bouton via on_release.
    """

    button = ObjectProperty()
    text = StringProperty()
    enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.register_event_type("on_release")
        super().__init__(**kwargs)

        Clock.schedule_once(self.initReleasedHandler)

    def initReleasedHandler(self, _: int):
        self.button.bind(on_release=lambda _: self.dispatch("on_release"))

    def on_release(self):
        pass


class CtxActionDefaultHandler:
    def __init__(self, action: str):
        self.action = action

    def __call__(self):
        Logger.debug("TitleBar : {} requested".format(self.action))


class GameCtxActions(BoxLayout):
    """Classe mère pour les menus d'actions contextuelles pendant une partie.

    Les implémentations de cette classe doivent définir actions, une liste de noms d'actions contextuelles.\n
    Chaque nom associe à un bouton d'une GameCtxAction (AnchorLayout) enfant du même nom un event respectif à émettre lorsque celui-ci est cliqué.
    """

    actions = []

    def __init__(self, **kwargs):
        for event in self.actions:  # Les enregistrements des types d'events doivent se faire avant l'appel au constructeur...
            fullName = "on_" + event

            setattr(self, fullName, CtxActionDefaultHandler(event))
            self.register_event_type(fullName)

        super().__init__(**kwargs)

        class ReleasedHandlerInitializer:
            ctx = self

            def __init__(self, action: str):
                self.action = action

            def __call__(self, _: int):
                self.ctx.ids[self.action].bind(on_release=lambda _: self.ctx.dispatch("on_" + self.action))

        for action in self.actions:  # ...par conséquent, il y a une deuxième boucle après cet appel.
            Clock.schedule_once(ReleasedHandlerInitializer(action))
