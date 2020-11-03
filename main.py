from kivy.config import Config

Config.set("graphics", "borderless", 1)
Config.set("kivy", "exit_on_escape", 0)

Config.set("graphics", "position", "custom")
Config.set("graphics", "top", 1250)
Config.set("graphics", "left", 600)

import kivy.resources  # noqa E402
from rboclient.gui.app import ClientApp  # noqa E402

kivy.resources.resource_add_path("rboclient/kv")

ClientApp().run()
