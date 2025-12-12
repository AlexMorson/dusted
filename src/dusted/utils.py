import io
from pathlib import Path

import requests
from dustmaker.dfreader import DFReader
from dustmaker.dfwriter import DFWriter
from dustmaker.level import Level
from dustmaker.replay import Replay

from dusted.config import config


def load_replay_from_dustkid(replay_id: str) -> Replay:
    data = {"replay": replay_id}
    response = requests.post("https://dustkid.com/backend8/get_replay.php", data=data)
    if not response.ok:
        raise RuntimeError("Could not fetch replay from dustkid")
    replay = DFReader(io.BytesIO(response.content)).read_replay()
    return replay


def load_level(level_id: str) -> Level:
    level = load_level_from_file(level_id)
    if level is None:
        level = load_level_from_dustkid(level_id)
    return level


def load_level_from_file(level_id: str) -> Level | None:
    for path in ("content/levels2", "content/levels3", "user/levels", "user/level_src"):
        level_path = Path(config.dustforce_path) / path / level_id
        try:
            with level_path.open("rb") as file:
                return DFReader(file).read_level()
        except FileNotFoundError:
            pass
    return None


def load_level_from_dustkid(level_id: str) -> Level:
    data = {"id": level_id}
    response = requests.post("https://dustkid.com/backend8/level.php", data=data)
    if not response.ok:
        raise RuntimeError("Could not fetch level from dustkid")
    return DFReader(io.BytesIO(response.content)).read_level()


def load_replay_from_file(filepath: str) -> Replay:
    with open(filepath, "rb") as file:
        return DFReader(file).read_replay()


def write_replay_to_file(filepath: str, replay: Replay):
    with open(filepath, "wb") as file:
        DFWriter(file).write_replay(replay)


def modifier_held(key_state: int) -> bool:
    """Check if Shift or Control are held."""
    return (key_state & 0x1) != 0 or (key_state & 0x4) != 0
