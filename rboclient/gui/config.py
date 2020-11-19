from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.input.motionevent import MotionEvent
from kivy.properties import StringProperty, ReferenceListProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget


def retrieveText(node: Widget, path: "list[str]") -> str:
    if len(path) == 0:
        next = path[0]
        return retrieveText(node.ids[next], path[1:])

    return node.text


class Section:
    def __init__(self, name: str, title: str, input: Widget, inputs: "dict[str, list[str]]"):
        self.name = name
        self.title = title
        self.input = input
        self.inputs = inputs

    def retrieveConfig(self) -> "dict[str, str]":
        config = {}
        for (option, input) in self.inputs.items():
            config[option] = retrieveText(self.input, input)

        return config


class Tab(AnchorLayout):
    title = StringProperty()
    name = StringProperty()

    def __init__(self, name: str, title: str, **kwargs):
        self.register_event_type("on_selected")
        super().__init__(name=name, title=title, **kwargs)

    def on_touch_down(self, touch: MotionEvent):
        if not super().collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.dispatch("on_selected", self.name)
        return True

    def on_selected(self, _: EventDispatcher, name: str):
        pass


class Tabs(StackLayout):
    sections = ReferenceListProperty()

    def __init__(self, **kwargs):
        self.register_event_type("on_enable")
        super().__init__(**kwargs)

    def registerSection(self, section: Section) -> None:
        tab = Tab(section.name, section.title)

        tab.bind(on_selected=self.enable)
        self.add_widget(tab)

    def enable(self, _: EventDispatcher, name: str):
        self.dispatch("on_enabled", name)

    def on_enable(self, _: EventDispatcher, name: str):
        Logger.debug("CfgTabs : Active tab : " + name)


class Pannel(BoxLayout):
    pass


class Content(BoxLayout):
    pass


class ConfigPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(content=Content(), **kwargs)
