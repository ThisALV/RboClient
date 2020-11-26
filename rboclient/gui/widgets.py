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

    label = StringProperty()

    def toggle(self) -> None:
        self.checkbox.active = True


class RboFillOption(RboOption):
    "Case à cocher accompagnée d'un label et liée avec une zone de saisie qu'elle (dés)active pour un insérer un texte prédéfini."

    input = ObjectProperty()
    field = StringProperty()
    fill = StringProperty()

    ckeckbox = ObjectProperty()
    enabled = BooleanProperty(False)

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

    digits = NumericProperty()
    max = NumericProperty(+inf)

    def valid(self) -> bool:
        try:
            return super().valid() and int(self.text) <= self.max
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
    value = StringProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_validate")
        super().__init__(title=self.title, **kwargs)

        self.content = InputContent(input=self.inputType(), **kwargs)
        self.content.bind(on_submit=lambda _: self.dispatch("on_validate", self.value))

    def on_validate(self, value: str):
        Logger.debug("TxtInput : Input value \"{}\"".format(value))
        self.dismiss()


class CheckpointInput(RboInput):
    pass


class TextInputPopup(InputPopup):
    "Cette popup affiche une zone de saisie et propose une méthode show() qui appelle open() et retourne le texte saisi."

    title = StringProperty("Choisir un checkpoint")
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
    questions = {
        YesNoQuestion.MissingParticipants: "Manque-t-il des participants ?",
        YesNoQuestion.RetryCheckpoint: "Choisir un autre checkpoint ?",
        YesNoQuestion.KickUnknownPlayers: "Déconnecter les joueurs en trop ?"
    }

    question = StringProperty()
    yes = ObjectProperty()
    no = ObjectProperty()

    def __init__(self, question: YesNoQuestion, **kwargs):
        self.register_event_type("on_choose")
        super().__init__(**kwargs)

        self.yes.bind(on_click=lambda _: self.dispatch("on_choose", True))
        self.no.bind(on_click=lambda _: self.dispatch("on_choose", False))

        self.question = YesNoContent.questions[question]

    def on_choose(self, chosen: bool):
        pass


class YesNoPopup(Popup):
    "Cette popup permet de répondre Oui ou Non à une question posée."

    questions = {
        YesNoQuestion.MissingParticipants: "Participants",
        YesNoQuestion.KickUnknownPlayers: "Participants",
        YesNoQuestion.RetryCheckpoint: "Checkpoint"
    }

    def __init__(self, question: YesNoQuestion, **kwargs):
        self.register_event_type("on_reply")
        super().__init__(title=YesNoPopup.questions[question], **kwargs)

        self.content = YesNoContent(question)
        self.content.bind(on_choose=lambda _, chosen: self.dispatch("on_reply", chosen))

    def on_reply(self, reply: bool):
        Logger.debug("YesNoPopup : Chosen reply {}".format(reply))
        self.dismiss()
