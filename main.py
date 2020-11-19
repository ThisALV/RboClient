from kivy.config import Config

from os import path
import platform

Config.set("kivy", "exit_on_escape", False)
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
