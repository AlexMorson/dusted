import io
import logging
import tkinter as tk
import tkinter.messagebox
from enum import Enum

import requests
from dustmaker.dfwriter import DFWriter
from dustmaker.replay import Replay

from dusted.config import config
from dusted.dialog import Dialog

log = logging.getLogger(__name__)


class ValidationError(Enum):
    DUSTKID_ID = "Invalid dustkid ID, must be a non-negative integer."
    TIME = "Invalid time, must be an non-negative integer number of milliseconds."
    COMPLETION = "Invalid completion, must be one of S, A, B, C, D, X."
    FINESSE = "Invalid finesse, must be one of S, A, B, C, D, X."


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


class PublishReplayDialog(Dialog):
    def __init__(self, parent: tk.Misc, replay: Replay) -> None:
        super().__init__(parent)
        self._replay = replay

        dustkid_id_label = tk.Label(self, text="Dustkid ID:")
        dustkid_id_label.grid(row=0, column=0, sticky="e")
        self.dustkid_id_var = tk.StringVar(self)
        dustkid_id_input = tk.Entry(self, textvariable=self.dustkid_id_var)
        dustkid_id_input.grid(row=0, column=1, sticky="ew")

        time_label = tk.Label(self, text="Time (in milliseconds):")
        time_label.grid(row=1, column=0, sticky="e")
        self.time_var = tk.StringVar(self)
        time_input = tk.Entry(self, textvariable=self.time_var)
        time_input.grid(row=1, column=1, sticky="ew")

        completion_label = tk.Label(self, text="Completion:")
        completion_label.grid(row=2, column=0, sticky="e")
        self.completion_var = tk.StringVar(self)
        completion_input = tk.Entry(self, textvariable=self.completion_var)
        completion_input.grid(row=2, column=1, sticky="ew")

        finesse_label = tk.Label(self, text="Finesse:")
        finesse_label.grid(row=3, column=0, sticky="e")
        self.finesse_var = tk.StringVar(self)
        finesse_input = tk.Entry(self, textvariable=self.finesse_var)
        finesse_input.grid(row=3, column=1, sticky="ew")

        button = tk.Button(self, text="Publish", command=self.publish)
        button.grid(row=4, columnspan=2)

        if config.dustkid_id is not None:
            self.dustkid_id_var.set(str(config.dustkid_id))

        self.bind("<Return>", lambda e: self.publish())

    def publish(self) -> None:
        """Validate the form and publish the replay."""

        errors = []

        raw_dustkid_id = self.dustkid_id_var.get()
        try:
            dustkid_id = int(raw_dustkid_id)
        except ValueError:
            errors.append(ValidationError.DUSTKID_ID)
        else:
            if dustkid_id < 0:
                errors.append(ValidationError.DUSTKID_ID)

        raw_time = self.time_var.get()
        try:
            time = int(raw_time)
        except ValueError:
            errors.append(ValidationError.TIME)
        else:
            if time < 0:
                errors.append(ValidationError.TIME)

        raw_completion = self.completion_var.get()
        try:
            completion = Score[raw_completion.upper()]
        except KeyError:
            errors.append(ValidationError.COMPLETION)

        raw_finesse = self.finesse_var.get()
        try:
            finesse = Score[raw_finesse.upper()]
        except KeyError:
            errors.append(ValidationError.FINESSE)

        if errors:
            tkinter.messagebox.showerror(
                message="\n".join(error.value for error in errors)
            )
            return

        try:
            publish_to_dustkid(
                replay=self._replay,
                completion=completion,
                finesse=finesse,
                time_ms=time,
                dustkid_id=dustkid_id,
            )
        except Exception as error:
            log.exception("Publishing replay failed")
            tkinter.messagebox.showerror(message=f"Publishing replay failed:\n{error}")
            return

        if config.dustkid_id != dustkid_id:
            config.dustkid_id = dustkid_id
            config.write()

        tkinter.messagebox.showinfo(message="Replay published successfully!")

        self.destroy()
