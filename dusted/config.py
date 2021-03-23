import configparser
from pathlib import Path

import appdirs


class Config:
    def __init__(self):
        self.path = Path(appdirs.user_config_dir("dusted")) / "config.ini"
        self.config = configparser.ConfigParser()
        self.read()

    @property
    def dustforce_path(self):
        return self.config["DEFAULT"].get("dustforce_path", r"C:\Program Files (x86)\Steam\steamapps\common\Dustforce")

    @dustforce_path.setter
    def dustforce_path(self, new_path):
        self.config["DEFAULT"]["dustforce_path"] = new_path

    def read(self):
        self.config.read(self.path)

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w+") as file:
            self.config.write(file)

config = Config()
