import configparser
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import appdirs


class _ConfigOption(NamedTuple):
    name: str
    default: str | bool


class ConfigOption(Enum):
    DUSTFORCE_PATH = _ConfigOption("dustforce_path", r"C:\Program Files (x86)\Steam\steamapps\common\Dustforce")

    @classmethod
    def defaults(cls):
        return {
            option.value.name: option.value.default
            for option in cls
        }



class Config:
    def __init__(self):
        self.path = Path(appdirs.user_config_dir("dusted")) / "config.ini"
        self.config = configparser.ConfigParser(ConfigOption.defaults())
        self.read()

    def get(self, option: ConfigOption):
        name = option.value.name
        if isinstance(option.value.default, bool):
            return self.config["DEFAULT"].getboolean(name)
        return self.config["DEFAULT"].get(name)

    def set(self, option: ConfigOption, value: str | bool):
        if isinstance(value, bool):
            real_value = "true" if value else "false"
        else:
            real_value = value
        self.config["DEFAULT"][option.value.name] = real_value

    def read(self):
        self.config.read(self.path)

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w+") as file:
            self.config.write(file)


config = Config()
