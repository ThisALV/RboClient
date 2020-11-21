from kivy.logger import Logger
from kivy.event import EventDispatcher
from kivy.clock import Clock
from kivy.input.motionevent import MotionEvent
from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget


def retrieveText(node: Widget, path: "list[str]") -> str:
    if len(path) == 0:
        return node

    next = path[0]
    return retrieveText(getattr(node, next), path[1:])


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

    isSelected = BooleanProperty(False)

    def __init__(self, name: str, title: str, **kwargs):
        self.register_event_type("on_selected")
        super().__init__(name=name, title=title, **kwargs)

    def on_touch_down(self, touch: MotionEvent):
        if not super().collide_point(*touch.pos):
            return super().on_touch_down(touch)

        self.dispatch("on_selected", self.name)
        return True

    def on_selected(self, _: str):
        self.isSelected = True

    def on_isSelected(self, _, selected: bool):
        pass


class Tabs(StackLayout):
    def __init__(self, **kwargs):
        self.register_event_type("on_enable")
        super().__init__(**kwargs)

        self.sections = {}
        self.selected = None

    def registerSection(self, section: Section) -> None:
        tab = Tab(section.name, section.title)
        if len(self.sections) == 0:
            tab.isSelected = True
            self.selected = section.name

        self.sections[section.name] = tab

        tab.bind(on_selected=self.enable)
        self.add_widget(tab)

    def enable(self, _: EventDispatcher, name: str):
        self.sections[self.selected].isSelected = False
        self.selected = name

        self.dispatch("on_enable", name)

    def on_enable(self, name: str):
        Logger.debug("CfgTabs : Active tab : " + name)


class Pannel(BoxLayout):
    tabs = ObjectProperty()
    input = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sections = {}
        Clock.schedule_once(self.listenTabs)

    def listenTabs(self, _: int):
        self.tabs.bind(on_enable=self.enable)

    def initSections(self, sections: "list[Section]") -> None:
        self.current = sections[0].input
        self.input.add_widget(self.current)

        for section in sections:
            self.tabs.registerSection(section)
            self.sections[section.name] = section

    def enable(self, _: EventDispatcher, name: str):
        if self.sections[name].input is self.current:
            return

        self.input.remove_widget(self.current)
        self.current = self.sections[name].input
        self.input.add_widget(self.current)

    def retrieveConfig(self) -> "dict[str, dict[str, str]]":
        config = {}

        for (name, section) in self.sections.items():
            config[name] = section.retrieveConfig()

        return config


class Content(BoxLayout):
    pannel = ObjectProperty()
    save = ObjectProperty()
    cancel = ObjectProperty()

    def __init__(self, sections: "list[Section]", **kwargs):
        self.register_event_type("on_close")
        super().__init__(**kwargs)

        self.pannel.initSections(sections)
        self.cancel.bind(on_press=lambda _: self.dispatch("on_close"))
        self.save.bind(on_press=self.saveCfg)

    def saveCfg(self, _: EventDispatcher):
        cfg = ""

        for (name, section) in self.pannel.retrieveConfig().items():
            cfg += "[{}]\n".format(name)

            for option in section.items():
                cfg += "{}={}\n".format(*option)

            cfg += "\n"

        Logger.debug("Config : Configuration saved : " + cfg)

    def on_close(self):
        pass


class ConfigPopup(Popup):
    def __init__(self, sections: "list[Section]", **kwargs):
        super().__init__(content=Content(sections), **kwargs)
        self.content.bind(on_close=lambda _: self.dismiss())
