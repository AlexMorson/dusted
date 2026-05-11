from dataclasses import dataclass

from dustmaker.replay import Character

from dusted.config import config
from dusted.models.cursor import Cursor
from dusted.models.inputs import Inputs, Intents
from dusted.models.inputs_grid import InputsGrid
from dusted.models.replay_diagnostics import ReplayDiagnostics
from dusted.models.undo_stack import UndoStack
from dusted.models.value import Value


@dataclass(frozen=True)
class AppState:
    level: Value[str]
    character: Value[Character]
    inputs: Inputs
    diagnostics: ReplayDiagnostics
    cursor: Cursor
    undo_stack: UndoStack
    show_level: Value[bool]

    @classmethod
    def default(cls) -> "AppState":
        inputs = Inputs([Intents.default()] * 55)
        cursor = Cursor(InputsGrid(inputs))
        return cls(
            level=Value("downhill"),
            character=Value(Character.DUSTMAN),
            inputs=inputs,
            diagnostics=ReplayDiagnostics(inputs),
            cursor=cursor,
            undo_stack=UndoStack(inputs, cursor),
            show_level=Value(config.show_level),
        )
