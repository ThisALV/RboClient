from kivy.config import Config

from os import path

Config.set("graphics", "borderless", 1)
Config.set("kivy", "exit_on_escape", 0)

Config.set("graphics", "position", "custom")
Config.set("graphics", "top", 1250)
Config.set("graphics", "left", 600)
Config.set("kivy", "log_level", "debug")

cfgFile = "config.ini"

defaultCfg = """
[Host]
address=
port=

[Player]
id=
name=
"""

if not path.isfile(cfgFile):
    with open(cfgFile, mode="w") as config:
        config.write(defaultCfg)

Config.read(cfgFile)

import kivy.resources  # noqa E402
from rboclient.gui.app import ClientApp  # noqa E402

kivy.resources.resource_add_path("rboclient/kv")

ClientApp().run()
