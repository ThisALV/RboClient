from kivy.config import Config, ConfigParser

from os import path

Config.set("graphics", "borderless", 1)
Config.set("kivy", "exit_on_escape", 0)

Config.set("kivy", "log_level", "debug")

cfgFile = "config.ini"

defaultCfg = """
[fields]
address=
port=
playerID=
name=

[graphics]
width=900
height=650

"""

if not path.isfile(cfgFile):
    with open(cfgFile, mode="w") as config:
        config.write(defaultCfg)

rboCfg = ConfigParser(name="rboclient")

for section in ["fields", "graphics"]:
    rboCfg.add_section(section)

rboCfg.read(cfgFile)

import kivy.resources  # noqa E402
from rboclient.gui.app import ClientApp  # noqa E402

kivy.resources.resource_add_path("rboclient/kv")

ClientApp(rboCfg).run()
