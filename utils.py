from subprocess import PIPE, Popen

import requests

from dustmaker import read_map
from replay_reader import read_replay
from replay_writer import write_replay


def fetch_replay(replay_id):
    data = {"replay": replay_id}
    response = requests.post("http://54.69.194.244/backend8/get_replay.php", data=data)
    replay = read_replay(response.content)
    return replay

def fetch_level(level_id):
    data = {"id": level_id}
    response = requests.post("http://54.69.194.244/backend8/level.php", data=data)
    level = read_map(response.content)
    return level

def write_replay_to_file(filepath, user, level, character, inputs):
    replay = {
        "username": user,
        "header": {
            "players": 1,
            "characters": [character],
            "levelname": level
        },
        "inputs": [inputs]
    }
    with open(filepath, "wb") as f:
        f.write(write_replay(replay))
