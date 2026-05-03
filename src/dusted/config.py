from __future__ import annotations

import configparser
import dataclasses
from dataclasses import dataclass
from pathlib import Path

import platformdirs

CONFIG_PATH = Path(platformdirs.user_config_dir("dusted")) / "config.ini"


@dataclass
class Config:
    dustforce_path: str = r"C:\Program Files (x86)\Steam\steamapps\common\Dustforce"
    show_level: bool = True
    window_geometry: str = ""
    dustkid_id: int | None = None

    @classmethod
    def read(cls) -> Config:
        """Read the config file."""

        parser = configparser.RawConfigParser(defaults=cls._defaults())
        parser.read(CONFIG_PATH)

        return cls(
            dustforce_path=parser.get("DEFAULT", "dustforce_path"),
            show_level=parser.getboolean("DEFAULT", "show_level"),
            window_geometry=parser.get("DEFAULT", "window_geometry"),
            dustkid_id=parser.getint("DEFAULT", "dustkid_id", fallback=None),
        )

    def write(self) -> None:
        """Write the config file."""

        parser = configparser.RawConfigParser(defaults=self._defaults())
        parser.read_dict(
            {
                "DEFAULT": {
                    key: self._stringify_value(value)
                    for key, value in dataclasses.asdict(self).items()
                    if value is not None
                }
            }
        )

        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w+") as file:
            parser.write(file)

    @classmethod
    def _defaults(cls) -> dict[str, str]:
        """Return the default values for the fields."""

        return {
            field.name: cls._stringify_value(field.default)
            for field in dataclasses.fields(cls)
            if field.default is not dataclasses.MISSING and field.default is not None
        }

    @staticmethod
    def _stringify_value(value: str | bool | int) -> str:
        """Convert a value into a string that the parser can deal with."""

        if isinstance(value, bool):
            if value:
                return "true"
            else:
                return "false"

        if isinstance(value, int):
            return str(value)

        return value


config = Config.read()
