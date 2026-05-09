import io
from enum import Enum

import requests
from dustmaker.dfwriter import DFWriter
from dustmaker.replay import Replay


class Score(Enum):
    S = 5
    A = 4
    B = 3
    C = 2
    D = 1
    X = 0


def publish_to_dustkid(
    replay: Replay,
    completion: Score,
    finesse: Score,
    time_ms: int,
    dustkid_id: int,
) -> None:
    """Publish a replay file to dustkid."""

    # Strip the DF_RPL2 (username) header.
    replay.username = b""

    replay_file = io.BytesIO()
    with DFWriter(replay_file) as writer:
        writer.write_replay(replay)
        replay_data = replay_file.getvalue()

    url = "https://dustkid.com/backend8/add_score.php"
    data = {
        "level": replay.level,
        "character": replay.players[0].character.value,
        "score1": completion.value,
        "score2": finesse.value,
        "time": time_ms,
        "user": dustkid_id,
        "replay": replay_data,
        "tool": "dusted",
    }
    response = requests.post(url, data=data)

    response.raise_for_status()

    if response.content == b"FAIL1":
        raise RuntimeError("Dustkid didn't like that")
